"""Outlook router — email sync and send endpoints.

POST /api/v1/outlook/sync   — trigger email sync
GET  /api/v1/outlook/emails — list synced emails
POST /api/v1/outlook/send   — send or draft an email
"""
from fastapi import APIRouter, Depends, HTTPException

from apps.api.dependencies import get_current_user
from apps.api.schemas.outlook import (
    OutlookSyncRequest,
    OutlookSyncResponse,
    OutlookEmailResponse,
    OutlookEmailListResponse,
    OutlookSendRequest,
    OutlookSendResponse,
)
from apps.api.services import outlook_service

router = APIRouter(prefix="/api/v1/outlook", tags=["outlook"])


@router.post("/sync", response_model=OutlookSyncResponse)
async def sync_emails(
    body: OutlookSyncRequest,
    current_user: dict = Depends(get_current_user),
) -> OutlookSyncResponse:
    """Trigger email sync from Outlook via Microsoft Graph API."""
    emails = await outlook_service.sync_emails_enhanced(
        tenant_id=str(current_user["tenant_id"]),
        user_id=body.user_id,
        since=body.since,
    )
    return OutlookSyncResponse(
        status="ok",
        emails=[
            OutlookEmailResponse(
                message_id=e["message_id"],
                subject=e["subject"],
                sender=e["sender"],
                recipients=e["recipients"],
                body_preview=e["body_preview"],
                received_at=e["received_at"],
                has_attachments=e.get("has_attachments", False),
                matched_case_id=e.get("matched_case_id"),
                matched_case_reference=e.get("matched_case_reference"),
            )
            for e in emails
        ],
        total_synced=len(emails),
        message=f"Synced {len(emails)} emails" if emails else "No new emails (stub — Graph API not configured)",
    )


@router.get("/emails", response_model=OutlookEmailListResponse)
async def list_emails(
    current_user: dict = Depends(get_current_user),
) -> OutlookEmailListResponse:
    """List synced emails for the current tenant."""
    emails = outlook_service.get_cached_emails(str(current_user["tenant_id"]))
    return OutlookEmailListResponse(
        emails=[
            OutlookEmailResponse(
                message_id=e["message_id"],
                subject=e["subject"],
                sender=e["sender"],
                recipients=e["recipients"],
                body_preview=e["body_preview"],
                received_at=e["received_at"],
                has_attachments=e.get("has_attachments", False),
                matched_case_id=e.get("matched_case_id"),
                matched_case_reference=e.get("matched_case_reference"),
            )
            for e in emails
        ],
        total=len(emails),
    )


@router.post("/send", response_model=OutlookSendResponse)
async def send_email(
    body: OutlookSendRequest,
    current_user: dict = Depends(get_current_user),
) -> OutlookSendResponse:
    """Send or queue an email via Outlook."""
    try:
        result = await outlook_service.send_email(
            tenant_id=str(current_user["tenant_id"]),
            to=body.to,
            subject=body.subject,
            body_text=body.body,
            draft_id=body.draft_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return OutlookSendResponse(
        status=result["status"],
        message_id=result.get("message_id", ""),
        message=result.get("message", ""),
    )
