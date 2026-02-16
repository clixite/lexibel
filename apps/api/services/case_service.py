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
    """Update a case by ID. Only updates non-None fields.

    Automatically logs status transitions to the timeline.
    """
    from datetime import datetime

    from packages.db.models.interaction_event import InteractionEvent

    case = await get_case(session, case_id)
    if case is None:
        return None

    # Track status change for timeline logging
    old_status = case.status
    status_changed = "status" in kwargs and kwargs["status"] != old_status

    for key, value in kwargs.items():
        if value is not None:
            setattr(case, key, value)

    await session.flush()

    # Log status transition to timeline
    if status_changed:
        event = InteractionEvent(
            tenant_id=case.tenant_id,
            case_id=case_id,
            source="MANUAL",
            event_type="STATUS_CHANGE",
            title=f"Statut modifié: {old_status} → {kwargs['status']}",
            body=f"Le statut du dossier a été modifié de '{old_status}' à '{kwargs['status']}'",
            occurred_at=datetime.utcnow(),
            metadata_={"old_status": old_status, "new_status": kwargs["status"]},
        )
        session.add(event)
        await session.flush()

    await session.refresh(case)
    return case


async def conflict_check(
    session: AsyncSession,
    case_id: uuid.UUID,
    contact_id: Optional[uuid.UUID] = None,
) -> dict:
    """Check for conflicts of interest on a case.

    Queries all other active cases for contacts in opposing roles.
    Opposing role pairs: client ↔ adverse, witness ↔ third_party.
    """
    from packages.db.models.case_contact import CaseContact
    from packages.db.models.contact import Contact

    case = await get_case(session, case_id)
    if case is None:
        return {"status": "error", "detail": "Case not found"}

    # Get all contacts linked to this case
    query = select(CaseContact).where(CaseContact.case_id == case_id)
    if contact_id:
        query = query.where(CaseContact.contact_id == contact_id)

    result = await session.execute(query)
    case_contacts = result.scalars().all()

    if not case_contacts:
        return {
            "status": "clear",
            "case_id": str(case_id),
            "conflicts_found": 0,
            "detail": "No contacts to check",
        }

    # Define opposing roles
    opposing_roles = {
        "client": "adverse",
        "adverse": "client",
        "witness": "third_party",
        "third_party": "witness",
    }

    conflicts = []

    for cc in case_contacts:
        # Find opposing role
        opposing_role = opposing_roles.get(cc.role)
        if not opposing_role:
            continue

        # Query other active cases where this contact appears in opposing role
        other_cases_query = (
            select(Case, CaseContact.role, Contact.full_name)
            .join(CaseContact, CaseContact.case_id == Case.id)
            .join(Contact, Contact.id == CaseContact.contact_id)
            .where(
                CaseContact.contact_id == cc.contact_id,
                CaseContact.role == opposing_role,
                Case.id != case_id,
                Case.status.in_(
                    ["open", "in_progress", "pending"]
                ),  # Active cases only
            )
        )

        other_result = await session.execute(other_cases_query)
        other_cases = other_result.all()

        for other_case, role, contact_name in other_cases:
            conflicts.append(
                {
                    "contact_id": str(cc.contact_id),
                    "contact_name": contact_name,
                    "current_role": cc.role,
                    "conflicting_case_id": str(other_case.id),
                    "conflicting_case_reference": other_case.reference,
                    "conflicting_role": role,
                }
            )

    return {
        "status": "warning" if conflicts else "clear",
        "case_id": str(case_id),
        "conflicts_found": len(conflicts),
        "conflicts": conflicts,
        "detail": f"Found {len(conflicts)} potential conflict(s)"
        if conflicts
        else "No conflicts detected",
    }
