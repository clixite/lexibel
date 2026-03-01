"""Emails router — Access synced email threads from Gmail and Outlook."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_current_tenant, get_current_user, get_db_session
from packages.db.models.email_message import EmailMessage
from packages.db.models.email_thread import EmailThread

router = APIRouter(prefix="/api/v1/emails", tags=["emails"])


def _extract_participants(participants: dict) -> list[str]:
    """Extract email addresses from the participants JSONB field."""
    emails: list[str] = []
    if not isinstance(participants, dict):
        return emails
    from_data = participants.get("from")
    if isinstance(from_data, dict) and from_data.get("email"):
        emails.append(from_data["email"])
    for to in participants.get("to", []):
        if isinstance(to, dict) and to.get("email"):
            emails.append(to["email"])
    return emails


@router.get("")
async def get_emails(
    limit: int = Query(50, le=200),
    current_user: dict = Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db_session),
):
    """Get synced email threads (Gmail + Outlook)."""
    query = (
        select(EmailThread)
        .where(EmailThread.tenant_id == tenant_id)
        .order_by(EmailThread.last_message_at.desc().nullslast())
        .limit(limit)
    )
    result = await db.execute(query)
    threads = result.scalars().all()

    emails = [
        {
            "id": str(t.id),
            "subject": t.subject or "(Aucun objet)",
            "participants": _extract_participants(t.participants),
            "date": t.last_message_at.isoformat() if t.last_message_at else None,
            "message_count": t.message_count,
            "has_attachments": t.has_attachments,
        }
        for t in threads
    ]

    return {"emails": emails, "total": len(emails)}


@router.get("/stats")
async def get_email_stats(
    current_user: dict = Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db_session),
):
    """Get email statistics."""
    total_threads = await db.scalar(
        select(func.count())
        .select_from(EmailThread)
        .where(EmailThread.tenant_id == tenant_id)
    )
    unread_count = await db.scalar(
        select(func.count())
        .select_from(EmailMessage)
        .where(EmailMessage.tenant_id == tenant_id, EmailMessage.is_read == False)  # noqa: E712
    )
    with_attachments = await db.scalar(
        select(func.count())
        .select_from(EmailThread)
        .where(
            EmailThread.tenant_id == tenant_id,
            EmailThread.has_attachments == True,  # noqa: E712
        )
    )
    return {
        "total_threads": total_threads or 0,
        "unread_count": unread_count or 0,
        "with_attachments": with_attachments or 0,
    }


@router.post("/sync")
async def sync_emails(
    current_user: dict = Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db_session),
):
    """Trigger email synchronization from Gmail and Outlook.

    Uses oauth_engine to retrieve valid tokens (handles auto-refresh).
    """
    from sqlalchemy import select as sa_select
    from packages.db.models.oauth_token import OAuthToken
    from apps.api.services.oauth_engine import get_oauth_engine

    user_id = (
        current_user["user_id"]
        if isinstance(current_user["user_id"], uuid.UUID)
        else uuid.UUID(str(current_user["user_id"]))
    )
    results: dict = {"google": None, "microsoft": None}
    oauth_engine = get_oauth_engine()

    # ── Google Gmail sync ──
    try:
        g_result = await db.execute(
            sa_select(OAuthToken).where(
                OAuthToken.tenant_id == tenant_id,
                OAuthToken.user_id == user_id,
                OAuthToken.provider == "google",
            )
        )
        g_token = g_result.scalar_one_or_none()

        if not g_token:
            results["google"] = {"error": "No Google account connected."}
        else:
            access_token = await oauth_engine.get_valid_token(db, g_token.id)
            from apps.api.services.gmail_sync_service import get_gmail_sync_service
            results["google"] = await get_gmail_sync_service().sync_emails_with_token(
                db, tenant_id, user_id, access_token
            )
    except Exception as e:
        results["google"] = {"error": str(e)}

    # ── Microsoft Outlook sync ──
    try:
        ms_result = await db.execute(
            sa_select(OAuthToken).where(
                OAuthToken.tenant_id == tenant_id,
                OAuthToken.user_id == user_id,
                OAuthToken.provider == "microsoft",
            )
        )
        ms_token = ms_result.scalar_one_or_none()

        if not ms_token:
            results["microsoft"] = {"error": "No Microsoft account connected."}
        else:
            access_token = await oauth_engine.get_valid_token(db, ms_token.id)
            from apps.api.services.microsoft_outlook_sync_service import (
                get_microsoft_outlook_sync_service,
            )
            results["microsoft"] = await get_microsoft_outlook_sync_service().sync_to_db_with_token(
                db, tenant_id, user_id, access_token
            )
    except Exception as e:
        results["microsoft"] = {"error": str(e)}

    return {"status": "success", "results": results}
