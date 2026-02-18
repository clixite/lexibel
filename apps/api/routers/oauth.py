"""OAuth2 router for Google and Microsoft integrations.

Endpoints:
- GET /oauth/{provider}/authorize - Get authorization URL
- GET /oauth/{provider}/callback - Handle OAuth callback
- GET /oauth/tokens - List user's OAuth tokens
- DELETE /oauth/tokens/{id} - Revoke token
- POST /oauth/tokens/{id}/test - Test token validity
- GET /oauth/config - Get tenant OAuth config (admin)
- PUT /oauth/config - Update tenant OAuth config (admin)
"""

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_current_tenant, get_current_user, get_db_session
from apps.api.services.oauth_engine import get_oauth_engine
from packages.db.models.oauth_token import OAuthToken
from packages.db.models.tenant import Tenant
from packages.db.models.user import User


router = APIRouter(prefix="/api/v1/oauth", tags=["oauth"])


class OAuthTokenResponse(BaseModel):
    """OAuth token response (without secrets)."""

    id: str
    provider: str
    email_address: str | None
    status: str
    scope: str | None
    expires_at: str | None
    created_at: str


class OAuthConfigResponse(BaseModel):
    """OAuth configuration response."""

    google_enabled: bool
    microsoft_enabled: bool
    google_client_id: str | None
    microsoft_client_id: str | None


class OAuthConfigUpdateRequest(BaseModel):
    """OAuth configuration update request."""

    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_enabled: bool | None = None
    microsoft_client_id: str | None = None
    microsoft_client_secret: str | None = None
    microsoft_enabled: bool | None = None


@router.get("/{provider}/authorize")
async def get_authorization_url(
    provider: Literal["google", "microsoft"],
    scopes: str | None = Query(None, description="Space-separated scopes (optional)"),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """Get OAuth2 authorization URL for the specified provider.

    Args:
        provider: 'google' or 'microsoft'
        scopes: Optional space-separated scopes (uses defaults if not provided)

    Returns:
        {
            "authorization_url": "https://...",
            "state": "JWT state token",
            "code_verifier": "PKCE code verifier (store client-side)"
        }
    """
    oauth_engine = get_oauth_engine()

    scope_list = scopes.split(" ") if scopes else None

    try:
        result = await oauth_engine.get_authorization_url(
            session=session,
            provider=provider,
            tenant_id=tenant_id,
            user_id=user.id,
            scopes=scope_list,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{provider}/callback")
async def oauth_callback(
    provider: Literal["google", "microsoft"],
    code: str = Query(..., description="Authorization code"),
    state: str = Query(..., description="State token"),
    code_verifier: str = Query(..., description="PKCE code verifier"),
    session: AsyncSession = Depends(get_db_session),
):
    """Handle OAuth2 callback from Google or Microsoft.

    This endpoint receives the authorization code and exchanges it for tokens.
    Then redirects to the frontend with success/error status.
    """
    oauth_engine = get_oauth_engine()

    try:
        # Exchange code for tokens
        oauth_token = await oauth_engine.handle_callback(
            session=session,
            provider=provider,
            code=code,
            state=state,
            code_verifier=code_verifier,
        )

        # Redirect to frontend with success
        frontend_url = f"https://lexibel.clixite.cloud/dashboard/admin?tab=integrations&status=success&provider={provider}&email={oauth_token.email_address}"
        return RedirectResponse(url=frontend_url)

    except ValueError as e:
        # Redirect to frontend with error
        frontend_url = f"https://lexibel.clixite.cloud/dashboard/admin?tab=integrations&status=error&message={str(e)}"
        return RedirectResponse(url=frontend_url)


@router.get("/tokens")
async def list_oauth_tokens(
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[OAuthTokenResponse]:
    """List all OAuth tokens for the current user.

    Returns tokens without sensitive data (no access_token/refresh_token).
    """
    result = await session.execute(
        select(OAuthToken)
        .where(
            OAuthToken.tenant_id == tenant_id,
            OAuthToken.user_id == user.id,
        )
        .order_by(OAuthToken.created_at.desc())
    )
    tokens = result.scalars().all()

    return [
        OAuthTokenResponse(
            id=str(token.id),
            provider=token.provider,
            email_address=token.email_address,
            status=token.status,
            scope=token.scope,
            expires_at=token.expires_at.isoformat() if token.expires_at else None,
            created_at=token.created_at.isoformat(),
        )
        for token in tokens
    ]


@router.delete("/tokens/{token_id}")
async def revoke_oauth_token(
    token_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """Revoke an OAuth token.

    Removes authorization and marks token as revoked.
    """
    # Verify token belongs to user
    result = await session.execute(
        select(OAuthToken).where(
            OAuthToken.id == token_id,
            OAuthToken.tenant_id == tenant_id,
            OAuthToken.user_id == user.id,
        )
    )
    token = result.scalar_one_or_none()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Token not found"
        )

    oauth_engine = get_oauth_engine()

    try:
        await oauth_engine.revoke_token(session, token_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/tokens/{token_id}/test")
async def test_oauth_token(
    token_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """Test an OAuth token by making a simple API call.

    For Google: Lists Gmail messages (limit 1)
    For Microsoft: Lists Outlook messages (limit 1)

    Returns:
        {
            "status": "ok",
            "provider": "google",
            "email": "user@example.com",
            "message": "Successfully retrieved 1 message"
        }
    """
    # Verify token belongs to user
    result = await session.execute(
        select(OAuthToken).where(
            OAuthToken.id == token_id,
            OAuthToken.tenant_id == tenant_id,
            OAuthToken.user_id == user.id,
        )
    )
    token = result.scalar_one_or_none()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Token not found"
        )

    oauth_engine = get_oauth_engine()

    try:
        # Get valid access token (will refresh if needed)
        access_token = await oauth_engine.get_valid_token(session, token_id)

        # Make test API call
        import httpx

        async with httpx.AsyncClient() as client:
            if token.provider == "google":
                response = await client.get(
                    "https://gmail.googleapis.com/gmail/v1/users/me/messages?maxResults=1",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
            else:  # microsoft
                response = await client.get(
                    "https://graph.microsoft.com/v1.0/me/messages?$top=1",
                    headers={"Authorization": f"Bearer {access_token}"},
                )

            if response.status_code != 200:
                return {
                    "status": "error",
                    "provider": token.provider,
                    "email": token.email_address,
                    "message": f"API call failed: {response.status_code} {response.text}",
                }

            data = response.json()
            message_count = (
                data.get("resultSizeEstimate", 0)
                if token.provider == "google"
                else len(data.get("value", []))
            )

            return {
                "status": "ok",
                "provider": token.provider,
                "email": token.email_address,
                "message": f"Successfully retrieved {message_count} message(s)",
            }

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/config")
async def get_oauth_config(
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> OAuthConfigResponse:
    """Get OAuth configuration for the tenant.

    Only returns client IDs (not secrets).
    """
    # TODO: Add admin role check
    # if user.role != "admin":
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    result = await session.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )

    oauth_config = tenant.config.get("oauth", {})

    return OAuthConfigResponse(
        google_enabled=oauth_config.get("google", {}).get("enabled", False),
        microsoft_enabled=oauth_config.get("microsoft", {}).get("enabled", False),
        google_client_id=oauth_config.get("google", {}).get("client_id"),
        microsoft_client_id=oauth_config.get("microsoft", {}).get("client_id"),
    )


@router.put("/config")
async def update_oauth_config(
    config_update: OAuthConfigUpdateRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """Update OAuth configuration for the tenant.

    Admin only.
    """
    # TODO: Add admin role check
    # if user.role != "admin":
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    result = await session.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )

    # Get existing config
    config = tenant.config or {}
    oauth_config = config.get("oauth", {})

    # Update Google config
    if (
        config_update.google_client_id is not None
        or config_update.google_client_secret is not None
        or config_update.google_enabled is not None
    ):
        google_config = oauth_config.get("google", {})
        if config_update.google_client_id is not None:
            google_config["client_id"] = config_update.google_client_id
        if config_update.google_client_secret is not None:
            google_config["client_secret"] = config_update.google_client_secret
        if config_update.google_enabled is not None:
            google_config["enabled"] = config_update.google_enabled
        oauth_config["google"] = google_config

    # Update Microsoft config
    if (
        config_update.microsoft_client_id is not None
        or config_update.microsoft_client_secret is not None
        or config_update.microsoft_enabled is not None
    ):
        microsoft_config = oauth_config.get("microsoft", {})
        if config_update.microsoft_client_id is not None:
            microsoft_config["client_id"] = config_update.microsoft_client_id
        if config_update.microsoft_client_secret is not None:
            microsoft_config["client_secret"] = config_update.microsoft_client_secret
        if config_update.microsoft_enabled is not None:
            microsoft_config["enabled"] = config_update.microsoft_enabled
        oauth_config["microsoft"] = microsoft_config

    # Update tenant config
    config["oauth"] = oauth_config
    tenant.config = config

    await session.commit()

    return {"message": "OAuth configuration updated successfully"}
