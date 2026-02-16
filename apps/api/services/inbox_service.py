"""Inbox service — human-in-the-loop queue for unvalidated items."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.models.inbox_item import InboxItem
from packages.db.models.interaction_event import InteractionEvent
from packages.db.models.case import Case


async def list_inbox(
    session: AsyncSession,
    page: int = 1,
    per_page: int = 20,
    status: Optional[str] = None,
) -> tuple[list[InboxItem], int]:
    """List inbox items with pagination and optional status filter.

    RLS automatically filters by tenant.
    """
    query = select(InboxItem)

    if status:
        query = query.where(InboxItem.status == status)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar_one()

    query = query.order_by(InboxItem.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await session.execute(query)
    items = list(result.scalars().all())

    return items, total


async def create_inbox_item(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    source: str = "MANUAL",
    raw_payload: dict | None = None,
    suggested_case_id: uuid.UUID | None = None,
) -> InboxItem:
    """Create a new inbox item (e.g. manual entry)."""
    item = InboxItem(
        tenant_id=tenant_id,
        source=source,
        raw_payload=raw_payload or {},
        suggested_case_id=suggested_case_id,
    )
    session.add(item)
    await session.flush()
    await session.refresh(item)
    return item


async def get_inbox_item(
    session: AsyncSession,
    item_id: uuid.UUID,
) -> InboxItem | None:
    """Get a single inbox item by ID (RLS filters by tenant)."""
    result = await session.execute(select(InboxItem).where(InboxItem.id == item_id))
    return result.scalar_one_or_none()


async def validate_inbox_item(
    session: AsyncSession,
    item_id: uuid.UUID,
    *,
    case_id: uuid.UUID,
    event_type: str,
    title: str,
    body: str | None = None,
    validated_by: uuid.UUID,
) -> tuple[InboxItem | None, InteractionEvent | None]:
    """Validate an inbox item: create an InteractionEvent and mark as VALIDATED.

    Returns (updated_item, created_event) or (None, None) if not found.
    """
    item = await get_inbox_item(session, item_id)
    if item is None:
        return None, None

    if item.status != "DRAFT":
        return item, None

    now = datetime.now(timezone.utc)

    # Create the interaction event from the inbox item
    event = InteractionEvent(
        tenant_id=item.tenant_id,
        case_id=case_id,
        source=item.source,
        event_type=event_type,
        title=title,
        body=body,
        occurred_at=now,
        metadata_=item.raw_payload,
        created_by=validated_by,
    )
    session.add(event)

    # Mark inbox item as validated
    item.status = "VALIDATED"
    item.validated_by = validated_by
    item.validated_at = now

    await session.flush()
    await session.refresh(event)
    await session.refresh(item)

    return item, event


async def refuse_inbox_item(
    session: AsyncSession,
    item_id: uuid.UUID,
    *,
    validated_by: uuid.UUID,
) -> InboxItem | None:
    """Refuse an inbox item: mark as REFUSED without creating an event."""
    item = await get_inbox_item(session, item_id)
    if item is None:
        return None

    if item.status != "DRAFT":
        return item

    item.status = "REFUSED"
    item.validated_by = validated_by
    item.validated_at = datetime.now(timezone.utc)

    await session.flush()
    await session.refresh(item)
    return item


async def create_case_from_inbox(
    session: AsyncSession,
    item_id: uuid.UUID,
    *,
    reference: str,
    title: str,
    matter_type: str,
    responsible_user_id: uuid.UUID,
    validated_by: uuid.UUID,
) -> tuple[InboxItem | None, Case | None, InteractionEvent | None]:
    """Create a new case from an inbox item and validate it in one step.

    Returns (item, case, event) or (None, None, None) if not found.
    """
    item = await get_inbox_item(session, item_id)
    if item is None:
        return None, None, None

    if item.status != "DRAFT":
        return item, None, None

    now = datetime.now(timezone.utc)

    # Create the case
    case = Case(
        tenant_id=item.tenant_id,
        reference=reference,
        title=title,
        matter_type=matter_type,
        responsible_user_id=responsible_user_id,
    )
    session.add(case)
    await session.flush()
    await session.refresh(case)

    # Create the interaction event linked to the new case
    event = InteractionEvent(
        tenant_id=item.tenant_id,
        case_id=case.id,
        source=item.source,
        event_type="DOCUMENT",
        title=title,
        occurred_at=now,
        metadata_=item.raw_payload,
        created_by=validated_by,
    )
    session.add(event)

    # Mark inbox item as validated
    item.status = "VALIDATED"
    item.validated_by = validated_by
    item.validated_at = now

    await session.flush()
    await session.refresh(event)
    await session.refresh(item)

    return item, case, event
