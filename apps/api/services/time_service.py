"""Time entry service — CRUD with rounding logic and approval workflow."""

import math
import uuid
from datetime import date
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.models.time_entry import TimeEntry


def apply_rounding(minutes: int, rule: str) -> int:
    """Apply rounding rule to duration in minutes.

    Rules:
    - 6min:  round up to nearest 6 minutes
    - 10min: round up to nearest 10 minutes
    - 15min: round up to nearest 15 minutes
    - none:  no rounding
    """
    if rule == "none" or minutes <= 0:
        return minutes

    increments = {"6min": 6, "10min": 10, "15min": 15}
    inc = increments.get(rule, 6)
    return math.ceil(minutes / inc) * inc


async def create_time_entry(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    case_id: uuid.UUID,
    description: str,
    duration_minutes: int,
    entry_date: date,
    billable: bool = True,
    rounding_rule: str = "6min",
    source: str = "MANUAL",
    hourly_rate_cents: int | None = None,
) -> TimeEntry:
    """Create a time entry with rounding applied."""
    rounded = apply_rounding(duration_minutes, rounding_rule)
    entry = TimeEntry(
        tenant_id=tenant_id,
        case_id=case_id,
        user_id=user_id,
        description=description,
        duration_minutes=rounded,
        billable=billable,
        date=entry_date,
        rounding_rule=rounding_rule,
        source=source,
        hourly_rate_cents=hourly_rate_cents,
    )
    session.add(entry)
    await session.flush()
    await session.refresh(entry)
    return entry


async def get_time_entry(
    session: AsyncSession,
    entry_id: uuid.UUID,
) -> TimeEntry | None:
    """Get a single time entry by ID (RLS filters by tenant)."""
    result = await session.execute(select(TimeEntry).where(TimeEntry.id == entry_id))
    return result.scalar_one_or_none()


async def list_time_entries(
    session: AsyncSession,
    page: int = 1,
    per_page: int = 20,
    case_id: Optional[uuid.UUID] = None,
    user_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> tuple[list[TimeEntry], int]:
    """List time entries with pagination and filters."""
    query = select(TimeEntry)

    if case_id:
        query = query.where(TimeEntry.case_id == case_id)
    if user_id:
        query = query.where(TimeEntry.user_id == user_id)
    if status:
        query = query.where(TimeEntry.status == status)
    if date_from:
        query = query.where(TimeEntry.date >= date_from)
    if date_to:
        query = query.where(TimeEntry.date <= date_to)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar_one()

    query = query.order_by(TimeEntry.date.desc(), TimeEntry.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await session.execute(query)
    items = list(result.scalars().all())
    return items, total


async def update_time_entry(
    session: AsyncSession,
    entry_id: uuid.UUID,
    **kwargs,
) -> TimeEntry | None:
    """Update a time entry (only allowed in draft status)."""
    entry = await get_time_entry(session, entry_id)
    if entry is None:
        return None

    if entry.status != "draft":
        return entry  # caller checks status

    # Re-apply rounding if duration changed
    if "duration_minutes" in kwargs and kwargs["duration_minutes"] is not None:
        rule = kwargs.get("rounding_rule") or entry.rounding_rule
        kwargs["duration_minutes"] = apply_rounding(kwargs["duration_minutes"], rule)

    for key, value in kwargs.items():
        if value is not None:
            setattr(entry, key, value)

    await session.flush()
    await session.refresh(entry)
    return entry


async def submit_time_entry(
    session: AsyncSession,
    entry_id: uuid.UUID,
) -> TimeEntry | None:
    """Submit a draft time entry for approval."""
    entry = await get_time_entry(session, entry_id)
    if entry is None:
        return None

    if entry.status != "draft":
        return entry

    entry.status = "submitted"
    await session.flush()
    await session.refresh(entry)
    return entry


async def approve_time_entry(
    session: AsyncSession,
    entry_id: uuid.UUID,
    approved_by: uuid.UUID,
) -> TimeEntry | None:
    """Approve a submitted time entry (partner action)."""
    entry = await get_time_entry(session, entry_id)
    if entry is None:
        return None

    if entry.status != "submitted":
        return entry

    entry.status = "approved"
    entry.approved_by = approved_by
    await session.flush()
    await session.refresh(entry)
    return entry
