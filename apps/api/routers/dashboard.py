"""Dashboard router — aggregate statistics for the dashboard view."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_current_user, get_db_session
from packages.db.models.case import Case
from packages.db.models.contact import Contact
from packages.db.models.evidence_link import EvidenceLink
from packages.db.models.inbox_item import InboxItem
from packages.db.models.invoice import Invoice
from packages.db.models.time_entry import TimeEntry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_dashboard_stats(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    """
    Get aggregate statistics for dashboard.

    Returns:
        {
            "total_cases": int,
            "total_contacts": int,
            "monthly_hours": float,
            "total_invoices": int,
            "total_documents": int,
            "pending_inbox": int,
        }
    """
    tenant_id = current_user["tenant_id"]

    # Count cases
    cases_count = await session.scalar(
        select(func.count(Case.id)).where(Case.tenant_id == tenant_id)
    )

    # Count contacts
    contacts_count = await session.scalar(
        select(func.count(Contact.id)).where(Contact.tenant_id == tenant_id)
    )

    # Count invoices
    invoices_count = await session.scalar(
        select(func.count(Invoice.id)).where(Invoice.tenant_id == tenant_id)
    )

    # Count documents (evidence links)
    documents_count = await session.scalar(
        select(func.count(EvidenceLink.id)).where(EvidenceLink.tenant_id == tenant_id)
    )

    # Count pending inbox items (status = DRAFT or PENDING)
    pending_inbox_count = await session.scalar(
        select(func.count(InboxItem.id))
        .where(InboxItem.tenant_id == tenant_id)
        .where(InboxItem.status.in_(["DRAFT", "PENDING"]))
    )

    # Sum monthly hours (this month)
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    monthly_hours = await session.scalar(
        select(func.coalesce(func.sum(TimeEntry.duration), 0))
        .where(TimeEntry.tenant_id == tenant_id)
        .where(TimeEntry.date >= month_start)
    )

    return {
        "stats": {
            "total_cases": cases_count or 0,
            "total_contacts": contacts_count or 0,
            "monthly_hours": float(monthly_hours or 0),
            "total_invoices": invoices_count or 0,
            "total_documents": documents_count or 0,
            "pending_inbox": pending_inbox_count or 0,
        }
    }
