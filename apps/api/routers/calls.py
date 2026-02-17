"""Calls router — Convenience wrapper for call records."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_current_user, get_db_session
from packages.db.models import InteractionEvent

router = APIRouter(prefix="/api/v1/calls", tags=["calls"])


@router.get("")
async def get_calls(
    direction: str | None = Query(None),
    status: str | None = Query(None),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    limit: int = Query(50, le=200),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get call records.

    Returns call history from interaction events.
    For full Ringover integration, use /api/v1/ringover/calls.
    """
    tenant_id = str(current_user["tenant_id"])

    from sqlalchemy import select

    query = (
        select(InteractionEvent)
        .where(InteractionEvent.tenant_id == tenant_id)
        .where(InteractionEvent.interaction_type == "call")
        .order_by(InteractionEvent.occurred_at.desc())
        .limit(limit)
    )

    if direction:
        query = query.where(InteractionEvent.direction == direction)

    result = await db.execute(query)
    events = result.scalars().all()

    return {
        "calls": [
            {
                "id": str(event.id),
                "case_id": str(event.case_id) if event.case_id else None,
                "contact_id": str(event.contact_id) if event.contact_id else None,
                "direction": event.direction,
                "occurred_at": event.occurred_at.isoformat()
                if event.occurred_at
                else None,
                "duration_seconds": event.duration_seconds,
                "transcript": event.transcript,
                "metadata": event.metadata or {},
            }
            for event in events
        ],
        "total": len(events),
    }


@router.get("/stats")
async def get_call_stats(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get call statistics."""
    tenant_id = str(current_user["tenant_id"])

    from sqlalchemy import func, select

    from packages.db.models import InteractionEvent

    # Count calls by direction
    query = (
        select(
            InteractionEvent.direction,
            func.count(InteractionEvent.id).label("count"),
            func.avg(InteractionEvent.duration_seconds).label("avg_duration"),
        )
        .where(InteractionEvent.tenant_id == tenant_id)
        .where(InteractionEvent.interaction_type == "call")
        .group_by(InteractionEvent.direction)
    )

    result = await db.execute(query)
    stats = result.all()

    return {
        "by_direction": [
            {
                "direction": row.direction,
                "count": row.count,
                "avg_duration_seconds": float(row.avg_duration)
                if row.avg_duration
                else 0,
            }
            for row in stats
        ]
    }
