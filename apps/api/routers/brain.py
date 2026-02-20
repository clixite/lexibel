"""Brain Intelligence Router — AI-powered case intelligence for lawyers.

Provides:
- Case analysis with risk assessment and completeness scoring
- Dashboard-level intelligence summary
- Smart action suggestions with approval workflow
- Deadline intelligence with Belgian legal deadlines
- Communication health scoring
- Insight management (list, dismiss)
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_current_user, get_db_session
from apps.api.schemas.brain import (
    ActionFeedbackRequest,
    ActionSuggestionResponse,
    BrainActionResponse,
    BrainInsightListResponse,
    BrainSummaryResponse,
    CaseAnalysisResponse,
    CaseHealthResponse,
    CompletenessItem,
    CompletenessResponse,
    DeadlineResponse,
    InsightDismissRequest,
    InsightResponse,
    RiskAssessmentResponse,
    RiskFactor,
    StrategySuggestionResponse,
    WorkloadWeek,
)
from packages.db.models.brain_action import BrainAction
from packages.db.models.brain_insight import BrainInsight
from packages.db.models.calendar_event import CalendarEvent
from packages.db.models.case import Case
from packages.db.models.evidence_link import EvidenceLink
from packages.db.models.interaction_event import InteractionEvent
from packages.db.models.invoice import Invoice
from packages.db.models.time_entry import TimeEntry
from packages.db.models.timeline_event import TimelineEvent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/brain", tags=["brain"])


# ── Helper: completeness checklist per matter type ───────────────────

COMPLETENESS_CHECKLISTS: dict[str, list[dict]] = {
    "civil": [
        {"element": "client_contact", "label_fr": "Contact client", "critical": True},
        {
            "element": "adverse_contact",
            "label_fr": "Partie adverse identifiee",
            "critical": True,
        },
        {"element": "mandate_letter", "label_fr": "Lettre de mandat", "critical": True},
        {
            "element": "timeline_events",
            "label_fr": "Chronologie des faits",
            "critical": True,
        },
        {
            "element": "key_documents",
            "label_fr": "Pieces justificatives",
            "critical": True,
        },
        {
            "element": "court_reference",
            "label_fr": "Reference du tribunal",
            "critical": False,
        },
        {
            "element": "billing_setup",
            "label_fr": "Facturation configuree",
            "critical": False,
        },
        {
            "element": "jurisdiction",
            "label_fr": "Juridiction determinee",
            "critical": True,
        },
    ],
    "penal": [
        {"element": "client_contact", "label_fr": "Contact client", "critical": True},
        {"element": "mandate_letter", "label_fr": "Lettre de mandat", "critical": True},
        {
            "element": "police_report",
            "label_fr": "Proces-verbal de police",
            "critical": True,
        },
        {
            "element": "timeline_events",
            "label_fr": "Chronologie des faits",
            "critical": True,
        },
        {
            "element": "court_reference",
            "label_fr": "Reference du tribunal",
            "critical": True,
        },
        {
            "element": "key_documents",
            "label_fr": "Pieces du dossier penal",
            "critical": True,
        },
        {"element": "witness_list", "label_fr": "Liste des temoins", "critical": False},
        {
            "element": "billing_setup",
            "label_fr": "Facturation configuree",
            "critical": False,
        },
    ],
    "family": [
        {"element": "client_contact", "label_fr": "Contact client", "critical": True},
        {
            "element": "adverse_contact",
            "label_fr": "Partie adverse identifiee",
            "critical": True,
        },
        {"element": "mandate_letter", "label_fr": "Lettre de mandat", "critical": True},
        {
            "element": "marriage_certificate",
            "label_fr": "Acte de mariage",
            "critical": False,
        },
        {
            "element": "timeline_events",
            "label_fr": "Chronologie des faits",
            "critical": True,
        },
        {
            "element": "key_documents",
            "label_fr": "Pieces justificatives",
            "critical": True,
        },
        {
            "element": "children_info",
            "label_fr": "Informations sur les enfants",
            "critical": False,
        },
        {
            "element": "billing_setup",
            "label_fr": "Facturation configuree",
            "critical": False,
        },
    ],
    "commercial": [
        {"element": "client_contact", "label_fr": "Contact client", "critical": True},
        {
            "element": "adverse_contact",
            "label_fr": "Partie adverse identifiee",
            "critical": True,
        },
        {"element": "mandate_letter", "label_fr": "Lettre de mandat", "critical": True},
        {"element": "contract", "label_fr": "Contrat litigieux", "critical": True},
        {
            "element": "timeline_events",
            "label_fr": "Chronologie des faits",
            "critical": True,
        },
        {
            "element": "key_documents",
            "label_fr": "Pieces justificatives",
            "critical": True,
        },
        {
            "element": "financial_docs",
            "label_fr": "Documents financiers",
            "critical": False,
        },
        {
            "element": "billing_setup",
            "label_fr": "Facturation configuree",
            "critical": False,
        },
    ],
}

# Default checklist for unknown matter types
DEFAULT_CHECKLIST = COMPLETENESS_CHECKLISTS["civil"]


# ── Helper: risk level from score ────────────────────────────────────


def _risk_level(score: int) -> str:
    """Return risk level string from numeric score."""
    if score >= 75:
        return "critical"
    if score >= 50:
        return "high"
    if score >= 25:
        return "medium"
    return "low"


def _health_status(score: int) -> str:
    """Return health status string from numeric score."""
    if score >= 80:
        return "healthy"
    if score >= 60:
        return "attention_needed"
    if score >= 40:
        return "at_risk"
    return "critical"


def _deadline_urgency(days: int) -> str:
    """Return urgency level for a deadline based on days remaining."""
    if days <= 2:
        return "critical"
    if days <= 7:
        return "urgent"
    if days <= 14:
        return "attention"
    return "normal"


# ── Helper: compute case risk assessment ─────────────────────────────


async def _compute_risk_assessment(
    session: AsyncSession,
    case: Case,
    tenant_id: uuid.UUID,
) -> RiskAssessmentResponse:
    """Compute risk assessment for a case based on real data."""
    now = datetime.now(timezone.utc)
    factors: list[RiskFactor] = []

    # Factor 1: Deadline proximity
    upcoming_deadlines = await session.scalar(
        select(func.count(CalendarEvent.id))
        .where(CalendarEvent.tenant_id == tenant_id)
        .where(CalendarEvent.case_id == case.id)
        .where(CalendarEvent.start_time >= now)
        .where(CalendarEvent.start_time <= now + timedelta(days=7))
    )
    deadline_score = min(100, (upcoming_deadlines or 0) * 25)
    factors.append(
        RiskFactor(
            name="deadline_proximity",
            score=deadline_score,
            weight=0.3,
            description="Echeances dans les 7 prochains jours",
            severity=_risk_level(deadline_score),
        )
    )

    # Factor 2: Communication gap (days since last interaction)
    last_interaction = await session.scalar(
        select(func.max(InteractionEvent.occurred_at))
        .where(InteractionEvent.tenant_id == tenant_id)
        .where(InteractionEvent.case_id == case.id)
    )
    if last_interaction:
        days_silent = (now - last_interaction).days
    else:
        days_silent = 90  # No interactions at all = high risk
    comm_score = min(100, days_silent * 3)
    factors.append(
        RiskFactor(
            name="communication_gap",
            score=comm_score,
            weight=0.25,
            description=f"Aucune communication depuis {days_silent} jours",
            severity=_risk_level(comm_score),
        )
    )

    # Factor 3: Document completeness (evidence links count)
    doc_count = await session.scalar(
        select(func.count(EvidenceLink.id))
        .join(
            InteractionEvent, InteractionEvent.id == EvidenceLink.interaction_event_id
        )
        .where(InteractionEvent.tenant_id == tenant_id)
        .where(InteractionEvent.case_id == case.id)
    )
    doc_score = max(0, 100 - min(100, (doc_count or 0) * 10))
    factors.append(
        RiskFactor(
            name="document_coverage",
            score=doc_score,
            weight=0.2,
            description=f"{doc_count or 0} documents au dossier",
            severity=_risk_level(doc_score),
        )
    )

    # Factor 4: Case age without resolution
    case_age_days = (now.date() - case.opened_at).days if case.opened_at else 0
    age_score = min(100, max(0, case_age_days - 90))  # Risk grows after 90 days
    factors.append(
        RiskFactor(
            name="case_age",
            score=age_score,
            weight=0.15,
            description=f"Dossier ouvert depuis {case_age_days} jours",
            severity=_risk_level(age_score),
        )
    )

    # Factor 5: Billing health (unbilled time)
    unbilled_entries = await session.scalar(
        select(func.count(TimeEntry.id))
        .where(TimeEntry.tenant_id == tenant_id)
        .where(TimeEntry.case_id == case.id)
        .where(TimeEntry.status == "draft")
        .where(TimeEntry.billable.is_(True))
    )
    billing_score = min(100, (unbilled_entries or 0) * 15)
    factors.append(
        RiskFactor(
            name="billing_health",
            score=billing_score,
            weight=0.1,
            description=f"{unbilled_entries or 0} prestations non facturees",
            severity=_risk_level(billing_score),
        )
    )

    # Overall weighted score
    overall = int(
        sum(f.score * f.weight for f in factors)
        / max(sum(f.weight for f in factors), 0.01)
    )

    # Recommendations
    recommendations = []
    if deadline_score >= 50:
        recommendations.append(
            "Verifier les echeances imminentes et preparer les documents necessaires"
        )
    if comm_score >= 50:
        recommendations.append(
            "Prendre contact avec le client pour un point de situation"
        )
    if doc_score >= 50:
        recommendations.append("Completer le dossier avec les pieces manquantes")
    if age_score >= 50:
        recommendations.append(
            "Evaluer l'avancement du dossier et definir les prochaines etapes"
        )
    if billing_score >= 50:
        recommendations.append("Regulariser la facturation des prestations en attente")

    return RiskAssessmentResponse(
        overall_score=overall,
        level=_risk_level(overall),
        factors=factors,
        recommendations=recommendations,
    )


# ── Helper: compute completeness ─────────────────────────────────────


async def _compute_completeness(
    session: AsyncSession,
    case: Case,
    tenant_id: uuid.UUID,
) -> CompletenessResponse:
    """Evaluate case completeness based on matter type checklist."""
    from packages.db.models.case_contact import CaseContact

    checklist = COMPLETENESS_CHECKLISTS.get(case.matter_type, DEFAULT_CHECKLIST)

    # Gather case data for checking
    contact_count = await session.scalar(
        select(func.count(CaseContact.id)).where(CaseContact.case_id == case.id)
    )
    adverse_count = await session.scalar(
        select(func.count(CaseContact.id))
        .where(CaseContact.case_id == case.id)
        .where(CaseContact.role == "adverse")
    )
    timeline_count = await session.scalar(
        select(func.count(TimelineEvent.id))
        .where(TimelineEvent.tenant_id == tenant_id)
        .where(TimelineEvent.case_id == case.id)
    )
    doc_count = await session.scalar(
        select(func.count(EvidenceLink.id))
        .join(
            InteractionEvent, InteractionEvent.id == EvidenceLink.interaction_event_id
        )
        .where(InteractionEvent.tenant_id == tenant_id)
        .where(InteractionEvent.case_id == case.id)
    )
    invoice_count = await session.scalar(
        select(func.count(Invoice.id))
        .where(Invoice.tenant_id == tenant_id)
        .where(Invoice.case_id == case.id)
    )

    # Check each element
    presence_map = {
        "client_contact": (contact_count or 0) > 0,
        "adverse_contact": (adverse_count or 0) > 0,
        "mandate_letter": (doc_count or 0) > 0,  # Approximation
        "timeline_events": (timeline_count or 0) >= 2,
        "key_documents": (doc_count or 0) >= 3,
        "court_reference": bool(case.court_reference),
        "billing_setup": (invoice_count or 0) > 0
        or bool(case.metadata_.get("billing_rate")),
        "jurisdiction": bool(case.jurisdiction),
        "police_report": (doc_count or 0) > 0,  # Approximation for penal
        "witness_list": False,  # Would need specific check
        "marriage_certificate": (doc_count or 0) > 0,  # Approximation for family
        "children_info": bool(case.metadata_.get("children")),
        "contract": (doc_count or 0) > 0,  # Approximation for commercial
        "financial_docs": (doc_count or 0) >= 2,  # Approximation
    }

    present_items = []
    missing_items = []

    for item in checklist:
        is_present = presence_map.get(item["element"], False)
        completeness_item = CompletenessItem(
            element=item["element"],
            label_fr=item["label_fr"],
            present=is_present,
            critical=item["critical"],
        )
        if is_present:
            present_items.append(completeness_item)
        else:
            missing_items.append(completeness_item)

    total = len(checklist)
    score = int((len(present_items) / max(total, 1)) * 100)

    return CompletenessResponse(
        score=score,
        present=present_items,
        missing=missing_items,
        matter_type=case.matter_type,
    )


# ── Helper: compute case health ──────────────────────────────────────


async def _compute_case_health(
    session: AsyncSession,
    case: Case,
    tenant_id: uuid.UUID,
) -> CaseHealthResponse:
    """Compute overall health score for a case."""
    now = datetime.now(timezone.utc)

    # Completeness component
    completeness = await _compute_completeness(session, case, tenant_id)
    completeness_score = completeness.score

    # Activity component (interactions in last 30 days)
    recent_interactions = await session.scalar(
        select(func.count(InteractionEvent.id))
        .where(InteractionEvent.tenant_id == tenant_id)
        .where(InteractionEvent.case_id == case.id)
        .where(InteractionEvent.occurred_at >= now - timedelta(days=30))
    )
    activity_score = min(100, (recent_interactions or 0) * 15)

    # Billing component (ratio of invoiced vs total time)
    total_entries = await session.scalar(
        select(func.count(TimeEntry.id))
        .where(TimeEntry.tenant_id == tenant_id)
        .where(TimeEntry.case_id == case.id)
    )
    invoiced_entries = await session.scalar(
        select(func.count(TimeEntry.id))
        .where(TimeEntry.tenant_id == tenant_id)
        .where(TimeEntry.case_id == case.id)
        .where(TimeEntry.status == "invoiced")
    )
    billing_score = (
        int((invoiced_entries or 0) / max(total_entries or 1, 1) * 100)
        if (total_entries or 0) > 0
        else 50  # Neutral if no time entries
    )

    # Communication component (recency of last interaction)
    last_interaction = await session.scalar(
        select(func.max(InteractionEvent.occurred_at))
        .where(InteractionEvent.tenant_id == tenant_id)
        .where(InteractionEvent.case_id == case.id)
    )
    if last_interaction:
        days_since = (now - last_interaction).days
        communication_score = max(0, 100 - days_since * 5)
    else:
        communication_score = 0

    # Deadline component (no overdue deadlines = good)
    overdue = await session.scalar(
        select(func.count(CalendarEvent.id))
        .where(CalendarEvent.tenant_id == tenant_id)
        .where(CalendarEvent.case_id == case.id)
        .where(CalendarEvent.start_time < now)
        .where(CalendarEvent.start_time >= now - timedelta(days=30))
    )
    deadline_score = max(0, 100 - (overdue or 0) * 20)

    components = {
        "completeness": completeness_score,
        "activity": activity_score,
        "billing": billing_score,
        "communication": communication_score,
        "deadlines": deadline_score,
    }

    overall = int(sum(components.values()) / max(len(components), 1))

    # Trend: compare with 30 days ago data (simplified — based on activity)
    older_interactions = await session.scalar(
        select(func.count(InteractionEvent.id))
        .where(InteractionEvent.tenant_id == tenant_id)
        .where(InteractionEvent.case_id == case.id)
        .where(InteractionEvent.occurred_at >= now - timedelta(days=60))
        .where(InteractionEvent.occurred_at < now - timedelta(days=30))
    )
    if (recent_interactions or 0) > (older_interactions or 0):
        trend = "improving"
    elif (recent_interactions or 0) < (older_interactions or 0):
        trend = "declining"
    else:
        trend = "stable"

    return CaseHealthResponse(
        overall_score=overall,
        status=_health_status(overall),
        components=components,
        trend=trend,
    )


# ── Helper: generate strategy suggestions ────────────────────────────


def _generate_strategy_suggestions(
    case: Case,
    risk: RiskAssessmentResponse,
    health: CaseHealthResponse,
) -> list[StrategySuggestionResponse]:
    """Generate strategy suggestions based on risk and health analysis."""
    suggestions = []

    if risk.overall_score >= 50:
        suggestions.append(
            StrategySuggestionResponse(
                title="Renforcement de la position",
                description="Le niveau de risque eleve justifie un examen approfondi de la strategie actuelle.",
                priority="high",
                rationale=f"Score de risque: {risk.overall_score}/100",
                estimated_impact="high",
                action_type="investigation",
            )
        )

    if health.components.get("communication", 100) < 40:
        suggestions.append(
            StrategySuggestionResponse(
                title="Reprise de contact client",
                description="La communication avec le client necessite une attention immediate pour maintenir la confiance.",
                priority="high",
                rationale="Score de communication inferieur a 40",
                estimated_impact="high",
                action_type="negotiation",
            )
        )

    if health.components.get("completeness", 100) < 60:
        suggestions.append(
            StrategySuggestionResponse(
                title="Constitution du dossier",
                description="Plusieurs pieces essentielles manquent au dossier. Completer la documentation avant toute action.",
                priority="medium",
                rationale="Score de completude inferieur a 60",
                estimated_impact="medium",
                action_type="documentation",
            )
        )

    if health.components.get("billing", 100) < 50:
        suggestions.append(
            StrategySuggestionResponse(
                title="Regularisation de la facturation",
                description="Des prestations non facturees s'accumulent. Preparer un etat de frais.",
                priority="medium",
                rationale="Score de facturation inferieur a 50",
                estimated_impact="medium",
                action_type="documentation",
            )
        )

    if case.matter_type in ("civil", "commercial") and risk.overall_score >= 30:
        suggestions.append(
            StrategySuggestionResponse(
                title="Evaluation d'une mediation",
                description="Envisager une mediation pour reduire les couts et accelerer la resolution.",
                priority="low",
                rationale="Dossier civil/commercial avec risque non negligeable",
                estimated_impact="medium",
                action_type="mediation",
            )
        )

    return suggestions


# ── Helper: generate action suggestions ──────────────────────────────


def _generate_action_suggestions(
    case: Case,
    risk: RiskAssessmentResponse,
    health: CaseHealthResponse,
) -> list[ActionSuggestionResponse]:
    """Generate smart action suggestions based on analysis."""
    actions = []

    # High risk → alert
    if risk.overall_score >= 60:
        actions.append(
            ActionSuggestionResponse(
                action_type="alert",
                title="Alerte risque eleve",
                description=f"Le dossier {case.reference} presente un risque eleve ({risk.overall_score}/100). "
                "Action immediate recommandee.",
                priority="critical" if risk.overall_score >= 75 else "urgent",
                confidence=0.85,
                trigger_source="analysis",
            )
        )

    # Communication gap → follow-up
    comm_score = health.components.get("communication", 100)
    if comm_score < 40:
        actions.append(
            ActionSuggestionResponse(
                action_type="follow_up",
                title="Relance client necessaire",
                description="Aucune communication recente. Contacter le client pour un suivi.",
                priority="urgent",
                confidence=0.9,
                trigger_source="communication",
            )
        )

    # Missing documents → suggestion
    completeness_score = health.components.get("completeness", 100)
    if completeness_score < 60:
        actions.append(
            ActionSuggestionResponse(
                action_type="suggestion",
                title="Completer le dossier",
                description="Pieces manquantes detectees. Demander les documents au client.",
                priority="normal",
                confidence=0.8,
                trigger_source="document",
            )
        )

    # Deadline approaching → alert
    deadline_score = health.components.get("deadlines", 100)
    if deadline_score < 60:
        actions.append(
            ActionSuggestionResponse(
                action_type="alert",
                title="Echeances proches",
                description="Des echeances imminentes ou depassees necessitent votre attention.",
                priority="urgent",
                confidence=0.95,
                trigger_source="deadline",
            )
        )

    return actions


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
        # Total active cases
        total_active = await session.scalar(
            select(func.count(Case.id))
            .where(Case.tenant_id == tenant_id)
            .where(Case.status.in_(["open", "in_progress", "pending"]))
        )

        # Pending brain actions
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

        # Recent insights (not dismissed)
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

        # Critical deadlines (calendar events in the next N days)
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
                urgency=_deadline_urgency((event.start_time - now).days),
                case_id=str(event.case_id) if event.case_id else None,
                case_title=case_title,
            )
            for event, case_title in deadline_rows
        ]

        # Risk distribution across active cases
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
            risk = await _compute_risk_assessment(session, case, tenant_id)
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

        # Workload next weeks
        workload_weeks = []
        for week_offset in range(4):
            week_start = now + timedelta(weeks=week_offset)
            week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
            # Adjust to Monday
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

            estimated_hours = (week_deadlines or 0) * 2.0  # Estimate 2h per event
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

        # Aggregate stats
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

    # Fetch case
    case = await session.scalar(
        select(Case).where(Case.tenant_id == tenant_id).where(Case.id == case_id)
    )
    if not case:
        raise HTTPException(status_code=404, detail="Dossier introuvable")

    try:
        # Risk assessment
        risk = await _compute_risk_assessment(session, case, tenant_id)

        # Completeness
        completeness = None
        if include_completeness:
            completeness = await _compute_completeness(session, case, tenant_id)

        # Health
        health = await _compute_case_health(session, case, tenant_id)

        # Strategy suggestions
        strategy_suggestions = []
        if include_strategy:
            strategy_suggestions = _generate_strategy_suggestions(case, risk, health)

        # Action suggestions
        action_suggestions = _generate_action_suggestions(case, risk, health)

        analyzed_at = datetime.now(timezone.utc)

        # Store insights in brain_insights table
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

        # Store actions in brain_actions table
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
        # Map feedback to status
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
            urg = _deadline_urgency(days_remaining)

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
        return await _compute_case_health(session, case, tenant_id)
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
            # Adjust to Monday
            week_start = week_start - timedelta(days=week_start.weekday())
            week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)

            # Count calendar events in this week
            week_deadlines = await session.scalar(
                select(func.count(CalendarEvent.id))
                .where(CalendarEvent.tenant_id == tenant_id)
                .where(CalendarEvent.start_time >= week_start)
                .where(CalendarEvent.start_time <= week_end)
            )

            # Count distinct cases with events this week
            week_cases = await session.scalar(
                select(func.count(func.distinct(CalendarEvent.case_id)))
                .where(CalendarEvent.tenant_id == tenant_id)
                .where(CalendarEvent.case_id.isnot(None))
                .where(CalendarEvent.start_time >= week_start)
                .where(CalendarEvent.start_time <= week_end)
            )

            # Estimate hours based on time entries from same period last year
            # (fallback: 2h per event)
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


# ── 10. POST /document/analyze — document intelligence ──────────


@router.post("/document/analyze")
async def analyze_document(
    body: dict,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Analyze a legal document — classify, extract clauses, detect risks.

    Body: { "text": "...", "filename": "contract.pdf" }
    """
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
            status_code=500,
            detail="Erreur lors de l'analyse du document",
        )


# ── 11. GET /billing/report — billing intelligence ─────────────


@router.get("/billing/report")
async def get_billing_report(
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Generate billing intelligence report — unbilled work, anomalies, suggestions."""
    tenant_id = current_user["tenant_id"]

    try:
        from apps.api.services.brain.billing_intelligence import BillingIntelligence

        # Fetch time entries
        te_result = await session.execute(
            select(TimeEntry).where(TimeEntry.tenant_id == tenant_id)
        )
        time_entries_raw = te_result.scalars().all()

        # Fetch invoices
        inv_result = await session.execute(
            select(Invoice).where(Invoice.tenant_id == tenant_id)
        )
        invoices_raw = inv_result.scalars().all()

        # Fetch cases
        cases_result = await session.execute(
            select(Case).where(Case.tenant_id == tenant_id)
        )
        cases_raw = cases_result.scalars().all()

        # Convert to dicts for the billing service
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


# ── 12. GET /client/{contact_id}/health — client intelligence ──


@router.get("/client/{contact_id}/health")
async def get_client_health(
    contact_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Assess client relationship health."""
    from packages.db.models.contact import Contact
    from packages.db.models.case_contact import CaseContact

    tenant_id = current_user["tenant_id"]

    try:
        # Verify contact exists
        contact_result = await session.execute(
            select(Contact).where(
                Contact.id == contact_id, Contact.tenant_id == tenant_id
            )
        )
        contact = contact_result.scalar_one_or_none()
        if not contact:
            raise HTTPException(status_code=404, detail="Contact non trouvé")

        # Get cases for this contact
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

        # Calculate health score
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
