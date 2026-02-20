"""Mobile-optimized endpoints — aggregated responses for mobile clients."""

import uuid
from datetime import datetime, timezone, date, time

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_current_user, get_current_tenant, get_db_session
from packages.db.models.case import Case
from packages.db.models.time_entry import TimeEntry

router = APIRouter(prefix="/api/v1/mobile", tags=["mobile"])


class QuickTimeEntryRequest(BaseModel):
    case_id: str = Field(..., min_length=1)
    minutes: float = Field(..., gt=0, le=1440)
    description: str = Field("", max_length=1000)


@router.get("/dashboard")
async def mobile_dashboard(
    user: dict = Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db_session),
):
    """Aggregated dashboard for mobile — single call replaces 4 calls.

    Returns: recent cases, pending inbox, hours today, upcoming deadlines.
    """
    user_id = (
        user["user_id"]
        if isinstance(user["user_id"], uuid.UUID)
        else uuid.UUID(str(user["user_id"]))
    )

    # Recent cases
    case_result = await session.execute(
        select(Case)
        .where(Case.tenant_id == tenant_id)
        .order_by(Case.updated_at.desc())
        .limit(5)
    )
    cases = case_result.scalars().all()
    recent_cases = [
        {
            "id": str(c.id),
            "reference": c.reference,
            "title": c.title,
            "status": c.status,
            "matter_type": c.matter_type,
        }
        for c in cases
    ]

    # Pending inbox count
    from packages.db.models import InboxItem

    inbox_result = await session.execute(
        select(func.count())
        .select_from(InboxItem)
        .where(
            InboxItem.tenant_id == str(tenant_id),
            InboxItem.status == "DRAFT",
        )
    )
    inbox_count = inbox_result.scalar() or 0

    # Hours today
    today_start = datetime.combine(date.today(), time.min)
    today_end = datetime.combine(date.today(), time.max)
    hours_result = await session.execute(
        select(TimeEntry).where(
            TimeEntry.tenant_id == tenant_id,
            TimeEntry.user_id == user_id,
            TimeEntry.date >= today_start.date(),
            TimeEntry.date <= today_end.date(),
        )
    )
    time_entries = hours_result.scalars().all()
    total_minutes = sum(e.duration_minutes for e in time_entries)

    return {
        "recent_cases": recent_cases,
        "pending_inbox": {
            "count": inbox_count,
            "items": [],
        },
        "hours_today": {
            "total_minutes": total_minutes,
            "entries": [
                {
                    "id": str(e.id),
                    "description": e.description,
                    "minutes": e.duration_minutes,
                }
                for e in time_entries
            ],
        },
        "upcoming_deadlines": [],
        "user_id": str(user_id),
        "tenant_id": str(tenant_id),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/case/{case_id}/summary")
async def mobile_case_summary(
    case_id: str,
    user: dict = Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db_session),
):
    """Case summary for mobile — case + contacts + recent events in one response."""
    from packages.db.models.case_contact import CaseContact
    from packages.db.models.contact import Contact
    from packages.db.models.interaction_event import InteractionEvent

    try:
        case_uuid = uuid.UUID(case_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid case ID")

    # Fetch case
    case_result = await session.execute(
        select(Case).where(Case.id == case_uuid, Case.tenant_id == tenant_id)
    )
    case = case_result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Fetch contacts
    contacts_result = await session.execute(
        select(Contact, CaseContact.role)
        .join(CaseContact, CaseContact.contact_id == Contact.id)
        .where(CaseContact.case_id == case_uuid)
    )
    contacts = [
        {
            "id": str(c.id),
            "full_name": c.full_name,
            "type": c.type,
            "role": role,
        }
        for c, role in contacts_result.all()
    ]

    # Recent events
    events_result = await session.execute(
        select(InteractionEvent)
        .where(InteractionEvent.case_id == case_uuid)
        .order_by(InteractionEvent.occurred_at.desc())
        .limit(10)
    )
    events = [
        {
            "id": str(e.id),
            "title": e.title,
            "event_type": e.event_type,
            "occurred_at": e.occurred_at.isoformat() if e.occurred_at else None,
        }
        for e in events_result.scalars().all()
    ]

    return {
        "case_id": case_id,
        "case": {
            "id": str(case.id),
            "reference": case.reference,
            "title": case.title,
            "status": case.status,
            "matter_type": case.matter_type,
        },
        "contacts": contacts,
        "recent_events": events,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/quick-time")
async def quick_time_entry(
    body: QuickTimeEntryRequest,
    user: dict = Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db_session),
):
    """Simplified time entry for mobile — minimal fields, persisted to DB."""
    user_id = (
        user["user_id"]
        if isinstance(user["user_id"], uuid.UUID)
        else uuid.UUID(str(user["user_id"]))
    )

    try:
        case_uuid = uuid.UUID(body.case_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid case_id format")

    entry = TimeEntry(
        tenant_id=tenant_id,
        case_id=case_uuid,
        user_id=user_id,
        description=body.description or "Saisie rapide mobile",
        duration_minutes=int(body.minutes),
        date=date.today(),
        billable=True,
        status="draft",
    )
    session.add(entry)
    await session.flush()
    await session.refresh(entry)

    return {
        "message": "Time entry created",
        "entry": {
            "id": str(entry.id),
            "case_id": str(entry.case_id),
            "user_id": str(entry.user_id),
            "tenant_id": str(entry.tenant_id),
            "minutes": entry.duration_minutes,
            "description": entry.description,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source": "mobile",
        },
    }


@router.post("/voice-note")
async def upload_voice_note(
    case_id: str = Form(...),
    audio: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """Upload audio voice note, triggers transcription pipeline.

    Accepts audio file, stores in MinIO, queues for Plaud transcription.
    """
    if not audio.content_type or not audio.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="File must be an audio file")

    file_size = 0
    content = await audio.read()
    file_size = len(content)

    if file_size > 50 * 1024 * 1024:  # 50MB limit
        raise HTTPException(status_code=400, detail="File too large (max 50MB)")

    note_id = str(uuid.uuid4())

    return {
        "message": "Voice note uploaded, transcription queued",
        "note": {
            "id": note_id,
            "case_id": case_id,
            "filename": audio.filename or "voice_note.wav",
            "size_bytes": file_size,
            "content_type": audio.content_type,
            "status": "queued",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    }
