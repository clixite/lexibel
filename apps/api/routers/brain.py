"""Brain Intelligence Router — AI-powered case intelligence for lawyers.

Provides:
- Case analysis with risk assessment and completeness scoring
- Dashboard-level intelligence summary
- Smart action suggestions with approval workflow
- Deadline intelligence with Belgian legal deadlines
- Communication health scoring
- Insight management (list, dismiss)
- Document, billing, and client intelligence
- Intelligent dossier/contact creation assistants

Helpers and constants are in brain_helpers.py and brain_legal_knowledge.py.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_current_user, get_db_session
from apps.api.routers.brain_helpers import (
    compute_case_health,
    compute_completeness,
    compute_risk_assessment,
    deadline_urgency,
    generate_action_suggestions,
    generate_strategy_suggestions,
)
from apps.api.routers.brain_legal_knowledge import (
    BELGIAN_LEGAL_KNOWLEDGE,
    estimate_complexity,
)
from apps.api.schemas.brain import (
    ActionFeedbackRequest,
    ActionSuggestionResponse,
    BrainActionResponse,
    BrainInsightListResponse,
    BrainSummaryResponse,
    CaseAnalysisResponse,
    CaseHealthResponse,
    ContactAssistRequest,
    ContactAssistResponse,
    DeadlineResponse,
    DossierCreationAssistRequest,
    DossierCreationAssistResponse,
    InsightDismissRequest,
    InsightResponse,
    WorkloadWeek,
)
from packages.db.models.brain_action import BrainAction
from packages.db.models.brain_insight import BrainInsight
from packages.db.models.calendar_event import CalendarEvent
from packages.db.models.case import Case
from packages.db.models.invoice import Invoice
from packages.db.models.time_entry import TimeEntry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/brain", tags=["brain"])


# ── Endpoint 1: GET /summary ─────────────────────────────────────────


@router.get("/summary", response_model=BrainSummaryResponse)
async def get_brain_summary(
    days_ahead: int = Query(14, ge=1, le=90),
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> BrainSummaryResponse:
    """Dashboard-level intelligence summary across all cases."""
    tenant_id = current_user["tenant_id"]
    now = datetime.now(timezone.utc)

    try:
        total_active = await session.scalar(
            select(func.count(Case.id))
            .where(Case.tenant_id == tenant_id)
            .where(Case.status.in_(["open", "in_progress", "pending"]))
        )

        pending_actions_rows = (
            (
                await session.execute(
                    select(BrainAction)
                    .where(BrainAction.tenant_id == tenant_id)
                    .where(BrainAction.status == "pending")
                    .order_by(
                        func.case(
                            (BrainAction.priority == "critical", 1),
                            (BrainAction.priority == "urgent", 2),
                            else_=3,
                        )
                    )
                    .limit(20)
                )
            )
            .scalars()
            .all()
        )

        pending_actions = [
            ActionSuggestionResponse(
                action_type=a.action_type,
                title=a.action_data.get("title", a.action_type),
                description=a.action_data.get("description", ""),
                priority=a.priority,
                confidence=a.confidence_score,
                trigger_source=a.trigger_source,
                generated_content=a.generated_content,
            )
            for a in pending_actions_rows
        ]

        recent_insights_rows = (
            (
                await session.execute(
                    select(BrainInsight)
                    .where(BrainInsight.tenant_id == tenant_id)
                    .where(BrainInsight.dismissed.is_(False))
                    .order_by(BrainInsight.created_at.desc())
                    .limit(20)
                )
            )
            .scalars()
            .all()
        )

        recent_insights = [
            InsightResponse(
                id=str(i.id),
                insight_type=i.insight_type,
                severity=i.severity,
                title=i.title,
                description=i.description,
                suggested_actions=list(i.suggested_actions)
                if i.suggested_actions
                else [],
                case_id=str(i.case_id),
                dismissed=i.dismissed,
            )
            for i in recent_insights_rows
        ]

        deadline_rows = (
            await session.execute(
                select(CalendarEvent, Case.title.label("case_title"))
                .outerjoin(Case, Case.id == CalendarEvent.case_id)
                .where(CalendarEvent.tenant_id == tenant_id)
                .where(CalendarEvent.start_time >= now)
                .where(CalendarEvent.start_time <= now + timedelta(days=days_ahead))
                .order_by(CalendarEvent.start_time.asc())
                .limit(30)
            )
        ).all()

        critical_deadlines = [
            DeadlineResponse(
                title=event.title,
                date=event.start_time.isoformat(),
                days_remaining=max(0, (event.start_time - now).days),
                urgency=deadline_urgency((event.start_time - now).days),
                case_id=str(event.case_id) if event.case_id else None,
                case_title=case_title,
            )
            for event, case_title in deadline_rows
        ]

        active_cases = (
            (
                await session.execute(
                    select(Case)
                    .where(Case.tenant_id == tenant_id)
                    .where(Case.status.in_(["open", "in_progress", "pending"]))
                )
            )
            .scalars()
            .all()
        )

        risk_dist = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        cases_needing_attention = []

        for case in active_cases:
            risk = await compute_risk_assessment(session, case, tenant_id)
            risk_dist[risk.level] = risk_dist.get(risk.level, 0) + 1
            if risk.level in ("high", "critical"):
                cases_needing_attention.append(
                    {
                        "case_id": str(case.id),
                        "title": case.title,
                        "reason": f"Risque {risk.level} ({risk.overall_score}/100)",
                        "urgency": risk.level,
                    }
                )

        workload_weeks = []
        for week_offset in range(4):
            week_start = now + timedelta(weeks=week_offset)
            week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
            week_start = week_start - timedelta(days=week_start.weekday())
            week_end = week_start + timedelta(days=6)

            week_deadlines = await session.scalar(
                select(func.count(CalendarEvent.id))
                .where(CalendarEvent.tenant_id == tenant_id)
                .where(CalendarEvent.start_time >= week_start)
                .where(CalendarEvent.start_time <= week_end)
            )
            week_cases = await session.scalar(
                select(func.count(func.distinct(CalendarEvent.case_id)))
                .where(CalendarEvent.tenant_id == tenant_id)
                .where(CalendarEvent.case_id.isnot(None))
                .where(CalendarEvent.start_time >= week_start)
                .where(CalendarEvent.start_time <= week_end)
            )

            estimated_hours = (week_deadlines or 0) * 2.0
            workload_weeks.append(
                WorkloadWeek(
                    week_start=week_start.date().isoformat(),
                    week_end=week_end.date().isoformat(),
                    deadline_count=week_deadlines or 0,
                    cases_count=week_cases or 0,
                    estimated_hours=estimated_hours,
                    overload=estimated_hours > 40,
                )
            )

        total_insights = await session.scalar(
            select(func.count(BrainInsight.id))
            .where(BrainInsight.tenant_id == tenant_id)
            .where(BrainInsight.dismissed.is_(False))
        )
        total_pending_actions = await session.scalar(
            select(func.count(BrainAction.id))
            .where(BrainAction.tenant_id == tenant_id)
            .where(BrainAction.status == "pending")
        )

        stats = {
            "total_insights": total_insights or 0,
            "total_pending_actions": total_pending_actions or 0,
            "cases_at_risk": risk_dist.get("high", 0) + risk_dist.get("critical", 0),
            "deadlines_this_period": len(critical_deadlines),
        }

    except Exception as e:
        logger.error("Failed to compute brain summary: %s", e)
        raise HTTPException(
            status_code=500, detail="Erreur lors du calcul du resume intelligence"
        )

    return BrainSummaryResponse(
        total_active_cases=total_active or 0,
        risk_distribution=risk_dist,
        critical_deadlines=critical_deadlines,
        pending_actions=pending_actions,
        recent_insights=recent_insights,
        workload_next_weeks=workload_weeks,
        cases_needing_attention=cases_needing_attention,
        stats=stats,
    )


# ── Endpoint 2: POST /analyze/{case_id} ──────────────────────────────


@router.post("/analyze/{case_id}", response_model=CaseAnalysisResponse)
async def analyze_case(
    case_id: uuid.UUID,
    include_strategy: bool = Query(True),
    include_completeness: bool = Query(True),
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> CaseAnalysisResponse:
    """Full case analysis with risk assessment, completeness, and strategy."""
    tenant_id = current_user["tenant_id"]

    case = await session.scalar(
        select(Case).where(Case.tenant_id == tenant_id).where(Case.id == case_id)
    )
    if not case:
        raise HTTPException(status_code=404, detail="Dossier introuvable")

    try:
        risk = await compute_risk_assessment(session, case, tenant_id)

        completeness = None
        if include_completeness:
            completeness = await compute_completeness(session, case, tenant_id)

        health = await compute_case_health(session, case, tenant_id)

        strategy_suggestions = []
        if include_strategy:
            strategy_suggestions = generate_strategy_suggestions(case, risk, health)

        action_suggestions = generate_action_suggestions(case, risk, health)
        analyzed_at = datetime.now(timezone.utc)

        if risk.overall_score >= 50:
            insight = BrainInsight(
                tenant_id=tenant_id,
                case_id=case.id,
                insight_type="risk",
                severity=risk.level,
                title=f"Risque {risk.level} detecte sur {case.reference}",
                description=f"Score de risque: {risk.overall_score}/100. "
                + "; ".join(risk.recommendations[:2]),
                suggested_actions=risk.recommendations[:3],
            )
            session.add(insight)

        if completeness and completeness.score < 60:
            missing_labels = [m.label_fr for m in completeness.missing[:3]]
            insight = BrainInsight(
                tenant_id=tenant_id,
                case_id=case.id,
                insight_type="gap",
                severity="high" if completeness.score < 40 else "medium",
                title=f"Dossier incomplet: {case.reference}",
                description=f"Score de completude: {completeness.score}/100. "
                f"Elements manquants: {', '.join(missing_labels)}",
                suggested_actions=[f"Ajouter: {label}" for label in missing_labels],
            )
            session.add(insight)

        for action in action_suggestions:
            brain_action = BrainAction(
                tenant_id=tenant_id,
                case_id=case.id,
                action_type=action.action_type,
                priority=action.priority,
                status="pending",
                confidence_score=action.confidence,
                trigger_source=action.trigger_source,
                action_data={
                    "title": action.title,
                    "description": action.description,
                },
                generated_content=action.generated_content,
            )
            session.add(brain_action)

        await session.flush()

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to analyze case %s: %s", case_id, e)
        raise HTTPException(
            status_code=500, detail="Erreur lors de l'analyse du dossier"
        )

    return CaseAnalysisResponse(
        case_id=str(case.id),
        risk_assessment=risk,
        completeness=completeness,
        health=health,
        strategy_suggestions=strategy_suggestions,
        suggested_actions=action_suggestions,
        analyzed_at=analyzed_at,
    )


# ── Endpoint 3: GET /insights ────────────────────────────────────────


@router.get("/insights", response_model=BrainInsightListResponse)
async def list_insights(
    severity: Optional[str] = Query(None),
    insight_type: Optional[str] = Query(None),
    case_id: Optional[uuid.UUID] = Query(None),
    dismissed: bool = Query(False),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> BrainInsightListResponse:
    """List brain insights with filters."""
    tenant_id = current_user["tenant_id"]

    try:
        query = (
            select(BrainInsight)
            .where(BrainInsight.tenant_id == tenant_id)
            .where(BrainInsight.dismissed == dismissed)
        )
        count_query = (
            select(func.count(BrainInsight.id))
            .where(BrainInsight.tenant_id == tenant_id)
            .where(BrainInsight.dismissed == dismissed)
        )

        if severity:
            query = query.where(BrainInsight.severity == severity)
            count_query = count_query.where(BrainInsight.severity == severity)
        if insight_type:
            query = query.where(BrainInsight.insight_type == insight_type)
            count_query = count_query.where(BrainInsight.insight_type == insight_type)
        if case_id:
            query = query.where(BrainInsight.case_id == case_id)
            count_query = count_query.where(BrainInsight.case_id == case_id)

        total = await session.scalar(count_query)

        rows = (
            (
                await session.execute(
                    query.order_by(BrainInsight.created_at.desc())
                    .offset((page - 1) * per_page)
                    .limit(per_page)
                )
            )
            .scalars()
            .all()
        )

        items = [
            InsightResponse(
                id=str(i.id),
                insight_type=i.insight_type,
                severity=i.severity,
                title=i.title,
                description=i.description,
                suggested_actions=list(i.suggested_actions)
                if i.suggested_actions
                else [],
                case_id=str(i.case_id),
                dismissed=i.dismissed,
            )
            for i in rows
        ]

    except Exception as e:
        logger.error("Failed to list insights: %s", e)
        raise HTTPException(
            status_code=500, detail="Erreur lors de la recuperation des insights"
        )

    return BrainInsightListResponse(items=items, total=total or 0)


# ── Endpoint 4: POST /insights/{insight_id}/dismiss ──────────────────


@router.post("/insights/{insight_id}/dismiss")
async def dismiss_insight(
    insight_id: uuid.UUID,
    body: InsightDismissRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Dismiss an insight with optional reason."""
    tenant_id = current_user["tenant_id"]
    now = datetime.now(timezone.utc)

    try:
        result = await session.execute(
            update(BrainInsight)
            .where(BrainInsight.tenant_id == tenant_id)
            .where(BrainInsight.id == insight_id)
            .values(
                dismissed=True,
                dismissed_at=now,
                dismissed_by=current_user["user_id"],
            )
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Insight introuvable")
        await session.flush()

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to dismiss insight %s: %s", insight_id, e)
        raise HTTPException(status_code=500, detail="Erreur lors du rejet de l'insight")

    return {"status": "dismissed"}


# ── Endpoint 5: GET /actions ─────────────────────────────────────────


@router.get("/actions", response_model=list[BrainActionResponse])
async def list_actions(
    status_filter: Optional[str] = Query(None, alias="status"),
    priority: Optional[str] = Query(None),
    case_id: Optional[uuid.UUID] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> list[BrainActionResponse]:
    """List brain actions with filters."""
    tenant_id = current_user["tenant_id"]

    try:
        query = select(BrainAction).where(BrainAction.tenant_id == tenant_id)
        if status_filter:
            query = query.where(BrainAction.status == status_filter)
        if priority:
            query = query.where(BrainAction.priority == priority)
        if case_id:
            query = query.where(BrainAction.case_id == case_id)

        rows = (
            (
                await session.execute(
                    query.order_by(BrainAction.created_at.desc())
                    .offset((page - 1) * per_page)
                    .limit(per_page)
                )
            )
            .scalars()
            .all()
        )

        return [
            BrainActionResponse(
                id=str(a.id),
                case_id=str(a.case_id),
                action_type=a.action_type,
                priority=a.priority,
                status=a.status,
                confidence_score=a.confidence_score,
                trigger_source=a.trigger_source,
                generated_content=a.generated_content,
                created_at=a.created_at.isoformat(),
            )
            for a in rows
        ]

    except Exception as e:
        logger.error("Failed to list brain actions: %s", e)
        raise HTTPException(
            status_code=500, detail="Erreur lors de la recuperation des actions"
        )


# ── Endpoint 6: POST /actions/{action_id}/feedback ───────────────────


@router.post("/actions/{action_id}/feedback")
async def action_feedback(
    action_id: uuid.UUID,
    body: ActionFeedbackRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Approve, reject, or defer a brain action."""
    tenant_id = current_user["tenant_id"]

    try:
        status_map = {
            "approved": "approved",
            "rejected": "rejected",
            "deferred": "pending",
        }
        new_status = status_map.get(body.feedback, "pending")
        values: dict = {
            "status": new_status,
            "reviewed_by": current_user["user_id"],
            "feedback": body.notes,
        }
        if body.feedback == "approved":
            values["executed_at"] = datetime.now(timezone.utc)

        result = await session.execute(
            update(BrainAction)
            .where(BrainAction.tenant_id == tenant_id)
            .where(BrainAction.id == action_id)
            .values(**values)
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Action introuvable")
        await session.flush()

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update action %s: %s", action_id, e)
        raise HTTPException(
            status_code=500, detail="Erreur lors de la mise a jour de l'action"
        )

    return {"status": "updated"}


# ── Endpoint 7: GET /deadlines ───────────────────────────────────────


@router.get("/deadlines", response_model=list[DeadlineResponse])
async def list_deadlines(
    days_ahead: int = Query(30, ge=1, le=365),
    urgency: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> list[DeadlineResponse]:
    """Upcoming deadlines across all cases."""
    tenant_id = current_user["tenant_id"]
    now = datetime.now(timezone.utc)

    try:
        rows = (
            await session.execute(
                select(CalendarEvent, Case.title.label("case_title"))
                .outerjoin(Case, Case.id == CalendarEvent.case_id)
                .where(CalendarEvent.tenant_id == tenant_id)
                .where(CalendarEvent.start_time >= now)
                .where(CalendarEvent.start_time <= now + timedelta(days=days_ahead))
                .order_by(CalendarEvent.start_time.asc())
                .limit(100)
            )
        ).all()

        deadlines = []
        for event, case_title in rows:
            days_remaining = max(0, (event.start_time - now).days)
            urg = deadline_urgency(days_remaining)
            if urgency and urg != urgency:
                continue
            deadlines.append(
                DeadlineResponse(
                    title=event.title,
                    date=event.start_time.isoformat(),
                    days_remaining=days_remaining,
                    urgency=urg,
                    case_id=str(event.case_id) if event.case_id else None,
                    case_title=case_title,
                )
            )

    except Exception as e:
        logger.error("Failed to list deadlines: %s", e)
        raise HTTPException(
            status_code=500, detail="Erreur lors de la recuperation des echeances"
        )

    return deadlines


# ── Endpoint 8: GET /case/{case_id}/health ───────────────────────────


@router.get("/case/{case_id}/health", response_model=CaseHealthResponse)
async def get_case_health(
    case_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> CaseHealthResponse:
    """Quick health check for a specific case."""
    tenant_id = current_user["tenant_id"]

    case = await session.scalar(
        select(Case).where(Case.tenant_id == tenant_id).where(Case.id == case_id)
    )
    if not case:
        raise HTTPException(status_code=404, detail="Dossier introuvable")

    try:
        return await compute_case_health(session, case, tenant_id)
    except Exception as e:
        logger.error("Failed to compute health for case %s: %s", case_id, e)
        raise HTTPException(
            status_code=500, detail="Erreur lors du calcul de la sante du dossier"
        )


# ── Endpoint 9: GET /workload ────────────────────────────────────────


@router.get("/workload", response_model=list[WorkloadWeek])
async def get_workload(
    weeks: int = Query(4, ge=1, le=12),
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> list[WorkloadWeek]:
    """Workload prediction for the next N weeks."""
    tenant_id = current_user["tenant_id"]
    now = datetime.now(timezone.utc)

    try:
        workload_weeks = []
        for week_offset in range(weeks):
            week_start = now + timedelta(weeks=week_offset)
            week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
            week_start = week_start - timedelta(days=week_start.weekday())
            week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)

            week_deadlines = await session.scalar(
                select(func.count(CalendarEvent.id))
                .where(CalendarEvent.tenant_id == tenant_id)
                .where(CalendarEvent.start_time >= week_start)
                .where(CalendarEvent.start_time <= week_end)
            )
            week_cases = await session.scalar(
                select(func.count(func.distinct(CalendarEvent.case_id)))
                .where(CalendarEvent.tenant_id == tenant_id)
                .where(CalendarEvent.case_id.isnot(None))
                .where(CalendarEvent.start_time >= week_start)
                .where(CalendarEvent.start_time <= week_end)
            )

            historical_hours = await session.scalar(
                select(func.coalesce(func.sum(TimeEntry.duration_minutes), 0))
                .where(TimeEntry.tenant_id == tenant_id)
                .where(TimeEntry.date >= (week_start - timedelta(days=365)).date())
                .where(TimeEntry.date <= (week_end - timedelta(days=365)).date())
            )
            if historical_hours and historical_hours > 0:
                estimated_hours = round(historical_hours / 60.0, 1)
            else:
                estimated_hours = round((week_deadlines or 0) * 2.0, 1)

            workload_weeks.append(
                WorkloadWeek(
                    week_start=week_start.date().isoformat(),
                    week_end=week_end.date().isoformat(),
                    deadline_count=week_deadlines or 0,
                    cases_count=week_cases or 0,
                    estimated_hours=estimated_hours,
                    overload=estimated_hours > 40,
                )
            )

    except Exception as e:
        logger.error("Failed to compute workload: %s", e)
        raise HTTPException(
            status_code=500, detail="Erreur lors du calcul de la charge de travail"
        )

    return workload_weeks


# ── Endpoint 10: POST /document/analyze ──────────────────────────────


@router.post("/document/analyze")
async def analyze_document(
    body: dict,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Analyze a legal document — classify, extract clauses, detect risks."""
    text = body.get("text", "")
    filename = body.get("filename", "")

    if not text.strip():
        raise HTTPException(status_code=400, detail="Le texte du document est requis")

    try:
        from apps.api.services.brain.document_intelligence import DocumentIntelligence

        di = DocumentIntelligence()
        result = di.analyze(text, filename)

        return {
            "classification": {
                "document_type": result.classification.document_type,
                "sub_type": result.classification.sub_type,
                "confidence": result.classification.confidence,
                "language": result.classification.language,
            },
            "key_clauses": [
                {
                    "clause_type": c.clause_type,
                    "text": c.text,
                    "importance": c.importance,
                    "party": c.party,
                }
                for c in result.key_clauses
            ],
            "parties": result.parties,
            "dates": result.dates,
            "amounts": result.amounts,
            "legal_references": result.legal_references,
            "risks": result.risks,
            "summary_points": result.summary_points,
            "completeness_issues": result.completeness_issues,
        }

    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="Service d'intelligence documentaire non disponible",
        )
    except Exception as e:
        logger.error("Document analysis failed: %s", e)
        raise HTTPException(
            status_code=500, detail="Erreur lors de l'analyse du document"
        )


# ── Endpoint 11: GET /billing/report ─────────────────────────────────


@router.get("/billing/report")
async def get_billing_report(
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Generate billing intelligence report."""
    tenant_id = current_user["tenant_id"]

    try:
        from apps.api.services.brain.billing_intelligence import BillingIntelligence

        te_result = await session.execute(
            select(TimeEntry).where(TimeEntry.tenant_id == tenant_id)
        )
        time_entries_raw = te_result.scalars().all()

        inv_result = await session.execute(
            select(Invoice).where(Invoice.tenant_id == tenant_id)
        )
        invoices_raw = inv_result.scalars().all()

        cases_result = await session.execute(
            select(Case).where(Case.tenant_id == tenant_id)
        )
        cases_raw = cases_result.scalars().all()

        time_entries = [
            {
                "id": str(te.id),
                "case_id": str(te.case_id),
                "date": te.date.isoformat() if te.date else None,
                "duration_minutes": te.duration_minutes,
                "description": te.description,
                "hourly_rate": getattr(te, "hourly_rate", None),
                "invoiced": getattr(te, "invoiced", False),
            }
            for te in time_entries_raw
        ]

        invoices = [
            {
                "id": str(inv.id),
                "case_id": str(inv.case_id) if inv.case_id else None,
                "amount": float(inv.total_amount) if inv.total_amount else 0,
                "status": inv.status,
                "issued_at": inv.created_at.isoformat() if inv.created_at else None,
            }
            for inv in invoices_raw
        ]

        cases = [
            {
                "id": str(c.id),
                "title": c.title,
                "status": c.status,
                "reference": c.reference,
            }
            for c in cases_raw
        ]

        bi = BillingIntelligence()
        report = bi.analyze_billing(time_entries, invoices, cases)

        return {
            "total_unbilled_hours": report.total_unbilled_hours,
            "total_unbilled_amount": report.total_unbilled_amount,
            "recovery_rate": report.recovery_rate,
            "anomalies": [
                {
                    "anomaly_type": a.anomaly_type,
                    "severity": a.severity,
                    "description": a.description,
                    "case_id": a.case_id,
                    "amount_at_risk": a.amount_at_risk,
                    "recommended_action": a.recommended_action,
                }
                for a in report.anomalies
            ],
            "invoice_suggestions": [
                {
                    "case_id": s.case_id,
                    "case_title": s.case_title,
                    "unbilled_hours": s.unbilled_hours,
                    "estimated_amount": s.estimated_amount,
                    "last_invoice_date": s.last_invoice_date,
                    "days_since_last_invoice": s.days_since_last_invoice,
                    "urgency": s.urgency,
                }
                for s in report.invoice_suggestions
            ],
            "recommendations": report.recommendations,
        }

    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="Service d'intelligence facturation non disponible",
        )
    except Exception as e:
        logger.error("Billing report failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de la génération du rapport de facturation",
        )


# ── Endpoint 12: GET /client/{contact_id}/health ─────────────────────


@router.get("/client/{contact_id}/health")
async def get_client_health(
    contact_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Assess client relationship health."""
    from packages.db.models.case_contact import CaseContact
    from packages.db.models.contact import Contact

    tenant_id = current_user["tenant_id"]

    try:
        contact_result = await session.execute(
            select(Contact).where(
                Contact.id == contact_id, Contact.tenant_id == tenant_id
            )
        )
        contact = contact_result.scalar_one_or_none()
        if not contact:
            raise HTTPException(status_code=404, detail="Contact non trouvé")

        case_links = await session.execute(
            select(CaseContact.case_id).where(CaseContact.contact_id == contact_id)
        )
        case_ids = [row[0] for row in case_links.all()]

        active_cases = 0
        if case_ids:
            active_count = await session.scalar(
                select(func.count(Case.id))
                .where(Case.id.in_(case_ids))
                .where(Case.status.in_(["open", "in_progress", "pending"]))
            )
            active_cases = active_count or 0

        from apps.api.services.brain.client_intelligence import ClientIntelligence

        ci = ClientIntelligence()
        contact_data = {
            "id": str(contact.id),
            "name": contact.full_name,
            "email": contact.email,
            "type": contact.type,
        }
        health = ci.assess_client_health(
            contact=contact_data,
            cases=[{"id": str(cid), "status": "open"} for cid in case_ids],
            communications=[],
            time_entries=[],
        )

        return {
            "contact_id": str(contact.id),
            "contact_name": contact.full_name,
            "health_score": health.health_score,
            "status": health.status,
            "active_cases": active_cases,
            "days_since_contact": health.days_since_contact,
            "risk_factors": health.risk_factors,
            "recommended_actions": health.recommended_actions,
        }

    except HTTPException:
        raise
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="Service d'intelligence client non disponible",
        )
    except Exception as e:
        logger.error("Client health check failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de l'évaluation de la santé client",
        )


# ── Endpoint 13: POST /dossier/assist-creation ───────────────────────


@router.post("/dossier/assist-creation", response_model=DossierCreationAssistResponse)
async def assist_dossier_creation(
    body: DossierCreationAssistRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> DossierCreationAssistResponse:
    """Assistance intelligente a la creation d'un dossier."""
    _tenant_id = current_user["tenant_id"]  # noqa: F841 — RLS via session

    try:
        matter = body.matter_type.lower().strip()
        knowledge = BELGIAN_LEGAL_KNOWLEDGE.get(matter)

        if knowledge is None:
            knowledge = BELGIAN_LEGAL_KNOWLEDGE["civil"]
            suggested_jurisdiction = (
                f"A determiner (matiere '{body.matter_type}' non reconnue — "
                "verifier la competence selon le Code judiciaire)"
            )
            suggested_sub_type = None
        else:
            suggested_jurisdiction = knowledge["jurisdiction"]
            suggested_sub_type = None
            desc_lower = body.description.lower()
            for sub in knowledge.get("sub_types", []):
                if any(word in desc_lower for word in sub.split() if len(word) > 3):
                    suggested_sub_type = sub
                    break

        complexity = estimate_complexity(body.description, matter)

        strategy = knowledge.get("strategy_notes", "")
        if body.client_name:
            strategy += (
                f"\n\nNote: dossier initie pour le client {body.client_name}. "
                "Verifier l'absence de conflit d'interets."
            )

        return DossierCreationAssistResponse(
            suggested_jurisdiction=suggested_jurisdiction,
            suggested_sub_type=suggested_sub_type,
            applicable_deadlines=knowledge.get("deadlines", []),
            required_documents=knowledge.get("required_documents", []),
            risk_points=knowledge.get("risk_points", []),
            strategy_notes=strategy,
            estimated_complexity=complexity,
            belgian_legal_references=knowledge.get("legal_references", []),
        )

    except Exception as e:
        logger.error("Dossier assist-creation failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de l'assistance a la creation du dossier",
        )


# ── Endpoint 14: POST /contact/assist-creation ──────────────────────


@router.post("/contact/assist-creation", response_model=ContactAssistResponse)
async def assist_contact_creation(
    body: ContactAssistRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> ContactAssistResponse:
    """Assistance intelligente a la creation d'un contact."""
    from packages.db.models.contact import Contact

    _tenant_id = current_user["tenant_id"]  # noqa: F841 — RLS via session

    try:
        suggested_fields: dict = {}
        bce_info: dict | None = None
        duplicate_warning: dict | None = None
        compliance_notes: list[str] = []
        relationship_suggestions: list[str] = []

        pattern = f"%{body.full_name}%"
        dup_query = select(Contact).where(Contact.full_name.ilike(pattern))
        dup_result = await session.execute(dup_query)
        duplicates = dup_result.scalars().all()

        if duplicates:
            first = duplicates[0]
            duplicate_warning = {
                "potential_duplicates": len(duplicates),
                "first_match": {
                    "id": str(first.id),
                    "full_name": first.full_name,
                    "type": first.type,
                    "email": first.email,
                    "phone_e164": first.phone_e164,
                },
                "message": (
                    f"Attention: {len(duplicates)} contact(s) existant(s) "
                    f"avec un nom similaire a '{body.full_name}'."
                ),
            }

        if body.bce_number and body.type == "legal":
            clean_bce = body.bce_number.replace(".", "").replace(" ", "")
            if len(clean_bce) == 10:
                formatted_bce = f"{clean_bce[0:4]}.{clean_bce[4:7]}.{clean_bce[7:10]}"
                bce_info = {
                    "formatted_number": formatted_bce,
                    "lookup_url": (
                        f"https://kbopub.economie.fgov.be/kbopub/"
                        f"toonondernemingps.html?ondernemingsnummer={clean_bce}"
                    ),
                    "note": (
                        "Consultez la Banque-Carrefour des Entreprises (BCE) "
                        "pour verifier les informations officielles de l'entreprise."
                    ),
                }
                suggested_fields["bce_number"] = formatted_bce

            bce_dup_result = await session.execute(
                select(Contact).where(Contact.bce_number.ilike(f"%{clean_bce[-6:]}%"))
            )
            bce_duplicates = bce_dup_result.scalars().all()
            if bce_duplicates:
                if duplicate_warning is None:
                    duplicate_warning = {}
                duplicate_warning["bce_match"] = {
                    "count": len(bce_duplicates),
                    "message": (
                        f"Un contact avec un numero BCE similaire existe deja: "
                        f"{bce_duplicates[0].full_name}"
                    ),
                }

        if body.type == "natural":
            suggested_fields.update(
                {
                    "language": "fr",
                    "metadata_suggestions": {
                        "civility": "Indiquer: M., Mme, Me, Dr",
                        "birth_date": "Date de naissance (YYYY-MM-DD)",
                        "national_register": "Numero de registre national (11 chiffres)",
                        "nationality": "belge",
                        "profession": "Profession du contact",
                    },
                }
            )
            relationship_suggestions = [
                "client",
                "partie_adverse",
                "temoin",
                "expert",
                "magistrat",
                "confrere",
                "notaire",
                "huissier",
            ]
        elif body.type == "legal":
            suggested_fields.update(
                {
                    "language": "fr",
                    "metadata_suggestions": {
                        "forme_juridique": "SA, SRL, SC, ASBL, etc.",
                        "numero_tva": "BE 0xxx.xxx.xxx",
                        "siege_social": "Adresse du siege social",
                        "representant_legal": "Nom du representant legal",
                        "date_constitution": "Date de constitution (YYYY-MM-DD)",
                    },
                }
            )
            relationship_suggestions = [
                "client",
                "partie_adverse",
                "societe_liee",
                "fournisseur",
                "sous-traitant",
                "assureur",
                "banque",
            ]

        compliance_notes = [
            "RGPD — Art. 6: Verifier la base legale du traitement "
            "(interet legitime du cabinet dans le cadre du mandat).",
            "RGPD — Art. 13-14: Informer le contact du traitement de "
            "ses donnees (notice de confidentialite du cabinet).",
            "RGPD — Art. 17: Le contact dispose d'un droit a l'effacement, "
            "sauf obligation legale de conservation.",
            "Secret professionnel — Art. 458 C. pen.: Les donnees sont "
            "couvertes par le secret professionnel de l'avocat.",
            "Conservation — Respecter les delais de conservation "
            "recommandes par l'Ordre: 5 ans apres la cloture du dossier.",
        ]

        if body.type == "natural":
            compliance_notes.append(
                "RGPD — Art. 9: Si des donnees sensibles sont collectees "
                "(sante, origine ethnique, convictions), une base legale "
                "renforcee est necessaire."
            )
            compliance_notes.append(
                "Registre national — L'acces au numero de registre national "
                "est soumis a autorisation prealable (Loi du 8/08/1983)."
            )

        return ContactAssistResponse(
            suggested_fields=suggested_fields,
            bce_info=bce_info,
            duplicate_warning=duplicate_warning,
            compliance_notes=compliance_notes,
            relationship_suggestions=relationship_suggestions,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Contact assist-creation failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de l'assistance a la creation du contact",
        )
