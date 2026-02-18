"""OAuth Flow Engine for Google and Microsoft OAuth2 flows.

Handles authorization URL generation, code exchange, token refresh,
and token revocation for both providers.
"""

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal
from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.models.oauth_token import OAuthToken
from packages.db.models.tenant import Tenant
from packages.security.oauth_state import get_state_manager
from packages.security.pkce import create_pkce_pair
from packages.security.token_encryption import get_encryption_service


ProviderType = Literal["google", "microsoft"]


class OAuthEngine:
    """OAuth2 flow engine supporting Google and Microsoft."""

    # OAuth2 endpoints
    GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
    GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

    MICROSOFT_AUTH_URL = (
        "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
    )
    MICROSOFT_TOKEN_URL = (
        "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    )
    MICROSOFT_REVOKE_URL = (
        "https://login.microsoftonline.com/common/oauth2/v2.0/revoke"
    )
    MICROSOFT_USERINFO_URL = "https://graph.microsoft.com/v1.0/me"

    # Default scopes
    GOOGLE_SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/calendar.readonly",
        "https://www.googleapis.com/auth/userinfo.email",
    ]

    MICROSOFT_SCOPES = [
        "offline_access",  # Required for refresh token
        "User.Read",
        "Mail.Read",
        "Mail.Send",
        "Calendars.Read",
    ]

    def __init__(self):
        """Initialize OAuth engine with encryption and state services."""
        self.encryption = get_encryption_service()
        self.state_manager = get_state_manager()
        self.redirect_base_url = os.getenv(
            "OAUTH_REDIRECT_BASE_URL", "https://lexibel.clixite.cloud"
        )

    async def get_oauth_config(
        self, session: AsyncSession, tenant_id: uuid.UUID, provider: ProviderType
    ) -> dict:
        """Get OAuth configuration for a tenant.

        Checks tenant.config.oauth.{provider} first, falls back to env vars.
        """
        # Query tenant config
        result = await session.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()

        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")

        # Try tenant-specific config first
        oauth_config = tenant.config.get("oauth", {}).get(provider, {})

        if provider == "google":
            client_id = oauth_config.get("client_id") or os.getenv(
                "GOOGLE_CLIENT_ID"
            )
            client_secret = oauth_config.get("client_secret") or os.getenv(
                "GOOGLE_CLIENT_SECRET"
            )
        else:  # microsoft
            client_id = oauth_config.get("client_id") or os.getenv(
                "MICROSOFT_CLIENT_ID"
            )
            client_secret = oauth_config.get("client_secret") or os.getenv(
                "MICROSOFT_CLIENT_SECRET"
            )

        if not client_id or not client_secret:
            raise ValueError(
                f"OAuth config missing for {provider}. "
                f"Set {provider.upper()}_CLIENT_ID and {provider.upper()}_CLIENT_SECRET "
                "in environment or configure in tenant settings."
            )

        return {
            "client_id": client_id,
            "client_secret": client_secret,
        }

    async def get_authorization_url(
        self,
        session: AsyncSession,
        provider: ProviderType,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        scopes: list[str] | None = None,
    ) -> dict[str, str]:
        """Generate OAuth2 authorization URL with PKCE.

        Returns:
            {
                "authorization_url": "https://...",
                "state": "JWT state token"
            }
        """
        # Get OAuth config
        config = await self.get_oauth_config(session, tenant_id, provider)

        # Create state token (JWT with tenant_id, user_id, provider)
        state = self.state_manager.create_state(tenant_id, user_id, provider)

        # Generate PKCE pair
        code_verifier, code_challenge = create_pkce_pair()

        # Store code_verifier in session/Redis (TODO: implement Redis storage)
        # For now, we'll pass it in the state token (not recommended for production)

        # Build redirect URI
        redirect_uri = f"{self.redirect_base_url}/api/v1/oauth/{provider}/callback"

        # Use default scopes if not provided
        if not scopes:
            scopes = (
                self.GOOGLE_SCOPES if provider == "google" else self.MICROSOFT_SCOPES
            )

        # Build authorization URL
        if provider == "google":
            params = {
                "client_id": config["client_id"],
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": " ".join(scopes),
                "access_type": "offline",  # Get refresh token
                "prompt": "consent",  # Force consent to always get refresh token
                "state": state,
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
            }
            auth_url = f"{self.GOOGLE_AUTH_URL}?{urlencode(params)}"

        else:  # microsoft
            params = {
                "client_id": config["client_id"],
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": " ".join(scopes),
                "state": state,
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
                "response_mode": "query",
            }
            auth_url = f"{self.MICROSOFT_AUTH_URL}?{urlencode(params)}"

        return {
            "authorization_url": auth_url,
            "state": state,
            "code_verifier": code_verifier,  # Client needs to store this
        }

    async def handle_callback(
        self,
        session: AsyncSession,
        provider: ProviderType,
        code: str,
        state: str,
        code_verifier: str,
    ) -> OAuthToken:
        """Exchange authorization code for access/refresh tokens.

        Args:
            session: Database session
            provider: 'google' or 'microsoft'
            code: Authorization code from callback
            state: State token from callback (JWT)
            code_verifier: PKCE code verifier (from client storage)

        Returns:
            Created OAuthToken instance

        Raises:
            ValueError: If state invalid or token exchange fails
        """
        # Validate state
        state_data = self.state_manager.validate_state(state)
        tenant_id = state_data["tenant_id"]
        user_id = state_data["user_id"]

        # Verify provider matches
        if state_data["provider"] != provider:
            raise ValueError(
                f"Provider mismatch: expected {state_data['provider']}, got {provider}"
            )

        # Get OAuth config
        config = await self.get_oauth_config(session, tenant_id, provider)

        # Build redirect URI (must match authorization request)
        redirect_uri = f"{self.redirect_base_url}/api/v1/oauth/{provider}/callback"

        # Exchange code for tokens
        async with httpx.AsyncClient() as client:
            token_url = (
                self.GOOGLE_TOKEN_URL
                if provider == "google"
                else self.MICROSOFT_TOKEN_URL
            )

            data = {
                "client_id": config["client_id"],
                "client_secret": config["client_secret"],
                "code": code,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
                "code_verifier": code_verifier,  # PKCE
            }

            response = await client.post(token_url, data=data)

            if response.status_code != 200:
                raise ValueError(
                    f"Token exchange failed: {response.status_code} {response.text}"
                )

            token_data = response.json()

        # Get user profile to extract email
        access_token = token_data["access_token"]
        email_address = await self._get_user_email(provider, access_token)

        # Encrypt tokens
        encrypted_access = self.encryption.encrypt(access_token)
        encrypted_refresh = (
            self.encryption.encrypt(token_data["refresh_token"])
            if token_data.get("refresh_token")
            else None
        )

        # Calculate expiration
        expires_in = token_data.get("expires_in", 3600)  # Default 1 hour
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        # Check if token already exists for this user+provider
        existing = await session.execute(
            select(OAuthToken).where(
                OAuthToken.tenant_id == tenant_id,
                OAuthToken.user_id == user_id,
                OAuthToken.provider == provider,
            )
        )
        oauth_token = existing.scalar_one_or_none()

        if oauth_token:
            # Update existing token
            oauth_token.access_token = encrypted_access
            oauth_token.refresh_token = encrypted_refresh
            oauth_token.token_type = token_data.get("token_type", "Bearer")
            oauth_token.expires_at = expires_at
            oauth_token.scope = token_data.get("scope", "")
            oauth_token.status = "active"
            oauth_token.email_address = email_address
        else:
            # Create new token
            oauth_token = OAuthToken(
                tenant_id=tenant_id,
                user_id=user_id,
                provider=provider,
                access_token=encrypted_access,
                refresh_token=encrypted_refresh,
                token_type=token_data.get("token_type", "Bearer"),
                expires_at=expires_at,
                scope=token_data.get("scope", ""),
                status="active",
                email_address=email_address,
            )
            session.add(oauth_token)

        await session.commit()
        await session.refresh(oauth_token)

        return oauth_token

    async def _get_user_email(self, provider: ProviderType, access_token: str) -> str:
        """Get user email from provider's userinfo endpoint."""
        async with httpx.AsyncClient() as client:
            if provider == "google":
                response = await client.get(
                    self.GOOGLE_USERINFO_URL,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
            else:  # microsoft
                response = await client.get(
                    self.MICROSOFT_USERINFO_URL,
                    headers={"Authorization": f"Bearer {access_token}"},
                )

            if response.status_code != 200:
                raise ValueError(f"Failed to get user profile: {response.text}")

            data = response.json()
            return data.get("email") or data.get("userPrincipalName")

    async def refresh_token(
        self, session: AsyncSession, token_id: uuid.UUID
    ) -> OAuthToken:
        """Refresh an expired OAuth token.

        Args:
            session: Database session
            token_id: OAuthToken ID

        Returns:
            Updated OAuthToken

        Raises:
            ValueError: If token not found or refresh fails
        """
        # Get token from database
        result = await session.execute(
            select(OAuthToken).where(OAuthToken.id == token_id)
        )
        oauth_token = result.scalar_one_or_none()

        if not oauth_token:
            raise ValueError(f"OAuth token {token_id} not found")

        if not oauth_token.refresh_token:
            raise ValueError("No refresh token available")

        # Decrypt refresh token
        refresh_token = self.encryption.decrypt(oauth_token.refresh_token)

        # Get OAuth config
        config = await self.get_oauth_config(
            session, oauth_token.tenant_id, oauth_token.provider
        )

        # Refresh token
        async with httpx.AsyncClient() as client:
            token_url = (
                self.GOOGLE_TOKEN_URL
                if oauth_token.provider == "google"
                else self.MICROSOFT_TOKEN_URL
            )

            data = {
                "client_id": config["client_id"],
                "client_secret": config["client_secret"],
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            }

            response = await client.post(token_url, data=data)

            if response.status_code != 200:
                # Mark token as expired
                oauth_token.status = "expired"
                await session.commit()
                raise ValueError(f"Token refresh failed: {response.text}")

            token_data = response.json()

        # Update token
        oauth_token.access_token = self.encryption.encrypt(token_data["access_token"])
        oauth_token.expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=token_data.get("expires_in", 3600)
        )
        oauth_token.status = "active"

        # Update refresh token if new one provided
        if token_data.get("refresh_token"):
            oauth_token.refresh_token = self.encryption.encrypt(
                token_data["refresh_token"]
            )

        await session.commit()
        await session.refresh(oauth_token)

        return oauth_token

    async def get_valid_token(
        self, session: AsyncSession, token_id: uuid.UUID
    ) -> str:
        """Get a valid access token, refreshing if expired.

        Args:
            session: Database session
            token_id: OAuthToken ID

        Returns:
            Decrypted access_token ready to use

        Raises:
            ValueError: If token cannot be refreshed
        """
        result = await session.execute(
            select(OAuthToken).where(OAuthToken.id == token_id)
        )
        oauth_token = result.scalar_one_or_none()

        if not oauth_token:
            raise ValueError(f"OAuth token {token_id} not found")

        if oauth_token.status == "revoked":
            raise ValueError("Token has been revoked")

        # Check if token is expired (with 5 min buffer)
        now = datetime.now(timezone.utc)
        buffer = timedelta(minutes=5)

        if oauth_token.expires_at and oauth_token.expires_at < (now + buffer):
            # Token expired or expiring soon, refresh it
            oauth_token = await self.refresh_token(session, token_id)

        # Decrypt and return access token
        return self.encryption.decrypt(oauth_token.access_token)

    async def revoke_token(
        self, session: AsyncSession, token_id: uuid.UUID
    ) -> None:
        """Revoke an OAuth token.

        Args:
            session: Database session
            token_id: OAuthToken ID
        """
        result = await session.execute(
            select(OAuthToken).where(OAuthToken.id == token_id)
        )
        oauth_token = result.scalar_one_or_none()

        if not oauth_token:
            raise ValueError(f"OAuth token {token_id} not found")

        # Decrypt access token
        access_token = self.encryption.decrypt(oauth_token.access_token)

        # Revoke token with provider
        async with httpx.AsyncClient() as client:
            if oauth_token.provider == "google":
                await client.post(
                    self.GOOGLE_REVOKE_URL,
                    data={"token": access_token},
                )
            else:  # microsoft
                config = await self.get_oauth_config(
                    session, oauth_token.tenant_id, oauth_token.provider
                )
                await client.post(
                    self.MICROSOFT_REVOKE_URL,
                    data={
                        "client_id": config["client_id"],
                        "client_secret": config["client_secret"],
                        "token": access_token,
                    },
                )

        # Mark as revoked in database
        oauth_token.status = "revoked"
        await session.commit()


# Global instance
_oauth_engine: OAuthEngine | None = None


def get_oauth_engine() -> OAuthEngine:
    """Get or create the global OAuth engine instance."""
    global _oauth_engine
    if _oauth_engine is None:
        _oauth_engine = OAuthEngine()
    return _oauth_engine
