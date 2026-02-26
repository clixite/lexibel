"""Emails router — Email access, stats, sync, compose, templates, search.

GET    /api/v1/emails              — list emails from inbox
GET    /api/v1/emails/stats        — email statistics
POST   /api/v1/emails/sync         — trigger email sync from providers
GET    /api/v1/emails/search       — full-text search across emails
GET    /api/v1/emails/templates    — list email templates
POST   /api/v1/emails/templates    — create custom template
POST   /api/v1/emails/templates/seed — seed system templates
POST   /api/v1/emails/templates/render — render template with case/contact data
GET    /api/v1/emails/templates/{id}  — get single template
PATCH  /api/v1/emails/templates/{id}  — update template
DELETE /api/v1/emails/templates/{id}  — delete template
POST   /api/v1/emails/compose      — compose and send email
POST   /api/v1/emails/{id}/link-case — auto-link email to case
GET    /api/v1/emails/{id}         — get single email detail
"""

import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_current_tenant, get_current_user, get_db_session
from apps.api.schemas.email_template import (
    EmailComposeRequest,
    EmailComposeResponse,
    EmailTemplateCreate,
    EmailTemplateRenderRequest,
    EmailTemplateRenderResponse,
    EmailTemplateResponse,
    EmailTemplateUpdate,
)
from apps.api.services import email_template_service
from packages.db.models import InboxItem
from packages.db.models.email_message import EmailMessage
from packages.db.models.email_thread import EmailThread

router = APIRouter(prefix="/api/v1/emails", tags=["emails"])

# ── Case reference patterns for auto-linking ──
CASE_REF_PATTERNS = [
    re.compile(r"\b(\d{4}/\d{2,4}(?:/[A-Z])?)\b"),  # 2026/001/A
    re.compile(r"\b[Dd]ossier\s+(\d+)\b"),  # Dossier 42
    re.compile(r"\bRG\s+(\d+/\d+)\b"),  # RG 2026/123
    re.compile(r"\bDOS[-\s]?(\d{3,6})\b"),  # DOS-001234
]


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


# ── Core email endpoints ──


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
    """Get email statistics — total, unread, validated, threads."""
    tenant_id = str(current_user["tenant_id"])

    # Total emails (inbox items)
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

    # Synced threads count
    thread_result = await db.execute(
        select(func.count())
        .select_from(EmailThread)
        .where(EmailThread.tenant_id == tenant_id)
    )
    threads = thread_result.scalar() or 0

    # Linked to cases
    linked_result = await db.execute(
        select(func.count())
        .select_from(EmailThread)
        .where(
            EmailThread.tenant_id == tenant_id,
            EmailThread.case_id.isnot(None),
        )
    )
    linked = linked_result.scalar() or 0

    return {
        "total": total,
        "unread": unread,
        "validated": validated,
        "refused": max(0, total - unread - validated),
        "threads": threads,
        "linked_to_case": linked,
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


# ── Full-text search ──


@router.get("/search")
async def search_emails(
    q: str = Query(..., min_length=1),
    case_id: uuid.UUID | None = Query(None),
    from_email: str | None = Query(None),
    has_attachments: bool | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Full-text search across synced email messages."""
    tenant_id = str(current_user["tenant_id"])
    pattern = f"%{q}%"

    query = (
        select(EmailMessage)
        .join(EmailThread, EmailThread.id == EmailMessage.thread_id)
        .where(
            EmailMessage.tenant_id == tenant_id,
            or_(
                EmailMessage.subject.ilike(pattern),
                EmailMessage.body_text.ilike(pattern),
                EmailMessage.from_address.ilike(pattern),
            ),
        )
    )

    if case_id:
        query = query.where(EmailThread.case_id == case_id)
    if from_email:
        query = query.where(EmailMessage.from_address.ilike(f"%{from_email}%"))
    if has_attachments is not None:
        query = query.where(EmailThread.has_attachments == has_attachments)

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Paginate
    query = query.order_by(EmailMessage.received_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    messages = result.scalars().all()

    return {
        "items": [
            {
                "id": str(msg.id),
                "thread_id": str(msg.thread_id),
                "subject": msg.subject,
                "from_address": msg.from_address,
                "body_preview": (msg.body_text or "")[:200],
                "received_at": msg.received_at.isoformat() if msg.received_at else None,
                "is_read": msg.is_read,
            }
            for msg in messages
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


# ── Email Templates ──


@router.get("/templates", response_model=list[EmailTemplateResponse])
async def list_templates(
    category: str | None = Query(None),
    language: str | None = Query(None),
    matter_type: str | None = Query(None),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
):
    """List available email templates."""
    templates = await email_template_service.list_templates(
        db,
        tenant_id=tenant_id,
        category=category,
        language=language,
        matter_type=matter_type,
    )
    return [EmailTemplateResponse.model_validate(t) for t in templates]


@router.post(
    "/templates",
    response_model=EmailTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_template(
    body: EmailTemplateCreate,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Create a custom email template."""
    template = await email_template_service.create_template(
        db,
        tenant_id=tenant_id,
        name=body.name,
        category=body.category,
        subject_template=body.subject_template,
        body_template=body.body_template,
        language=body.language,
        matter_types=body.matter_types,
        created_by=current_user["user_id"],
    )
    await db.commit()
    return EmailTemplateResponse.model_validate(template)


@router.post("/templates/seed")
async def seed_templates(
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
):
    """Seed system templates for this tenant."""
    count = await email_template_service.seed_system_templates(db, tenant_id)
    await db.commit()
    return {"seeded": count, "message": f"Created {count} system templates"}


@router.post("/templates/render", response_model=EmailTemplateRenderResponse)
async def render_template(
    body: EmailTemplateRenderRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
):
    """Render an email template with case/contact data."""
    try:
        rendered = await email_template_service.render_for_case(
            db,
            template_id=body.template_id,
            case_id=body.case_id,
            contact_id=body.contact_id,
            extra_vars=body.extra_variables,
            tenant_id=tenant_id,
        )
        return EmailTemplateRenderResponse(**rendered)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/templates/{template_id}", response_model=EmailTemplateResponse)
async def get_template(
    template_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
):
    """Get a single email template."""
    template = await email_template_service.get_template(
        db, template_id, tenant_id=tenant_id
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return EmailTemplateResponse.model_validate(template)


@router.patch("/templates/{template_id}", response_model=EmailTemplateResponse)
async def update_template(
    template_id: uuid.UUID,
    body: EmailTemplateUpdate,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
):
    """Update a custom email template."""
    try:
        update_data = body.model_dump(exclude_unset=True)
        template = await email_template_service.update_template(
            db, template_id, tenant_id=tenant_id, **update_data
        )
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        await db.commit()
        return EmailTemplateResponse.model_validate(template)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
):
    """Delete a custom email template."""
    try:
        deleted = await email_template_service.delete_template(
            db, template_id, tenant_id=tenant_id
        )
        if not deleted:
            raise HTTPException(status_code=404, detail="Template not found")
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Compose & Send ──


@router.post("/compose", response_model=EmailComposeResponse)
async def compose_email(
    body: EmailComposeRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Compose and send an email via the user's connected provider.

    Supports:
    - Direct compose
    - Reply (set in_reply_to)
    - Template-based compose (set template_id + case_id)
    - Auto-link to case (set case_id)
    """
    from packages.db.models.oauth_token import OAuthToken

    user_id = current_user["user_id"]

    # Find active OAuth token for this user (defense-in-depth: filter by tenant_id)
    token_result = await db.execute(
        select(OAuthToken).where(
            OAuthToken.tenant_id == tenant_id,
            OAuthToken.user_id == user_id,
            OAuthToken.status == "active",
            OAuthToken.provider.in_(["google", "microsoft"]),
        )
    )
    oauth_token = token_result.scalar_one_or_none()
    if not oauth_token:
        raise HTTPException(
            status_code=400,
            detail="No active email integration found. Connect Outlook or Gmail first.",
        )

    # Send via email sync service
    from apps.api.services.email_sync import get_email_sync_service

    service = get_email_sync_service()
    try:
        result = await service.send_email(
            session=db,
            token_id=oauth_token.id,
            to=body.to[0],  # Primary recipient
            subject=body.subject,
            body=body.body_text,
            cc=body.cc or None,
            body_html=body.body_html,
        )
    except ValueError as e:
        raise HTTPException(status_code=502, detail=f"Send failed: {e}")

    # Log as interaction event if linked to case
    if body.case_id:
        from datetime import datetime

        from packages.db.models.interaction_event import InteractionEvent

        event = InteractionEvent(
            tenant_id=tenant_id,
            case_id=body.case_id,
            source="OUTLOOK" if oauth_token.provider == "microsoft" else "MANUAL",
            event_type="EMAIL",
            title=f"Email envoyé: {body.subject}",
            body=body.body_text[:500],
            occurred_at=datetime.utcnow(),
            metadata_={
                "to": [str(addr) for addr in body.to],
                "cc": [str(addr) for addr in body.cc] if body.cc else [],
                "message_id": result.get("message_id"),
                "provider": result.get("provider"),
            },
            created_by=user_id,
        )
        db.add(event)
        await db.flush()

    await db.commit()

    return EmailComposeResponse(
        status="sent",
        message_id=result.get("message_id"),
        provider=result.get("provider", "unknown"),
        case_id=str(body.case_id) if body.case_id else None,
    )


# ── Auto-link to case ──


@router.post("/{email_id}/link-case")
async def link_email_to_case(
    email_id: uuid.UUID,
    case_id: uuid.UUID | None = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Link an email thread to a case.

    If case_id is not provided, attempts to auto-detect
    from case reference patterns in the subject/body.
    """
    from packages.db.models.case import Case

    tenant_id = str(current_user["tenant_id"])

    # Find the email thread
    thread_result = await db.execute(
        select(EmailThread).where(
            EmailThread.id == email_id,
            EmailThread.tenant_id == tenant_id,
        )
    )
    thread = thread_result.scalar_one_or_none()
    if not thread:
        raise HTTPException(status_code=404, detail="Email thread not found")

    if case_id:
        # Manual link
        thread.case_id = case_id
        await db.flush()
        await db.commit()
        return {
            "status": "linked",
            "thread_id": str(email_id),
            "case_id": str(case_id),
            "method": "manual",
        }

    # Auto-detect case reference from subject
    detected_refs = []
    text = thread.subject or ""

    # Also check first message body
    msg_result = await db.execute(
        select(EmailMessage)
        .where(EmailMessage.thread_id == thread.id)
        .order_by(EmailMessage.received_at.asc())
        .limit(1)
    )
    first_msg = msg_result.scalar_one_or_none()
    if first_msg and first_msg.body_text:
        text += " " + first_msg.body_text[:1000]

    for pattern in CASE_REF_PATTERNS:
        matches = pattern.findall(text)
        detected_refs.extend(matches)

    if not detected_refs:
        return {
            "status": "no_match",
            "thread_id": str(email_id),
            "message": "No case reference detected in email subject/body",
        }

    # Try to match detected references to existing cases
    for ref in detected_refs:
        case_result = await db.execute(
            select(Case).where(
                Case.tenant_id == tenant_id,
                Case.reference.ilike(f"%{ref}%"),
            )
        )
        matched_case = case_result.scalar_one_or_none()
        if matched_case:
            thread.case_id = matched_case.id
            await db.flush()
            await db.commit()
            return {
                "status": "linked",
                "thread_id": str(email_id),
                "case_id": str(matched_case.id),
                "case_reference": matched_case.reference,
                "method": "auto",
                "matched_pattern": ref,
            }

    return {
        "status": "no_match",
        "thread_id": str(email_id),
        "detected_references": detected_refs,
        "message": "References detected but no matching case found",
    }


# ── Single email detail ──


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

    # Classify email
    from apps.api.services.ml.email_triage import EmailTriageClassifier

    classifier = EmailTriageClassifier()
    classification = classifier.classify(
        subject=payload.get("subject", ""),
        body=payload.get("body", payload.get("body_preview", "")),
        sender=payload.get("from_email", payload.get("sender", "")),
    )

    return {
        "id": str(item.id),
        "subject": payload.get("subject", ""),
        "from_email": payload.get("from_email", payload.get("sender", "")),
        "from_name": payload.get("from_name", ""),
        "body": payload.get("body", payload.get("body_preview", "")),
        "received_at": item.created_at.isoformat() if item.created_at else None,
        "status": item.status,
        "source": item.source,
        "classification": {
            "category": classification.category,
            "confidence": classification.confidence,
            "priority": classification.suggested_priority,
            "reasons": classification.reasons,
        },
        "metadata": {
            k: v
            for k, v in payload.items()
            if k not in ("subject", "from_email", "from_name", "sender", "body")
        },
    }
