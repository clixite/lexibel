"""Emails router — Convenience wrapper for email access."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_current_user, get_db_session
from packages.db.models import InboxItem

router = APIRouter(prefix="/api/v1/emails", tags=["emails"])


@router.get("")
async def get_emails(
    folder: str | None = Query(None),
    unread_only: bool = Query(False),
    limit: int = Query(50, le=200),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get emails from inbox.

    Returns emails from the inbox that have item_type='email'.
    For full Outlook integration, use /api/v1/outlook/emails.
    """
    tenant_id = str(current_user["tenant_id"])

    from sqlalchemy import select

    query = (
        select(InboxItem)
        .where(InboxItem.tenant_id == tenant_id)
        .where(InboxItem.item_type == "email")
        .order_by(InboxItem.received_at.desc())
        .limit(limit)
    )

    if unread_only:
        query = query.where(InboxItem.status == "pending")

    result = await db.execute(query)
    items = result.scalars().all()

    return {
        "emails": [
            {
                "id": str(item.id),
                "subject": item.subject,
                "from_email": item.from_email,
                "from_name": item.from_name,
                "received_at": item.received_at.isoformat()
                if item.received_at
                else None,
                "status": item.status,
                "metadata": item.metadata or {},
            }
            for item in items
        ],
        "total": len(items),
    }
