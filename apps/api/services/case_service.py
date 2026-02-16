"""Case service — async CRUD with pagination and filtering."""

import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.models.case import Case


async def create_case(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    **kwargs,
) -> Case:
    """Create a new case within the tenant scope."""
    case = Case(tenant_id=tenant_id, **kwargs)
    session.add(case)
    await session.flush()
    await session.refresh(case)
    return case


async def get_case(
    session: AsyncSession,
    case_id: uuid.UUID,
) -> Case | None:
    """Get a single case by ID (RLS filters by tenant)."""
    result = await session.execute(select(Case).where(Case.id == case_id))
    return result.scalar_one_or_none()


async def list_cases(
    session: AsyncSession,
    page: int = 1,
    per_page: int = 20,
    status: Optional[str] = None,
    matter_type: Optional[str] = None,
    responsible_user_id: Optional[uuid.UUID] = None,
) -> tuple[list[Case], int]:
    """List cases with pagination and optional filters.

    Returns (items, total_count).
    RLS automatically filters by tenant.
    """
    query = select(Case)

    if status:
        query = query.where(Case.status == status)
    if matter_type:
        query = query.where(Case.matter_type == matter_type)
    if responsible_user_id:
        query = query.where(Case.responsible_user_id == responsible_user_id)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar_one()

    # Paginate
    query = query.order_by(Case.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await session.execute(query)
    items = list(result.scalars().all())

    return items, total


async def update_case(
    session: AsyncSession,
    case_id: uuid.UUID,
    **kwargs,
) -> Case | None:
    """Update a case by ID. Only updates non-None fields."""
    case = await get_case(session, case_id)
    if case is None:
        return None

    for key, value in kwargs.items():
        if value is not None:
            setattr(case, key, value)

    await session.flush()
    await session.refresh(case)
    return case


async def conflict_check(
    session: AsyncSession,
    case_id: uuid.UUID,
) -> dict:
    """Stub: Check for conflicts of interest on a case.

    Will be implemented with Neo4j graph traversal in Sprint 2.
    Returns a placeholder result.
    """
    case = await get_case(session, case_id)
    if case is None:
        return {"status": "error", "detail": "Case not found"}

    return {
        "status": "clear",
        "case_id": str(case_id),
        "conflicts_found": 0,
        "detail": "No conflicts detected (stub — full graph check in Sprint 2)",
    }
