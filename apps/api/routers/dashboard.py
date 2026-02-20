"""Dashboard router — aggregate statistics for the dashboard view."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_current_user, get_db_session
from packages.db.models.brain_action import BrainAction
from packages.db.models.brain_insight import BrainInsight
from packages.db.models.calendar_event import CalendarEvent
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

    try:
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
            select(func.count(EvidenceLink.id)).where(
                EvidenceLink.tenant_id == tenant_id
            )
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
    except Exception as e:
        logger.error("Failed to fetch dashboard stats: %s", e)
        raise HTTPException(
            status_code=500, detail="Failed to fetch dashboard statistics"
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


@router.get("/intelligence")
async def get_dashboard_intelligence(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    """Quick brain intelligence data for the dashboard.

    Returns:
        {
            "critical_insights_count": int,
            "pending_actions_count": int,
            "cases_at_risk_count": int,
            "upcoming_deadlines": [...],
            "recent_brain_actions": [...],
        }
    """
    tenant_id = current_user["tenant_id"]
    now = datetime.now(timezone.utc)

    try:
        # Critical insights count (high + critical, not dismissed)
        critical_insights_count = await session.scalar(
            select(func.count(BrainInsight.id))
            .where(BrainInsight.tenant_id == tenant_id)
            .where(BrainInsight.dismissed.is_(False))
            .where(BrainInsight.severity.in_(["high", "critical"]))
        )

        # Pending actions count
        pending_actions_count = await session.scalar(
            select(func.count(BrainAction.id))
            .where(BrainAction.tenant_id == tenant_id)
            .where(BrainAction.status == "pending")
        )

        # Cases at risk (cases with high/critical insights)
        cases_at_risk_count = await session.scalar(
            select(func.count(func.distinct(BrainInsight.case_id)))
            .where(BrainInsight.tenant_id == tenant_id)
            .where(BrainInsight.dismissed.is_(False))
            .where(BrainInsight.severity.in_(["high", "critical"]))
        )

        # Upcoming deadlines (next 7 days)
        deadline_rows = (
            await session.execute(
                select(CalendarEvent, Case.title.label("case_title"))
                .outerjoin(Case, Case.id == CalendarEvent.case_id)
                .where(CalendarEvent.tenant_id == tenant_id)
                .where(CalendarEvent.start_time >= now)
                .where(CalendarEvent.start_time <= now + timedelta(days=7))
                .order_by(CalendarEvent.start_time.asc())
                .limit(10)
            )
        ).all()

        upcoming_deadlines = [
            {
                "title": event.title,
                "date": event.start_time.isoformat(),
                "days_remaining": max(0, (event.start_time - now).days),
                "case_id": str(event.case_id) if event.case_id else None,
                "case_title": case_title,
            }
            for event, case_title in deadline_rows
        ]

        # Recent brain actions (last 5)
        recent_actions_rows = (
            (
                await session.execute(
                    select(BrainAction)
                    .where(BrainAction.tenant_id == tenant_id)
                    .order_by(BrainAction.created_at.desc())
                    .limit(5)
                )
            )
            .scalars()
            .all()
        )

        recent_brain_actions = [
            {
                "id": str(a.id),
                "case_id": str(a.case_id),
                "action_type": a.action_type,
                "priority": a.priority,
                "status": a.status,
                "created_at": a.created_at.isoformat(),
            }
            for a in recent_actions_rows
        ]

    except Exception as e:
        logger.error("Failed to fetch dashboard intelligence: %s", e)
        raise HTTPException(
            status_code=500, detail="Erreur lors du chargement de l'intelligence"
        )

    return {
        "critical_insights_count": critical_insights_count or 0,
        "pending_actions_count": pending_actions_count or 0,
        "cases_at_risk_count": cases_at_risk_count or 0,
        "upcoming_deadlines": upcoming_deadlines,
        "recent_brain_actions": recent_brain_actions,
    }
