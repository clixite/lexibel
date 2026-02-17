"""Transcriptions router — Manage audio transcriptions."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_current_user, get_db_session
from packages.db.models import InteractionEvent

router = APIRouter(prefix="/api/v1/transcriptions", tags=["transcriptions"])


@router.get("")
async def get_transcriptions(
    case_id: str | None = Query(None),
    limit: int = Query(50, le=200),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get transcriptions for calls/meetings.

    Returns transcription records from interaction events.
    """
    tenant_id = str(current_user["tenant_id"])

    # Build query
    from sqlalchemy import select

    query = (
        select(InteractionEvent)
        .where(InteractionEvent.tenant_id == tenant_id)
        .where(InteractionEvent.interaction_type == "call")
        .where(InteractionEvent.transcript.isnot(None))
        .order_by(InteractionEvent.occurred_at.desc())
        .limit(limit)
    )

    if case_id:
        query = query.where(InteractionEvent.case_id == case_id)

    result = await db.execute(query)
    events = result.scalars().all()

    return {
        "transcriptions": [
            {
                "id": str(event.id),
                "case_id": str(event.case_id) if event.case_id else None,
                "contact_id": str(event.contact_id) if event.contact_id else None,
                "transcript": event.transcript,
                "occurred_at": event.occurred_at.isoformat()
                if event.occurred_at
                else None,
                "duration_seconds": event.duration_seconds,
                "metadata": event.metadata or {},
            }
            for event in events
        ],
        "total": len(events),
    }
