"""Integrations router — OAuth, status, and sync triggers.

Google OAuth:
  GET    /api/v1/integrations/google/auth-url    — generate OAuth consent URL
  POST   /api/v1/integrations/google/callback    — exchange code for tokens
  POST   /api/v1/integrations/google/sync/gmail  — sync Gmail emails
  POST   /api/v1/integrations/google/sync/calendar — sync Google Calendar events
  DELETE /api/v1/integrations/google/disconnect  — revoke Google OAuth token

Microsoft OAuth:
  GET    /api/v1/integrations/microsoft/auth-url    — generate OAuth consent URL
  POST   /api/v1/integrations/microsoft/callback    — exchange code for tokens
  DELETE /api/v1/integrations/microsoft/disconnect — revoke Microsoft OAuth token

Status:
  GET    /api/v1/integrations/status — list enabled integrations per tenant

Outlook:
  POST   /api/v1/integrations/outlook/sync — trigger email sync
"""

import secrets
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_current_tenant, get_current_user, get_db_session
from apps.api.services import outlook_service
from apps.api.services.google_oauth_service import get_google_oauth_service
from apps.api.services.microsoft_oauth_service import get_microsoft_oauth_service
from apps.api.services.gmail_sync_service import get_gmail_sync_service
from apps.api.services.calendar_sync_service import get_calendar_sync_service
from apps.api.services.microsoft_outlook_sync_service import get_microsoft_outlook_sync_service
from apps.api.services.microsoft_calendar_service import get_microsoft_calendar_service
from packages.db.models.oauth_token import OAuthToken

router = APIRouter(prefix="/api/v1/integrations", tags=["integrations"])


class IntegrationStatus(BaseModel):
    name: str
    enabled: bool
    status: str = "disconnected"
    last_sync_at: Optional[str] = None


class IntegrationListResponse(BaseModel):
    integrations: list[IntegrationStatus]


class OutlookSyncRequest(BaseModel):
    mailbox: str = Field(..., description="Email address to sync")


class OutlookSyncResponse(BaseModel):
    status: str
    items_synced: int = 0
    message: str = ""


# Google OAuth models
class GoogleAuthUrlResponse(BaseModel):
    auth_url: str
    state: str


class GoogleCallbackRequest(BaseModel):
    code: str = Field(..., description="Authorization code from Google OAuth callback")


class GoogleCallbackResponse(BaseModel):
    status: str
    message: str
    provider: str = "google"


class GmailSyncResponse(BaseModel):
    status: str
    threads_created: int = 0
    messages_created: int = 0
    total_processed: int = 0


class CalendarSyncResponse(BaseModel):
    status: str
    events_created: int = 0
    total_processed: int = 0


# Microsoft OAuth models
class MicrosoftAuthUrlResponse(BaseModel):
    auth_url: str
    state: str


class MicrosoftCallbackRequest(BaseModel):
    code: str = Field(..., description="Authorization code from Microsoft OAuth callback")


class MicrosoftCallbackResponse(BaseModel):
    status: str
    message: str
    provider: str = "microsoft"


class OutlookEmailSyncResponse(BaseModel):
    status: str
    threads_created: int = 0
    messages_created: int = 0
    messages_updated: int = 0
    total_processed: int = 0


class MicrosoftCalendarSyncResponse(BaseModel):
    status: str
    events_created: int = 0
    events_updated: int = 0
    total_processed: int = 0


@router.get("/status", response_model=IntegrationListResponse)
async def get_integration_status(
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> IntegrationListResponse:
    """List all available integrations and their status for the current tenant."""
    user_id = user["user_id"]

    # Query OAuth tokens for this user
    stmt = select(OAuthToken).where(
        OAuthToken.tenant_id == tenant_id,
        OAuthToken.user_id == user_id,
    )
    result = await session.execute(stmt)
    oauth_tokens = result.scalars().all()

    # Build map of provider -> token
    token_map = {token.provider: token for token in oauth_tokens}

    # Check Google integration
    google_token = token_map.get("google")
    google_status = "connected" if google_token else "disconnected"
    google_last_sync = google_token.updated_at.isoformat() if google_token else None

    # Check Microsoft integration
    microsoft_token = token_map.get("microsoft")
    microsoft_status = "connected" if microsoft_token else "disconnected"
    microsoft_last_sync = microsoft_token.updated_at.isoformat() if microsoft_token else None

    integrations = [
        IntegrationStatus(
            name="google",
            enabled=google_status == "connected",
            status=google_status,
            last_sync_at=google_last_sync,
        ),
        IntegrationStatus(
            name="microsoft",
            enabled=microsoft_status == "connected",
            status=microsoft_status,
            last_sync_at=microsoft_last_sync,
        ),
        IntegrationStatus(
            name="ringover",
            enabled=True,
            status="active",
            last_sync_at=None,
        ),
        IntegrationStatus(
            name="plaud",
            enabled=True,
            status="active",
            last_sync_at=None,
        ),
        IntegrationStatus(
            name="outlook",
            enabled=False,
            status="disconnected",
            last_sync_at=None,
        ),
        IntegrationStatus(
            name="dpa_deposit",
            enabled=False,
            status="disconnected",
            last_sync_at=None,
        ),
    ]
    return IntegrationListResponse(integrations=integrations)


@router.post("/outlook/sync", response_model=OutlookSyncResponse)
async def trigger_outlook_sync(
    body: OutlookSyncRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db_session),
) -> OutlookSyncResponse:
    """Trigger an email sync from Outlook/Exchange for the current tenant."""
    emails = await outlook_service.sync_emails(tenant_id, body.mailbox)

    if not emails:
        return OutlookSyncResponse(
            status="ok",
            items_synced=0,
            message="No new emails found (stub — Graph API not yet configured)",
        )

    items = await outlook_service.create_inbox_items_from_emails(tenant_id, emails)
    return OutlookSyncResponse(
        status="ok",
        items_synced=len(items),
        message=f"Synced {len(items)} emails to inbox",
    )


# ── Google OAuth endpoints ──


@router.get("/google/auth-url", response_model=GoogleAuthUrlResponse)
async def get_google_auth_url() -> GoogleAuthUrlResponse:
    """Generate Google OAuth authorization URL.

    Returns authorization URL with state parameter for CSRF protection.
    User should be redirected to this URL to grant permissions.
    """
    google_oauth = get_google_oauth_service()
    state = secrets.token_urlsafe(32)

    auth_url = google_oauth.get_authorization_url(state)

    return GoogleAuthUrlResponse(
        auth_url=auth_url,
        state=state,
    )


@router.post("/google/callback", response_model=GoogleCallbackResponse)
async def handle_google_callback(
    body: GoogleCallbackRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> GoogleCallbackResponse:
    """Handle Google OAuth callback and exchange code for tokens.

    Stores encrypted access and refresh tokens in the database.
    """
    user_id = user["user_id"]
    google_oauth = get_google_oauth_service()

    try:
        await google_oauth.exchange_code_for_tokens(
            code=body.code,
            session=session,
            tenant_id=tenant_id,
            user_id=user_id,
        )

        return GoogleCallbackResponse(
            status="success",
            message="Google account connected successfully",
        )

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to exchange authorization code: {str(e)}",
        )


@router.delete("/google/disconnect")
async def disconnect_google(
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Disconnect Google OAuth integration.

    Revokes and deletes stored OAuth tokens.
    """
    user_id = user["user_id"]
    google_oauth = get_google_oauth_service()

    success = await google_oauth.revoke_token(
        session=session,
        tenant_id=tenant_id,
        user_id=user_id,
    )

    if success:
        return {
            "status": "success",
            "message": "Google account disconnected",
        }

    return {
        "status": "info",
        "message": "No Google account was connected",
    }


@router.post("/google/sync/gmail", response_model=GmailSyncResponse)
async def sync_gmail(
    max_results: int = Query(100, ge=1, le=500, description="Maximum emails to sync"),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> GmailSyncResponse:
    """Sync Gmail emails to database.

    Fetches emails from Gmail API and stores them in EmailThread and EmailMessage tables.
    Requires active Google OAuth connection.
    """
    user_id = user["user_id"]
    gmail_sync = get_gmail_sync_service()

    try:
        result = await gmail_sync.sync_emails(
            session=session,
            tenant_id=tenant_id,
            user_id=user_id,
            max_results=max_results,
        )

        return GmailSyncResponse(
            status="success",
            threads_created=result["threads_created"],
            messages_created=result["messages_created"],
            total_processed=result["total_processed"],
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync Gmail: {str(e)}",
        )


@router.post("/google/sync/calendar", response_model=CalendarSyncResponse)
async def sync_google_calendar(
    max_results: int = Query(100, ge=1, le=500, description="Maximum events to sync"),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> CalendarSyncResponse:
    """Sync Google Calendar events to database.

    Fetches calendar events from Google Calendar API and stores them in CalendarEvent table.
    Requires active Google OAuth connection.
    """
    user_id = user["user_id"]
    calendar_sync = get_calendar_sync_service()

    try:
        result = await calendar_sync.sync_google_calendar(
            session=session,
            tenant_id=tenant_id,
            user_id=user_id,
            max_results=max_results,
        )

        return CalendarSyncResponse(
            status="success",
            events_created=result["events_created"],
            total_processed=result["total_processed"],
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync Google Calendar: {str(e)}",
        )


# ── Microsoft OAuth endpoints ──


@router.get("/microsoft/auth-url", response_model=MicrosoftAuthUrlResponse)
async def get_microsoft_auth_url() -> MicrosoftAuthUrlResponse:
    """Generate Microsoft OAuth authorization URL.

    Returns authorization URL with state parameter for CSRF protection.
    User should be redirected to this URL to grant permissions.
    """
    microsoft_oauth = get_microsoft_oauth_service()
    state = secrets.token_urlsafe(32)

    auth_url = microsoft_oauth.get_authorization_url(state)

    return MicrosoftAuthUrlResponse(
        auth_url=auth_url,
        state=state,
    )


@router.post("/microsoft/callback", response_model=MicrosoftCallbackResponse)
async def handle_microsoft_callback(
    body: MicrosoftCallbackRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> MicrosoftCallbackResponse:
    """Handle Microsoft OAuth callback and exchange code for tokens.

    Stores encrypted access and refresh tokens in the database.
    """
    user_id = user["user_id"]
    microsoft_oauth = get_microsoft_oauth_service()

    try:
        await microsoft_oauth.exchange_code_for_tokens(
            code=body.code,
            session=session,
            tenant_id=tenant_id,
            user_id=user_id,
        )

        return MicrosoftCallbackResponse(
            status="success",
            message="Microsoft account connected successfully",
        )

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to exchange authorization code: {str(e)}",
        )


@router.delete("/microsoft/disconnect")
async def disconnect_microsoft(
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Disconnect Microsoft OAuth integration.

    Revokes and deletes stored OAuth tokens.
    """
    user_id = user["user_id"]
    microsoft_oauth = get_microsoft_oauth_service()

    success = await microsoft_oauth.revoke_token(
        session=session,
        tenant_id=tenant_id,
        user_id=user_id,
    )

    if success:
        return {
            "status": "success",
            "message": "Microsoft account disconnected",
        }

    return {
        "status": "info",
        "message": "No Microsoft account was connected",
    }


@router.post("/microsoft/sync/outlook", response_model=OutlookEmailSyncResponse)
async def sync_microsoft_outlook(
    since_date: Optional[datetime] = Query(None, description="Only sync emails after this date"),
    max_results: int = Query(50, ge=1, le=500, description="Maximum emails to sync"),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> OutlookEmailSyncResponse:
    """Sync Outlook emails via Microsoft Graph API.

    Fetches emails from Outlook and stores them in EmailThread and EmailMessage tables.
    Requires active Microsoft OAuth connection.
    """
    user_id = user["user_id"]
    outlook_sync = get_microsoft_outlook_sync_service()

    try:
        result = await outlook_sync.sync_to_db(
            session=session,
            tenant_id=tenant_id,
            user_id=user_id,
            since_date=since_date,
            max_results=max_results,
        )

        return OutlookEmailSyncResponse(
            status="success",
            threads_created=result["threads_created"],
            messages_created=result["messages_created"],
            messages_updated=result["messages_updated"],
            total_processed=result["total_processed"],
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync Outlook emails: {str(e)}",
        )


@router.post("/microsoft/sync/calendar", response_model=MicrosoftCalendarSyncResponse)
async def sync_microsoft_calendar(
    start_time: Optional[datetime] = Query(None, description="Filter events starting after this time"),
    end_time: Optional[datetime] = Query(None, description="Filter events ending before this time"),
    max_results: int = Query(100, ge=1, le=500, description="Maximum events to sync"),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> MicrosoftCalendarSyncResponse:
    """Sync Microsoft Calendar events via Graph API.

    Fetches calendar events and stores them in CalendarEvent table.
    Requires active Microsoft OAuth connection.
    """
    user_id = user["user_id"]
    calendar_service = get_microsoft_calendar_service()

    try:
        result = await calendar_service.sync_to_db(
            session=session,
            tenant_id=tenant_id,
            user_id=user_id,
            start_time=start_time,
            end_time=end_time,
            max_results=max_results,
        )

        return MicrosoftCalendarSyncResponse(
            status="success",
            events_created=result["events_created"],
            events_updated=result["events_updated"],
            total_processed=result["total_processed"],
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync Microsoft Calendar: {str(e)}",
        )
