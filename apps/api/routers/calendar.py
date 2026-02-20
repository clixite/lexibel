"""Calendar router — Calendar events from Google and Outlook."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_current_user, get_current_tenant, get_db_session
from packages.db.models.calendar_event import CalendarEvent
from apps.api.services.calendar_sync_service import get_calendar_sync_service

router = APIRouter(prefix="/api/v1/calendar", tags=["calendar"])


@router.get("/events")
async def get_calendar_events(
    after: datetime | None = Query(None, description="Filter events after this date"),
    before: datetime | None = Query(None, description="Filter events before this date"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """Get calendar events."""
    user_id = (
        current_user["user_id"]
        if isinstance(current_user["user_id"], uuid.UUID)
        else uuid.UUID(str(current_user["user_id"]))
    )

    query = select(CalendarEvent).where(
        CalendarEvent.tenant_id == tenant_id,
        CalendarEvent.user_id == user_id,
    )

    if after:
        query = query.where(CalendarEvent.start_time >= after)
    if before:
        query = query.where(CalendarEvent.start_time <= before)

    query = query.order_by(CalendarEvent.start_time.asc())
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await session.execute(query)
    events = result.scalars().all()

    # Count total
    count_query = (
        select(func.count())
        .select_from(CalendarEvent)
        .where(
            CalendarEvent.tenant_id == tenant_id,
            CalendarEvent.user_id == user_id,
        )
    )
    if after:
        count_query = count_query.where(CalendarEvent.start_time >= after)
    if before:
        count_query = count_query.where(CalendarEvent.start_time <= before)

    total_result = await session.execute(count_query)
    total = total_result.scalar()

    return {
        "events": [
            {
                "id": str(event.id),
                "title": event.title,
                "description": event.description,
                "start_time": event.start_time.isoformat()
                if event.start_time
                else None,
                "end_time": event.end_time.isoformat() if event.end_time else None,
                "location": event.location,
                "provider": event.provider,
                "is_all_day": event.is_all_day,
            }
            for event in events
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.post("/events", status_code=201)
async def create_calendar_event(
    title: str,
    start_time: datetime,
    end_time: datetime | None = None,
    description: str | None = None,
    location: str | None = None,
    is_all_day: bool = False,
    case_id: uuid.UUID | None = None,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """Create a new calendar event."""
    user_id = (
        current_user["user_id"]
        if isinstance(current_user["user_id"], uuid.UUID)
        else uuid.UUID(str(current_user["user_id"]))
    )

    event = CalendarEvent(
        tenant_id=tenant_id,
        user_id=user_id,
        title=title,
        description=description,
        start_time=start_time,
        end_time=end_time,
        location=location,
        provider="manual",
        is_all_day=is_all_day,
    )
    session.add(event)
    await session.flush()
    await session.refresh(event)

    return {
        "id": str(event.id),
        "title": event.title,
        "description": event.description,
        "start_time": event.start_time.isoformat() if event.start_time else None,
        "end_time": event.end_time.isoformat() if event.end_time else None,
        "location": event.location,
        "provider": event.provider,
        "is_all_day": event.is_all_day,
    }


@router.patch("/events/{event_id}")
async def update_calendar_event(
    event_id: uuid.UUID,
    title: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    description: str | None = None,
    location: str | None = None,
    is_all_day: bool | None = None,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """Update a calendar event."""
    result = await session.execute(
        select(CalendarEvent).where(
            CalendarEvent.id == event_id,
            CalendarEvent.tenant_id == tenant_id,
        )
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if title is not None:
        event.title = title
    if start_time is not None:
        event.start_time = start_time
    if end_time is not None:
        event.end_time = end_time
    if description is not None:
        event.description = description
    if location is not None:
        event.location = location
    if is_all_day is not None:
        event.is_all_day = is_all_day

    await session.flush()
    await session.refresh(event)

    return {
        "id": str(event.id),
        "title": event.title,
        "description": event.description,
        "start_time": event.start_time.isoformat() if event.start_time else None,
        "end_time": event.end_time.isoformat() if event.end_time else None,
        "location": event.location,
        "provider": event.provider,
        "is_all_day": event.is_all_day,
    }


@router.delete("/events/{event_id}", status_code=204)
async def delete_calendar_event(
    event_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """Delete a calendar event."""
    from sqlalchemy import delete as sa_delete

    result = await session.execute(
        sa_delete(CalendarEvent).where(
            CalendarEvent.id == event_id,
            CalendarEvent.tenant_id == tenant_id,
        )
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Event not found")
    await session.commit()


@router.get("/stats")
async def get_calendar_stats(
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """Get calendar statistics."""
    user_id = (
        current_user["user_id"]
        if isinstance(current_user["user_id"], uuid.UUID)
        else uuid.UUID(str(current_user["user_id"]))
    )

    # Total events
    total_query = (
        select(func.count())
        .select_from(CalendarEvent)
        .where(
            CalendarEvent.tenant_id == tenant_id,
            CalendarEvent.user_id == user_id,
        )
    )
    total_result = await session.execute(total_query)
    total = total_result.scalar()

    # Upcoming events (after now)
    now = datetime.utcnow()
    upcoming_query = (
        select(func.count())
        .select_from(CalendarEvent)
        .where(
            CalendarEvent.tenant_id == tenant_id,
            CalendarEvent.user_id == user_id,
            CalendarEvent.start_time >= now,
        )
    )
    upcoming_result = await session.execute(upcoming_query)
    upcoming = upcoming_result.scalar()

    # Today's events
    from datetime import date, time

    today_start = datetime.combine(date.today(), time.min)
    today_end = datetime.combine(date.today(), time.max)

    today_query = (
        select(func.count())
        .select_from(CalendarEvent)
        .where(
            CalendarEvent.tenant_id == tenant_id,
            CalendarEvent.user_id == user_id,
            CalendarEvent.start_time >= today_start,
            CalendarEvent.start_time <= today_end,
        )
    )
    today_result = await session.execute(today_query)
    today = today_result.scalar()

    return {
        "total": total,
        "upcoming": upcoming,
        "today": today,
    }


@router.post("/sync")
async def trigger_calendar_sync(
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """Trigger calendar synchronization from Google and Outlook."""
    user_id = (
        current_user["user_id"]
        if isinstance(current_user["user_id"], uuid.UUID)
        else uuid.UUID(str(current_user["user_id"]))
    )

    calendar_sync = get_calendar_sync_service()

    try:
        results = await calendar_sync.sync_all(session, tenant_id, user_id)
        return {
            "status": "success",
            "results": results,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")
