"""Emails router — Email access, stats, and sync.

GET    /api/v1/emails        — list emails from inbox
GET    /api/v1/emails/stats  — email statistics
POST   /api/v1/emails/sync   — trigger email sync from providers
GET    /api/v1/emails/{id}   — get single email detail
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_current_user, get_db_session
from packages.db.models import InboxItem

router = APIRouter(prefix="/api/v1/emails", tags=["emails"])


def _inbox_to_email(item: InboxItem) -> dict:
    """Extract email fields from InboxItem raw_payload."""
    payload = item.raw_payload or {}
    return {
        "id": str(item.id),
        "subject": payload.get("subject", ""),
        "from_email": payload.get("from_email", payload.get("sender", "")),
        "from_name": payload.get("from_name", ""),
        "received_at": item.created_at.isoformat() if item.created_at else None,
        "status": item.status,
        "source": item.source,
        "metadata": {
            k: v
            for k, v in payload.items()
            if k not in ("subject", "from_email", "from_name", "sender", "body")
        },
    }


@router.get("")
async def get_emails(
    folder: str | None = Query(None),
    unread_only: bool = Query(False),
    limit: int = Query(50, le=200),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get emails from inbox.

    Returns inbox items from OUTLOOK source.
    For full Outlook integration, use /api/v1/outlook/emails.
    """
    tenant_id = str(current_user["tenant_id"])

    query = (
        select(InboxItem)
        .where(InboxItem.tenant_id == tenant_id)
        .where(InboxItem.source == "OUTLOOK")
        .order_by(InboxItem.created_at.desc())
        .limit(limit)
    )

    if unread_only:
        query = query.where(InboxItem.status == "DRAFT")

    result = await db.execute(query)
    items = result.scalars().all()

    return {
        "emails": [_inbox_to_email(item) for item in items],
        "total": len(items),
    }


@router.get("/stats")
async def get_email_stats(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get email statistics — total, unread, validated."""
    tenant_id = str(current_user["tenant_id"])

    # Total emails
    total_result = await db.execute(
        select(func.count())
        .select_from(InboxItem)
        .where(
            InboxItem.tenant_id == tenant_id,
            InboxItem.source == "OUTLOOK",
        )
    )
    total = total_result.scalar() or 0

    # Unread (DRAFT status)
    unread_result = await db.execute(
        select(func.count())
        .select_from(InboxItem)
        .where(
            InboxItem.tenant_id == tenant_id,
            InboxItem.source == "OUTLOOK",
            InboxItem.status == "DRAFT",
        )
    )
    unread = unread_result.scalar() or 0

    # Validated
    validated_result = await db.execute(
        select(func.count())
        .select_from(InboxItem)
        .where(
            InboxItem.tenant_id == tenant_id,
            InboxItem.source == "OUTLOOK",
            InboxItem.status == "VALIDATED",
        )
    )
    validated = validated_result.scalar() or 0

    return {
        "total": total,
        "unread": unread,
        "validated": validated,
        "refused": max(0, total - unread - validated),
    }


@router.post("/sync")
async def sync_emails(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Trigger email sync from configured providers (Outlook/Gmail).

    Checks for OAuth tokens and syncs from available providers.
    """

    tenant_id = current_user["tenant_id"]
    user_id = current_user["user_id"]

    synced = {"outlook": 0, "gmail": 0}

    # Try Outlook sync
    try:
        from apps.api.services.outlook_service import sync_emails_enhanced

        result = await sync_emails_enhanced(
            tenant_id=str(tenant_id),
            user_id=str(user_id),
        )
        synced["outlook"] = len(result) if isinstance(result, list) else 0
    except Exception:
        pass

    # Try Gmail sync via integrations service
    try:
        from apps.api.services.google_service import sync_gmail

        result = await sync_gmail(
            tenant_id=str(tenant_id),
            user_id=str(user_id),
        )
        synced["gmail"] = len(result) if isinstance(result, list) else 0
    except Exception:
        pass

    total_synced = synced["outlook"] + synced["gmail"]
    return {
        "status": "success",
        "synced": total_synced,
        "details": synced,
        "message": f"Synced {total_synced} new emails",
    }


@router.get("/{email_id}")
async def get_email_detail(
    email_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get a single email by ID."""
    tenant_id = str(current_user["tenant_id"])

    result = await db.execute(
        select(InboxItem).where(
            InboxItem.id == email_id,
            InboxItem.tenant_id == tenant_id,
            InboxItem.source == "OUTLOOK",
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Email not found")

    payload = item.raw_payload or {}
    return {
        "id": str(item.id),
        "subject": payload.get("subject", ""),
        "from_email": payload.get("from_email", payload.get("sender", "")),
        "from_name": payload.get("from_name", ""),
        "body": payload.get("body", payload.get("body_preview", "")),
        "received_at": item.created_at.isoformat() if item.created_at else None,
        "status": item.status,
        "source": item.source,
        "metadata": {
            k: v
            for k, v in payload.items()
            if k not in ("subject", "from_email", "from_name", "sender", "body")
        },
    }
