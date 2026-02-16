"""Integrations router — status and sync triggers.

GET    /api/v1/integrations/status       — list enabled integrations per tenant
POST   /api/v1/integrations/outlook/sync — trigger email sync
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_current_tenant, get_db_session
from apps.api.services import outlook_service

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


@router.get("/status", response_model=IntegrationListResponse)
async def get_integration_status(
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> IntegrationListResponse:
    """List all available integrations and their status for the current tenant."""
    # In production, read from tenant config / integration_settings table
    integrations = [
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
