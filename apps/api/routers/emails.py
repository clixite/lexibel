"""Emails router — Full email thread/message management with sync."""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_current_user, get_db_session
from packages.db.models.email_message import EmailMessage
from packages.db.models.email_thread import EmailThread
from packages.db.models.oauth_token import OAuthToken

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/emails", tags=["emails"])


# --------------- Schemas ---------------


class LinkCaseRequest(BaseModel):
    case_id: str


class MarkReadRequest(BaseModel):
    is_read: bool = True


# --------------- GET /emails/stats ---------------


@router.get("/stats")
async def get_email_stats(
    case_id: str | None = Query(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Email statistics for the current tenant."""
    tenant_id = str(current_user["tenant_id"])

    base = select(EmailThread).where(EmailThread.tenant_id == tenant_id)
    if case_id:
        base = base.where(EmailThread.case_id == uuid.UUID(case_id))

    # Total threads
    total_q = select(func.count()).select_from(base.subquery())
    total_threads = (await db.execute(total_q)).scalar() or 0

    # Unread count (threads that have at least one unread message)
    unread_q = (
        select(func.count(func.distinct(EmailMessage.thread_id)))
        .where(EmailMessage.tenant_id == tenant_id)
        .where(EmailMessage.is_read.is_(False))
    )
    unread_count = (await db.execute(unread_q)).scalar() or 0

    # Threads with attachments
    attach_q = base.where(EmailThread.has_attachments.is_(True))
    attach_count_q = select(func.count()).select_from(attach_q.subquery())
    with_attachments = (await db.execute(attach_count_q)).scalar() or 0

    return {
        "total_threads": total_threads,
        "unread_count": unread_count,
        "with_attachments": with_attachments,
    }


# --------------- GET /emails/sync-status ---------------


@router.get("/sync-status")
async def get_sync_status(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Return sync status for each connected email provider."""
    tenant_id = str(current_user["tenant_id"])
    user_id = str(current_user["user_id"])

    result = await db.execute(
        select(OAuthToken).where(
            OAuthToken.tenant_id == tenant_id,
            OAuthToken.user_id == user_id,
            OAuthToken.provider.in_(["google", "microsoft"]),
        )
    )
    tokens = result.scalars().all()

    syncs = []
    for token in tokens:
        syncs.append(
            {
                "id": str(token.id),
                "provider": token.provider,
                "email": token.email_address,
                "status": token.sync_status or "idle",
                "error": token.sync_error,
                "last_sync_at": token.last_sync_at.isoformat()
                if token.last_sync_at
                else None,
            }
        )

    return {"syncs": syncs}


# --------------- POST /emails/sync ---------------


@router.post("/sync")
async def trigger_email_sync(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Trigger email synchronization for all connected email providers."""
    tenant_id = str(current_user["tenant_id"])
    user_id = str(current_user["user_id"])

    # Find all email-capable OAuth tokens for this user
    result = await db.execute(
        select(OAuthToken).where(
            OAuthToken.tenant_id == tenant_id,
            OAuthToken.user_id == user_id,
            OAuthToken.provider.in_(["google", "microsoft"]),
            OAuthToken.status == "active",
        )
    )
    tokens = result.scalars().all()

    if not tokens:
        raise HTTPException(
            status_code=404,
            detail="Aucun compte email connecté. Configurez Google ou Microsoft dans les Paramètres.",
        )

    from apps.api.services.email_sync import get_email_sync_service

    sync_service = get_email_sync_service()
    results = []

    for token in tokens:
        try:
            # Mark as syncing
            token.sync_status = "syncing"
            token.sync_error = None
            await db.commit()

            sync_result = await sync_service.sync_emails(
                session=db,
                token_id=token.id,
                max_results=50,
            )
            results.append(sync_result)

            # Mark success
            token.sync_status = "idle"
            token.last_sync_at = datetime.now(timezone.utc)
            await db.commit()

        except Exception as e:
            logger.error("Email sync failed for token %s: %s", token.id, e)
            token.sync_status = "error"
            token.sync_error = str(e)[:500]
            await db.commit()
            results.append({"error": str(e), "provider": token.provider})

    return {"status": "completed", "results": results}


# --------------- POST /emails/sync/{integration_id} ---------------


@router.post("/sync/{integration_id}")
async def trigger_sync_for_integration(
    integration_id: str = Path(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Trigger sync for a specific OAuth integration."""
    tenant_id = str(current_user["tenant_id"])

    result = await db.execute(
        select(OAuthToken).where(
            OAuthToken.id == uuid.UUID(integration_id),
            OAuthToken.tenant_id == tenant_id,
            OAuthToken.status == "active",
        )
    )
    token = result.scalar_one_or_none()

    if not token:
        raise HTTPException(status_code=404, detail="Intégration non trouvée")

    from apps.api.services.email_sync import get_email_sync_service

    sync_service = get_email_sync_service()

    try:
        token.sync_status = "syncing"
        token.sync_error = None
        await db.commit()

        sync_result = await sync_service.sync_emails(
            session=db, token_id=token.id, max_results=50
        )

        token.sync_status = "idle"
        token.last_sync_at = datetime.now(timezone.utc)
        await db.commit()

        return {"status": "completed", "result": sync_result}

    except Exception as e:
        logger.error("Email sync failed for token %s: %s", token.id, e)
        token.sync_status = "error"
        token.sync_error = str(e)[:500]
        await db.commit()
        raise HTTPException(status_code=500, detail=str(e))


# --------------- GET /emails/threads ---------------


@router.get("/threads")
async def get_email_threads(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    case_id: str | None = Query(None),
    has_attachments: bool | None = Query(None),
    is_important: bool | None = Query(None),
    search: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """List email threads with filtering and pagination."""
    tenant_id = str(current_user["tenant_id"])

    query = select(EmailThread).where(EmailThread.tenant_id == tenant_id)

    if case_id:
        query = query.where(EmailThread.case_id == uuid.UUID(case_id))
    if has_attachments is not None:
        query = query.where(EmailThread.has_attachments == has_attachments)
    if is_important is not None:
        query = query.where(EmailThread.is_important == is_important)
    if search:
        query = query.where(EmailThread.subject.ilike(f"%{search}%"))
    if date_from:
        query = query.where(
            EmailThread.last_message_at >= datetime.fromisoformat(date_from)
        )
    if date_to:
        query = query.where(
            EmailThread.last_message_at <= datetime.fromisoformat(date_to)
        )

    # Count
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Paginate
    offset = (page - 1) * per_page
    query = (
        query.order_by(EmailThread.last_message_at.desc().nullslast())
        .offset(offset)
        .limit(per_page)
    )
    result = await db.execute(query)
    threads = result.scalars().all()

    return {
        "threads": [
            {
                "id": str(t.id),
                "subject": t.subject,
                "participants": _format_participants(t.participants),
                "message_count": t.message_count,
                "has_attachments": t.has_attachments,
                "is_important": t.is_important,
                "last_message_at": t.last_message_at.isoformat()
                if t.last_message_at
                else None,
                "case_id": str(t.case_id) if t.case_id else None,
                "provider": t.provider,
            }
            for t in threads
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


# --------------- GET /emails/threads/{thread_id}/messages ---------------


@router.get("/threads/{thread_id}/messages")
async def get_thread_messages(
    thread_id: str = Path(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get all messages in a thread."""
    tenant_id = str(current_user["tenant_id"])

    # Verify thread belongs to tenant
    thread_result = await db.execute(
        select(EmailThread).where(
            EmailThread.id == uuid.UUID(thread_id),
            EmailThread.tenant_id == tenant_id,
        )
    )
    thread = thread_result.scalar_one_or_none()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread non trouvé")

    result = await db.execute(
        select(EmailMessage)
        .where(
            EmailMessage.thread_id == uuid.UUID(thread_id),
            EmailMessage.tenant_id == tenant_id,
        )
        .order_by(EmailMessage.received_at.asc())
    )
    messages = result.scalars().all()

    return {
        "messages": [_format_message(m) for m in messages],
        "total": len(messages),
        "thread": {
            "id": str(thread.id),
            "subject": thread.subject,
            "provider": thread.provider,
        },
    }


# --------------- GET /emails/{email_id} ---------------


@router.get("/{email_id}")
async def get_email(
    email_id: str = Path(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get a single email message by ID."""
    tenant_id = str(current_user["tenant_id"])

    result = await db.execute(
        select(EmailMessage).where(
            EmailMessage.id == uuid.UUID(email_id),
            EmailMessage.tenant_id == tenant_id,
        )
    )
    message = result.scalar_one_or_none()

    if not message:
        raise HTTPException(status_code=404, detail="Email non trouvé")

    return _format_message(message)


# --------------- POST /emails/{email_id}/link-case ---------------


@router.post("/{email_id}/link-case")
async def link_email_to_case(
    body: LinkCaseRequest,
    email_id: str = Path(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Link an email's thread to a dossier (case)."""
    tenant_id = str(current_user["tenant_id"])

    # Get the message to find its thread
    result = await db.execute(
        select(EmailMessage).where(
            EmailMessage.id == uuid.UUID(email_id),
            EmailMessage.tenant_id == tenant_id,
        )
    )
    message = result.scalar_one_or_none()
    if not message:
        raise HTTPException(status_code=404, detail="Email non trouvé")

    # Update the thread's case_id
    await db.execute(
        update(EmailThread)
        .where(
            EmailThread.id == message.thread_id,
            EmailThread.tenant_id == tenant_id,
        )
        .values(case_id=uuid.UUID(body.case_id))
    )
    await db.commit()

    return {
        "status": "linked",
        "thread_id": str(message.thread_id),
        "case_id": body.case_id,
    }


# --------------- POST /emails/{email_id}/mark-read ---------------


@router.post("/{email_id}/mark-read")
async def mark_email_read(
    body: MarkReadRequest,
    email_id: str = Path(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Mark an email as read or unread."""
    tenant_id = str(current_user["tenant_id"])

    result = await db.execute(
        select(EmailMessage).where(
            EmailMessage.id == uuid.UUID(email_id),
            EmailMessage.tenant_id == tenant_id,
        )
    )
    message = result.scalar_one_or_none()
    if not message:
        raise HTTPException(status_code=404, detail="Email non trouvé")

    message.is_read = body.is_read
    await db.commit()

    return {"status": "updated", "is_read": body.is_read}


# --------------- Helpers ---------------


def _format_participants(participants: dict | None) -> list[str]:
    """Extract participant email addresses from JSONB."""
    if not participants:
        return []
    emails = set()
    from_info = participants.get("from", {})
    if isinstance(from_info, dict) and from_info.get("email"):
        emails.add(from_info["email"])
    for key in ("to", "cc"):
        for p in participants.get(key, []):
            if isinstance(p, dict) and p.get("email"):
                emails.add(p["email"])
    return sorted(emails)


def _format_message(m: EmailMessage) -> dict:
    return {
        "id": str(m.id),
        "thread_id": str(m.thread_id),
        "external_id": m.external_id,
        "provider": m.provider,
        "subject": m.subject,
        "from_address": m.from_address,
        "to_addresses": m.to_addresses or [],
        "cc_addresses": m.cc_addresses or [],
        "bcc_addresses": m.bcc_addresses or [],
        "body_text": m.body_text,
        "body_html": m.body_html,
        "attachments": m.attachments or [],
        "is_read": m.is_read,
        "is_important": m.is_important,
        "received_at": m.received_at.isoformat() if m.received_at else None,
        "synced_at": m.synced_at.isoformat() if m.synced_at else None,
    }
