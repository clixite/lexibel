"""Timeline service — append-only event store with pagination and filtering."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.models.evidence_link import EvidenceLink
from packages.db.models.interaction_event import InteractionEvent


async def create_event(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    source: str,
    event_type: str,
    title: str,
    occurred_at: datetime,
    case_id: uuid.UUID | None = None,
    body: str | None = None,
    metadata: dict | None = None,
    created_by: uuid.UUID | None = None,
) -> InteractionEvent:
    """Create an interaction event (append-only, never updated)."""
    event = InteractionEvent(
        tenant_id=tenant_id,
        case_id=case_id,
        source=source,
        event_type=event_type,
        title=title,
        body=body,
        occurred_at=occurred_at,
        metadata_=metadata or {},
        created_by=created_by,
    )
    session.add(event)
    await session.flush()
    await session.refresh(event)
    return event


async def get_event(
    session: AsyncSession,
    event_id: uuid.UUID,
) -> InteractionEvent | None:
    """Get a single event by ID (RLS filters by tenant)."""
    result = await session.execute(
        select(InteractionEvent).where(InteractionEvent.id == event_id)
    )
    return result.scalar_one_or_none()


async def get_event_with_evidence(
    session: AsyncSession,
    event_id: uuid.UUID,
) -> tuple[InteractionEvent | None, list[EvidenceLink]]:
    """Get an event with its evidence links."""
    event = await get_event(session, event_id)
    if event is None:
        return None, []

    result = await session.execute(
        select(EvidenceLink)
        .where(EvidenceLink.interaction_event_id == event_id)
        .order_by(EvidenceLink.created_at.asc())
    )
    links = list(result.scalars().all())
    return event, links


async def update_event(
    session: AsyncSession,
    event_id: uuid.UUID,
    **kwargs,
) -> InteractionEvent | None:
    """Update an event's mutable fields (title, body, event_type, metadata)."""
    event = await get_event(session, event_id)
    if event is None:
        return None

    for key, value in kwargs.items():
        if value is not None:
            if key == "metadata":
                setattr(event, "metadata_", value)
            else:
                setattr(event, key, value)

    await session.flush()
    await session.refresh(event)
    return event


async def delete_event(
    session: AsyncSession,
    event_id: uuid.UUID,
) -> bool:
    """Delete an event and its evidence links."""
    event = await get_event(session, event_id)
    if event is None:
        return False

    # Delete evidence links first
    from sqlalchemy import delete as sa_delete

    await session.execute(
        sa_delete(EvidenceLink).where(EvidenceLink.interaction_event_id == event_id)
    )
    await session.delete(event)
    await session.flush()
    return True


async def list_by_case(
    session: AsyncSession,
    case_id: uuid.UUID,
    page: int = 1,
    per_page: int = 20,
    source: Optional[str] = None,
    event_type: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> tuple[list[InteractionEvent], int]:
    """List events for a case with pagination and filters.

    RLS automatically filters by tenant.
    """
    query = select(InteractionEvent).where(InteractionEvent.case_id == case_id)

    if source:
        query = query.where(InteractionEvent.source == source)
    if event_type:
        query = query.where(InteractionEvent.event_type == event_type)
    if date_from:
        query = query.where(InteractionEvent.occurred_at >= date_from)
    if date_to:
        query = query.where(InteractionEvent.occurred_at <= date_to)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar_one()

    query = query.order_by(InteractionEvent.occurred_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await session.execute(query)
    items = list(result.scalars().all())

    return items, total
