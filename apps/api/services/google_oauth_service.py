"""Google OAuth service for Gmail and Google Calendar integration.

Handles OAuth2 flow, token storage, and refresh.
"""

import os
from datetime import datetime
from typing import Optional
from uuid import UUID

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.models.oauth_token import OAuthToken
from apps.api.services.oauth_encryption_service import get_oauth_encryption_service


class GoogleOAuthService:
    """Google OAuth2 integration service."""

    SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/calendar.readonly",
    ]

    def __init__(self):
        """Initialize Google OAuth service."""
        self.client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        self.redirect_uri = os.getenv(
            "GOOGLE_REDIRECT_URI", "http://localhost:3000/api/auth/callback/google"
        )

        if not self.client_id or not self.client_secret:
            raise ValueError("GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set")

        self.encryption_service = get_oauth_encryption_service()

    def get_authorization_url(self, state: str) -> str:
        """Generate OAuth authorization URL.

        Args:
            state: Random state parameter for CSRF protection

        Returns:
            Authorization URL to redirect user to
        """
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri],
                }
            },
            scopes=self.SCOPES,
            redirect_uri=self.redirect_uri,
        )

        authorization_url, _ = flow.authorization_url(
            access_type="offline",  # Get refresh token
            include_granted_scopes="true",
            state=state,
            prompt="consent",  # Force consent to get refresh token
        )

        return authorization_url

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
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri],
                }
            },
            scopes=self.SCOPES,
            redirect_uri=self.redirect_uri,
        )

        flow.fetch_token(code=code)

        credentials = flow.credentials

        # Encrypt tokens
        encrypted_access_token = self.encryption_service.encrypt(credentials.token)
        encrypted_refresh_token = None
        if credentials.refresh_token:
            encrypted_refresh_token = self.encryption_service.encrypt(
                credentials.refresh_token
            )

        # Check if token already exists
        stmt = select(OAuthToken).where(
            OAuthToken.tenant_id == tenant_id,
            OAuthToken.user_id == user_id,
            OAuthToken.provider == "google",
        )
        result = await session.execute(stmt)
        existing_token = result.scalar_one_or_none()

        if existing_token:
            # Update existing token
            existing_token.access_token = encrypted_access_token
            if encrypted_refresh_token:
                existing_token.refresh_token = encrypted_refresh_token
            existing_token.expires_at = credentials.expiry
            existing_token.scope = " ".join(self.SCOPES)
            existing_token.updated_at = datetime.utcnow()
            oauth_token = existing_token
        else:
            # Create new token
            oauth_token = OAuthToken(
                tenant_id=tenant_id,
                user_id=user_id,
                provider="google",
                access_token=encrypted_access_token,
                refresh_token=encrypted_refresh_token,
                token_type="Bearer",
                expires_at=credentials.expiry,
                scope=" ".join(self.SCOPES),
            )
            session.add(oauth_token)

        await session.commit()
        await session.refresh(oauth_token)

        return oauth_token

    async def get_valid_credentials(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
    ) -> Optional[Credentials]:
        """Get valid Google credentials, refreshing if necessary.

        Args:
            session: Database session
            tenant_id: Tenant ID
            user_id: User ID

        Returns:
            Valid Credentials object or None if no token exists
        """
        stmt = select(OAuthToken).where(
            OAuthToken.tenant_id == tenant_id,
            OAuthToken.user_id == user_id,
            OAuthToken.provider == "google",
        )
        result = await session.execute(stmt)
        oauth_token = result.scalar_one_or_none()

        if not oauth_token:
            return None

        # Decrypt tokens
        access_token = self.encryption_service.decrypt(oauth_token.access_token)
        refresh_token = None
        if oauth_token.refresh_token:
            refresh_token = self.encryption_service.decrypt(oauth_token.refresh_token)

        credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.client_id,
            client_secret=self.client_secret,
            scopes=self.SCOPES,
        )

        # Check if token is expired and refresh if needed
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())

            # Update stored token
            oauth_token.access_token = self.encryption_service.encrypt(
                credentials.token
            )
            oauth_token.expires_at = credentials.expiry
            oauth_token.updated_at = datetime.utcnow()
            await session.commit()

        return credentials

    async def revoke_token(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        user_id: UUID,
    ) -> bool:
        """Revoke Google OAuth token.

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
            OAuthToken.provider == "google",
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
_google_oauth_service: GoogleOAuthService | None = None


def get_google_oauth_service() -> GoogleOAuthService:
    """Get singleton Google OAuth service."""
    global _google_oauth_service
    if _google_oauth_service is None:
        _google_oauth_service = GoogleOAuthService()
    return _google_oauth_service
