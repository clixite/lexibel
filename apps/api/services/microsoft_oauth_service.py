"""Microsoft OAuth service for Outlook and Microsoft Calendar integration.

Handles OAuth2 flow, token storage, and refresh via Microsoft Graph API.
"""

import os
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.models.oauth_token import OAuthToken
from apps.api.services.oauth_encryption_service import get_oauth_encryption_service


class MicrosoftOAuthService:
    """Microsoft OAuth2 integration service (Graph API)."""

    SCOPES = [
        "Mail.Read",
        "Calendars.Read",
        "offline_access",  # Required for refresh token
    ]

    def __init__(self):
        """Initialize Microsoft OAuth service."""
        self.client_id = os.getenv("MICROSOFT_CLIENT_ID")
        self.client_secret = os.getenv("MICROSOFT_CLIENT_SECRET")
        self.tenant_id = os.getenv("MICROSOFT_TENANT_ID", "common")
        self.redirect_uri = os.getenv(
            "MICROSOFT_REDIRECT_URI",
            "http://localhost:3000/api/auth/callback/microsoft"
        )

        if not self.client_id or not self.client_secret:
            raise ValueError("MICROSOFT_CLIENT_ID and MICROSOFT_CLIENT_SECRET must be set")

        self.encryption_service = get_oauth_encryption_service()

        # Microsoft endpoints
        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        self.authorize_url = f"{self.authority}/oauth2/v2.0/authorize"
        self.token_url = f"{self.authority}/oauth2/v2.0/token"

    def get_authorization_url(self, state: str) -> str:
        """Generate OAuth authorization URL.

        Args:
            state: Random state parameter for CSRF protection

        Returns:
            Authorization URL to redirect user to
        """
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.SCOPES),
            "state": state,
            "response_mode": "query",
            "prompt": "consent",  # Force consent to get refresh token
        }

        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.authorize_url}?{query_string}"

    async def exchange_code_for_tokens(
        self,
        code: str,
        session: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
    ) -> OAuthToken:
        """Exchange authorization code for access/refresh tokens.

        Args:
            code: Authorization code from callback
            session: Database session
            tenant_id: Tenant ID
            user_id: User ID

        Returns:
            Created OAuthToken record
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": self.redirect_uri,
                    "grant_type": "authorization_code",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            response.raise_for_status()
            token_data = response.json()

        access_token = token_data["access_token"]
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 3600)

        # Encrypt tokens
        encrypted_access_token = self.encryption_service.encrypt(access_token)
        encrypted_refresh_token = None
        if refresh_token:
            encrypted_refresh_token = self.encryption_service.encrypt(refresh_token)

        # Calculate expiry
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        # Check if token already exists
        stmt = select(OAuthToken).where(
            OAuthToken.tenant_id == tenant_id,
            OAuthToken.user_id == user_id,
            OAuthToken.provider == "microsoft",
        )
        result = await session.execute(stmt)
        existing_token = result.scalar_one_or_none()

        if existing_token:
            # Update existing token
            existing_token.access_token = encrypted_access_token
            if encrypted_refresh_token:
                existing_token.refresh_token = encrypted_refresh_token
            existing_token.expires_at = expires_at
            existing_token.scope = " ".join(self.SCOPES)
            existing_token.updated_at = datetime.utcnow()
            oauth_token = existing_token
        else:
            # Create new token
            oauth_token = OAuthToken(
                tenant_id=tenant_id,
                user_id=user_id,
                provider="microsoft",
                access_token=encrypted_access_token,
                refresh_token=encrypted_refresh_token,
                token_type="Bearer",
                expires_at=expires_at,
                scope=" ".join(self.SCOPES),
            )
            session.add(oauth_token)

        await session.commit()
        await session.refresh(oauth_token)

        return oauth_token

    async def refresh_access_token(
        self,
        oauth_token: OAuthToken,
        session: AsyncSession,
    ) -> str:
        """Refresh access token using refresh token.

        Args:
            oauth_token: OAuthToken record with refresh_token
            session: Database session

        Returns:
            New access token (decrypted)
        """
        if not oauth_token.refresh_token:
            raise ValueError("No refresh token available")

        refresh_token = self.encryption_service.decrypt(oauth_token.refresh_token)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            response.raise_for_status()
            token_data = response.json()

        access_token = token_data["access_token"]
        new_refresh_token = token_data.get("refresh_token", refresh_token)
        expires_in = token_data.get("expires_in", 3600)

        # Update stored token
        oauth_token.access_token = self.encryption_service.encrypt(access_token)
        if new_refresh_token != refresh_token:
            oauth_token.refresh_token = self.encryption_service.encrypt(new_refresh_token)
        oauth_token.expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        oauth_token.updated_at = datetime.utcnow()

        await session.commit()

        return access_token

    async def get_valid_access_token(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
    ) -> Optional[str]:
        """Get valid access token, refreshing if necessary.

        Args:
            session: Database session
            tenant_id: Tenant ID
            user_id: User ID

        Returns:
            Valid access token (decrypted) or None if no token exists
        """
        stmt = select(OAuthToken).where(
            OAuthToken.tenant_id == tenant_id,
            OAuthToken.user_id == user_id,
            OAuthToken.provider == "microsoft",
        )
        result = await session.execute(stmt)
        oauth_token = result.scalar_one_or_none()

        if not oauth_token:
            return None

        # Check if token is expired
        if oauth_token.expires_at and oauth_token.expires_at < datetime.utcnow():
            # Refresh token
            return await self.refresh_access_token(oauth_token, session)

        # Decrypt and return valid token
        return self.encryption_service.decrypt(oauth_token.access_token)

    async def revoke_token(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
    ) -> bool:
        """Revoke Microsoft OAuth token.

        Args:
            session: Database session
            tenant_id: Tenant ID
            user_id: User ID

        Returns:
            True if token was revoked, False if no token existed
        """
        stmt = select(OAuthToken).where(
            OAuthToken.tenant_id == tenant_id,
            OAuthToken.user_id == user_id,
            OAuthToken.provider == "microsoft",
        )
        result = await session.execute(stmt)
        oauth_token = result.scalar_one_or_none()

        if not oauth_token:
            return False

        # Delete token from database
        await session.delete(oauth_token)
        await session.commit()

        return True


# Singleton instance
_microsoft_oauth_service: MicrosoftOAuthService | None = None


def get_microsoft_oauth_service() -> MicrosoftOAuthService:
    """Get singleton Microsoft OAuth service."""
    global _microsoft_oauth_service
    if _microsoft_oauth_service is None:
        _microsoft_oauth_service = MicrosoftOAuthService()
    return _microsoft_oauth_service
