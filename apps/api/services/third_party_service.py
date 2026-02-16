"""Third-party account service — append-only ledger (compte de tiers).

OBFG/OVB compliance: entries are INSERT-only. Corrections are reversal entries.
"""

import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.models.third_party_entry import ThirdPartyEntry


async def create_entry(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    case_id: uuid.UUID,
    entry_type: str,
    amount_cents: int,
    description: str,
    reference: str,
    entry_date: date,
    created_by: uuid.UUID,
) -> ThirdPartyEntry:
    """Create a third-party account entry (append-only)."""
    entry = ThirdPartyEntry(
        tenant_id=tenant_id,
        case_id=case_id,
        entry_type=entry_type,
        amount_cents=amount_cents,
        description=description,
        reference=reference,
        entry_date=entry_date,
        created_by=created_by,
    )
    session.add(entry)
    await session.flush()
    await session.refresh(entry)
    return entry


async def list_by_case(
    session: AsyncSession,
    case_id: uuid.UUID,
    page: int = 1,
    per_page: int = 50,
) -> tuple[list[ThirdPartyEntry], int]:
    """List all third-party entries for a case (paginated)."""
    query = select(ThirdPartyEntry).where(ThirdPartyEntry.case_id == case_id)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar_one()

    query = query.order_by(
        ThirdPartyEntry.entry_date.desc(), ThirdPartyEntry.created_at.desc()
    )
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await session.execute(query)
    items = list(result.scalars().all())
    return items, total


async def calculate_balance(
    session: AsyncSession,
    case_id: uuid.UUID,
) -> dict:
    """Calculate the balance of a case's third-party account.

    Returns deposits, withdrawals, interest, and net balance.
    """
    query = (
        select(
            ThirdPartyEntry.entry_type,
            func.sum(ThirdPartyEntry.amount_cents).label("total"),
        )
        .where(ThirdPartyEntry.case_id == case_id)
        .group_by(ThirdPartyEntry.entry_type)
    )

    result = await session.execute(query)
    rows = result.all()

    totals = {"deposit": 0, "withdrawal": 0, "interest": 0}
    for entry_type, total in rows:
        totals[entry_type] = int(total)

    balance = totals["deposit"] + totals["interest"] - totals["withdrawal"]

    return {
        "case_id": case_id,
        "deposits": totals["deposit"],
        "withdrawals": totals["withdrawal"],
        "interest": totals["interest"],
        "balance": balance,
    }
