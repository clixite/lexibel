"""Contact service — async CRUD with search."""
import uuid
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.models.contact import Contact


async def create_contact(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    **kwargs,
) -> Contact:
    """Create a new contact within the tenant scope."""
    contact = Contact(tenant_id=tenant_id, **kwargs)
    session.add(contact)
    await session.flush()
    await session.refresh(contact)
    return contact


async def get_contact(
    session: AsyncSession,
    contact_id: uuid.UUID,
) -> Contact | None:
    """Get a single contact by ID (RLS filters by tenant)."""
    result = await session.execute(select(Contact).where(Contact.id == contact_id))
    return result.scalar_one_or_none()


async def list_contacts(
    session: AsyncSession,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[Contact], int]:
    """List contacts with pagination. RLS filters by tenant."""
    query = select(Contact)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar_one()

    query = query.order_by(Contact.full_name.asc())
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await session.execute(query)
    items = list(result.scalars().all())

    return items, total


async def update_contact(
    session: AsyncSession,
    contact_id: uuid.UUID,
    **kwargs,
) -> Contact | None:
    """Update a contact by ID. Only updates non-None fields."""
    contact = await get_contact(session, contact_id)
    if contact is None:
        return None

    for key, value in kwargs.items():
        if value is not None:
            setattr(contact, key, value)

    await session.flush()
    await session.refresh(contact)
    return contact


async def search_contacts(
    session: AsyncSession,
    q: str,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[Contact], int]:
    """Search contacts by name, BCE number, or phone (E.164).

    Uses ILIKE for case-insensitive partial matching.
    RLS automatically filters by tenant.
    """
    pattern = f"%{q}%"
    query = select(Contact).where(
        or_(
            Contact.full_name.ilike(pattern),
            Contact.bce_number.ilike(pattern),
            Contact.phone_e164.ilike(pattern),
            Contact.email.ilike(pattern),
        )
    )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar_one()

    query = query.order_by(Contact.full_name.asc())
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await session.execute(query)
    items = list(result.scalars().all())

    return items, total
