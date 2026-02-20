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
    ContactAssistRequest,
    ContactAssistResponse,
    DeadlineResponse,
    DossierCreationAssistRequest,
    DossierCreationAssistResponse,
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


# ── Belgian legal knowledge base for dossier assist ──────────────────

BELGIAN_LEGAL_KNOWLEDGE: dict[str, dict] = {
    "civil": {
        "jurisdiction": "Tribunal de premiere instance (section civile)",
        "sub_types": [
            "responsabilite contractuelle",
            "responsabilite extracontractuelle",
            "recouvrement de creance",
            "servitudes",
            "troubles de voisinage",
            "bail",
        ],
        "deadlines": [
            {
                "name": "Prescription de droit commun",
                "duration": "10 ans",
                "description": "Art. 2262bis C. civ. — prescription de droit commun pour les actions personnelles",
            },
            {
                "name": "Prescription responsabilite extracontractuelle",
                "duration": "5 ans",
                "description": "Art. 2262bis §1 al.2 C. civ. — a partir de la connaissance du dommage",
            },
            {
                "name": "Delai d'appel",
                "duration": "1 mois",
                "description": "Art. 1051 C. jud. — a compter de la signification du jugement",
            },
            {
                "name": "Pourvoi en cassation",
                "duration": "3 mois",
                "description": "Art. 1073 C. jud. — a compter de la signification de la decision",
            },
        ],
        "required_documents": [
            "Lettre de mandat signee",
            "Pieces d'identite du client",
            "Contrat ou convention litigieuse",
            "Correspondances echangees entre les parties",
            "Preuves du dommage (factures, photos, expertises)",
            "Mise en demeure prealable",
        ],
        "risk_points": [
            "Verifier la prescription avant toute action",
            "Evaluer la solvabilite de la partie adverse",
            "Verifier la competence territoriale du tribunal",
            "Analyser les clauses attributives de competence",
            "Examiner les clauses de mediation ou arbitrage prealable",
        ],
        "legal_references": [
            "Code civil (art. 1101 et s. — obligations)",
            "Code judiciaire (art. 1050-1073 — voies de recours)",
            "Code judiciaire (art. 624-633 — competence territoriale)",
            "Loi du 21 février 2005 sur la mediation",
        ],
        "strategy_notes": "En matiere civile belge, privilegier la mise en demeure detaillee avant toute citation. "
        "Evaluer l'opportunite d'une mediation (obligatoire en certaines matieres depuis 2024). "
        "Verifier les conditions de l'aide juridique si le client y a droit.",
    },
    "penal": {
        "jurisdiction": "Tribunal correctionnel / Cour d'assises",
        "sub_types": [
            "plainte avec constitution de partie civile",
            "defense en correctionnelle",
            "instruction penale",
            "detention preventive",
            "execution des peines",
            "mediation penale",
        ],
        "deadlines": [
            {
                "name": "Prescription contraventions",
                "duration": "6 mois",
                "description": "Art. 68 C. pen. — prescription de l'action publique pour les contraventions",
            },
            {
                "name": "Prescription delits",
                "duration": "5 ans",
                "description": "Art. 68 C. pen. — prescription de l'action publique pour les delits",
            },
            {
                "name": "Prescription crimes",
                "duration": "15 ans",
                "description": "Art. 68 C. pen. — prescription de l'action publique pour les crimes",
            },
            {
                "name": "Delai d'appel (penal)",
                "duration": "30 jours",
                "description": "Art. 203 C.I.Cr. — a compter du prononce du jugement",
            },
            {
                "name": "Chambre du conseil (detention preventive)",
                "duration": "5 jours",
                "description": "Art. 21 Loi du 20/07/1990 — comparution dans les 5 jours du mandat d'arret",
            },
        ],
        "required_documents": [
            "Lettre de mandat signee",
            "Proces-verbal de police / plainte",
            "Copie du dossier repressif (acces au dossier)",
            "Pieces d'identite du client",
            "Casier judiciaire du client",
            "Elements a decharge",
        ],
        "risk_points": [
            "Verifier le respect des droits de la defense (acces au dossier, Salduz)",
            "Controler la regularite des devoirs d'enquete",
            "Evaluer le risque de detention preventive",
            "Verifier la qualification penale retenue",
            "Examiner les possibilites de transaction penale (art. 216bis C.I.Cr.)",
        ],
        "legal_references": [
            "Code penal (Livre I et II)",
            "Code d'instruction criminelle (art. 182 et s.)",
            "Loi du 20 juillet 1990 relative a la detention preventive",
            "Loi Salduz du 13 aout 2011 (assistance de l'avocat)",
            "Loi du 5 mai 2014 relative a l'internement",
        ],
        "strategy_notes": "En matiere penale, l'acces au dossier est fondamental (art. 21bis C.I.Cr.). "
        "Verifier immediatement les delais de detention preventive et les conditions de remise en liberte. "
        "Envisager la mediation penale ou la transaction si les faits s'y pretent.",
    },
    "commercial": {
        "jurisdiction": "Tribunal de l'entreprise",
        "sub_types": [
            "litiges entre entreprises",
            "droit des contrats commerciaux",
            "concurrence deloyale",
            "recouvrement commercial",
            "faillite et reorganisation judiciaire",
            "droit des marques",
        ],
        "deadlines": [
            {
                "name": "Prescription commerciale",
                "duration": "10 ans",
                "description": "Art. 2262bis C. civ. — prescription de droit commun applicable aux obligations commerciales",
            },
            {
                "name": "Delai de paiement (B2B)",
                "duration": "30 jours",
                "description": "Loi du 2 aout 2002 — delai de paiement par defaut entre entreprises",
            },
            {
                "name": "Declaration de cessation de paiement",
                "duration": "1 mois",
                "description": "Art. XX.102 CDE — obligation de declaration dans le mois de la cessation",
            },
            {
                "name": "Delai d'appel",
                "duration": "1 mois",
                "description": "Art. 1051 C. jud. — a compter de la signification du jugement",
            },
        ],
        "required_documents": [
            "Lettre de mandat signee",
            "Extrait BCE/KBO de l'entreprise cliente",
            "Contrat commercial litigieux",
            "Factures et bons de commande",
            "Correspondances commerciales",
            "Comptes annuels des parties (via BNB)",
        ],
        "risk_points": [
            "Verifier la qualite de commercant/entreprise des parties",
            "Analyser les conditions generales applicables",
            "Evaluer le risque d'insolvabilite (via Banque-Carrefour des Entreprises)",
            "Verifier l'existence de clauses compromissoires",
            "Examiner les pratiques du marche pertinent",
        ],
        "legal_references": [
            "Code de droit economique (CDE, Livres I-XX)",
            "Code judiciaire (art. 573-574 — competence du tribunal de l'entreprise)",
            "Loi du 2 aout 2002 concernant la lutte contre le retard de paiement",
            "Livre XX CDE — insolvabilite des entreprises",
        ],
        "strategy_notes": "En matiere commerciale belge, la procedure sommaire inedite (PSI) permet une resolution rapide. "
        "Verifier si une reorganisation judiciaire (Livre XX CDE) est envisageable pour l'adversaire. "
        "Les conditions generales de vente doivent etre analysees avec soin (battle of the forms).",
    },
    "social": {
        "jurisdiction": "Tribunal du travail",
        "sub_types": [
            "licenciement abusif",
            "contrat de travail",
            "securite sociale",
            "accidents du travail",
            "discrimination au travail",
            "harcelement",
        ],
        "deadlines": [
            {
                "name": "Prescription actions contractuelles (travail)",
                "duration": "1 an",
                "description": "Art. 15 Loi du 3/07/1978 — prescription des actions naissant du contrat de travail",
            },
            {
                "name": "Contestation du licenciement",
                "duration": "1 an",
                "description": "CCT n°109 — delai pour contester le caractere manifestement deraisonnable du licenciement",
            },
            {
                "name": "Delai de preavis",
                "duration": "Variable selon anciennete",
                "description": "Art. 37/2 Loi du 3/07/1978 — selon l'anciennete du travailleur (statut unique)",
            },
            {
                "name": "Delai d'appel",
                "duration": "1 mois",
                "description": "Art. 1051 C. jud. — a compter de la signification du jugement",
            },
        ],
        "required_documents": [
            "Lettre de mandat signee",
            "Contrat de travail",
            "Fiches de paie recentes",
            "Lettre de licenciement / preavis",
            "Reglement de travail",
            "Correspondances avec l'employeur",
            "Certificat medical (si applicable)",
        ],
        "risk_points": [
            "Verifier le respect de la procedure de licenciement (motivation — CCT 109)",
            "Controler le calcul de l'indemnite de preavis (statut unique)",
            "Examiner les protections speciales (grossesse, mandat syndical, etc.)",
            "Evaluer les indemnites reclamables (preavis, dommages, protection)",
            "Verifier l'application de la clause de non-concurrence",
        ],
        "legal_references": [
            "Loi du 3 juillet 1978 relative aux contrats de travail",
            "CCT n°109 du CNT — licenciement manifestement deraisonnable",
            "Loi du 10 mai 2007 — anti-discrimination",
            "Loi du 4 aout 1996 — bien-etre au travail",
            "Code judiciaire (art. 578-583 — competence du tribunal du travail)",
        ],
        "strategy_notes": "En droit social belge, le tribunal du travail a une competence exclusive. "
        "La charge de la preuve en matiere de licenciement pese sur l'employeur (motivation — CCT 109). "
        "Envisager la conciliation obligatoire devant le bureau de conciliation du tribunal du travail.",
    },
    "fiscal": {
        "jurisdiction": "Tribunal de premiere instance (section fiscale)",
        "sub_types": [
            "impot des personnes physiques (IPP)",
            "impot des societes (ISoc)",
            "TVA",
            "droits de succession",
            "droits d'enregistrement",
            "procedure fiscale",
        ],
        "deadlines": [
            {
                "name": "Reclamation administrative",
                "duration": "6 mois",
                "description": "Art. 371 CIR 92 — a compter de l'envoi de l'avertissement-extrait de role",
            },
            {
                "name": "Recours judiciaire",
                "duration": "3 mois",
                "description": "Art. 1385undecies C. jud. — a compter de la notification de la decision directoriale",
            },
            {
                "name": "Prescription fiscale ordinaire",
                "duration": "3 ans",
                "description": "Art. 354 CIR 92 — prescription de l'imposition supplementaire",
            },
            {
                "name": "Prescription fiscale extraordinaire",
                "duration": "7 ans",
                "description": "Art. 354 al.2 CIR 92 — en cas de fraude fiscale",
            },
        ],
        "required_documents": [
            "Lettre de mandat signee",
            "Avertissement-extrait de role conteste",
            "Declaration fiscale concernee",
            "Notification de rectification (le cas echeant)",
            "Correspondances avec l'administration fiscale",
            "Pieces comptables justificatives",
        ],
        "risk_points": [
            "Verifier le respect des delais de reclamation (forclusion)",
            "Analyser la validite de la procedure de taxation",
            "Evaluer le risque de sanctions administratives et penales",
            "Verifier l'existence d'un ruling fiscal prealable",
            "Examiner les conventions preventives de double imposition",
        ],
        "legal_references": [
            "Code des impots sur les revenus 1992 (CIR 92)",
            "Code de la TVA",
            "Code des droits de succession",
            "Code des droits d'enregistrement",
            "Code judiciaire (art. 569 al.1, 32° — competence fiscale)",
            "Charte du contribuable (Loi du 4 aout 1986)",
        ],
        "strategy_notes": "En matiere fiscale belge, la reclamation administrative est un prealable obligatoire avant le recours judiciaire. "
        "Le delai de 6 mois pour reclamer est imperatif et de rigueur. "
        "Envisager un accord avec l'administration via la mediation fiscale (Service de conciliation fiscale).",
    },
    "family": {
        "jurisdiction": "Tribunal de la famille",
        "sub_types": [
            "divorce par consentement mutuel",
            "divorce pour desunion irreparable",
            "autorite parentale",
            "obligations alimentaires",
            "filiation",
            "adoption",
            "regime matrimonial",
        ],
        "deadlines": [
            {
                "name": "Delai de reflexion (divorce consentement mutuel)",
                "duration": "3 mois (si enfant mineur) / pas de delai sinon",
                "description": "Art. 1289 C. jud. — delai de comparution supprime ou reduit",
            },
            {
                "name": "Delai d'appel (famille)",
                "duration": "1 mois",
                "description": "Art. 1051 C. jud. — a compter de la signification du jugement",
            },
            {
                "name": "Action en contestation de paternite",
                "duration": "1 an",
                "description": "Art. 318 C. civ. — a compter de la decouverte du fait",
            },
            {
                "name": "Prescription aliments",
                "duration": "5 ans",
                "description": "Art. 2277 C. civ. — arrieres de pensions alimentaires",
            },
        ],
        "required_documents": [
            "Lettre de mandat signee",
            "Acte de mariage",
            "Actes de naissance des enfants",
            "Composition de menage",
            "Preuves de revenus des parties (fiches de paie, avertissements-extraits de role)",
            "Inventaire du patrimoine commun",
            "Convention prealable (si divorce amiable)",
        ],
        "risk_points": [
            "Proteger les interets des enfants mineurs en priorite",
            "Evaluer les mesures urgentes et provisoires necessaires",
            "Verifier l'inventaire complet du patrimoine commun",
            "Analyser le regime matrimonial applicable",
            "Examiner les droits de la partie la plus faible economiquement",
        ],
        "legal_references": [
            "Code civil (art. 229 et s. — divorce)",
            "Code civil (art. 371-387 — autorite parentale)",
            "Code judiciaire (art. 1253ter et s. — tribunal de la famille)",
            "Loi du 19 mars 2010 — tribunal de la famille et de la jeunesse",
            "Code civil (art. 203-211 — obligations alimentaires)",
        ],
        "strategy_notes": "Le tribunal de la famille est competent pour l'ensemble du contentieux familial depuis 2014. "
        "Privilegier le divorce par consentement mutuel quand c'est possible (plus rapide et moins couteux). "
        "En cas de violence conjugale, envisager immediatement une ordonnance d'eloignement.",
    },
    "administrative": {
        "jurisdiction": "Conseil d'Etat (section du contentieux administratif)",
        "sub_types": [
            "recours en annulation",
            "recours en suspension",
            "marches publics",
            "urbanisme et environnement",
            "fonction publique",
            "etrangers et asile",
        ],
        "deadlines": [
            {
                "name": "Recours en annulation",
                "duration": "60 jours",
                "description": "Art. 4 Arrete du Regent du 23/08/1948 — a compter de la notification ou publication",
            },
            {
                "name": "Demande de suspension (extreme urgence)",
                "duration": "15 jours",
                "description": "Art. 17 §1 Lois coordonnees — suspension d'extreme urgence",
            },
            {
                "name": "Recours marches publics",
                "duration": "15 jours (suspension) / 60 jours (annulation)",
                "description": "Loi du 17/06/2013 — delais specifiques en matiere de marches publics",
            },
        ],
        "required_documents": [
            "Lettre de mandat signee",
            "Acte administratif attaque (decision, permis, arrete)",
            "Preuve de notification de la decision",
            "Dossier administratif complet",
            "Memoire en requete (formalisme strict)",
            "Pieces justificatives du prejudice",
        ],
        "risk_points": [
            "Respecter strictement le delai de 60 jours (delai de forclusion)",
            "Verifier l'epuisement des recours administratifs internes",
            "Evaluer l'interet au recours (interet personnel, direct et actuel)",
            "Identifier les moyens d'annulation (incompetence, vice de forme, violation de la loi, detournement de pouvoir)",
            "Envisager la demande de suspension si urgence",
        ],
        "legal_references": [
            "Lois coordonnees sur le Conseil d'Etat du 12 janvier 1973",
            "Arrete du Regent du 23 aout 1948 — procedure devant le Conseil d'Etat",
            "Loi du 17 juin 2013 — marches publics",
            "CoBAT / CoDT — urbanisme (selon la region)",
        ],
        "strategy_notes": "La procedure devant le Conseil d'Etat est ecrite et formaliste. "
        "L'auditeur joue un role determinant — analyser soigneusement son rapport. "
        "En matiere d'urbanisme, distinguer les competences regionales (Bruxelles, Wallonie, Flandre).",
    },
    "immobilier": {
        "jurisdiction": "Justice de paix / Tribunal de premiere instance",
        "sub_types": [
            "bail d'habitation",
            "bail commercial",
            "copropriete",
            "vente immobiliere",
            "vices caches",
            "servitudes",
        ],
        "deadlines": [
            {
                "name": "Action en garantie des vices caches",
                "duration": "Bref delai (apprecie par le juge)",
                "description": "Art. 1648 C. civ. — action a intenter a bref delai",
            },
            {
                "name": "Conge bail d'habitation",
                "duration": "6 mois / 3 mois selon le motif",
                "description": "Art. 3 §2-4 Loi sur les baux d'habitation — preavis selon le motif de conge",
            },
            {
                "name": "Renouvellement bail commercial",
                "duration": "Entre 18 et 15 mois avant l'echeance",
                "description": "Art. 14 Loi sur les baux commerciaux — demande de renouvellement",
            },
            {
                "name": "Delai d'appel",
                "duration": "1 mois",
                "description": "Art. 1051 C. jud.",
            },
        ],
        "required_documents": [
            "Lettre de mandat signee",
            "Contrat de bail ou acte de vente",
            "Etat des lieux d'entree (bail)",
            "Proces-verbal de copropriete (le cas echeant)",
            "Rapports d'expertise technique",
            "Correspondances et mises en demeure",
        ],
        "risk_points": [
            "Verifier l'enregistrement du bail (consequences fiscales et civiles)",
            "Analyser la conformite urbanistique du bien",
            "Evaluer les obligations du bailleur vs locataire",
            "Verifier les regles de copropriete (majorites requises, parties communes)",
            "Examiner la legislation regionale applicable (bail = competence regionale)",
        ],
        "legal_references": [
            "Code civil (art. 1714-1762 — bail)",
            "Legislation regionale sur le bail d'habitation (Bruxelles, Wallonie, Flandre)",
            "Loi du 30 avril 1951 sur les baux commerciaux",
            "Loi du 2 juin 2010 sur la copropriete",
        ],
        "strategy_notes": "Le droit du bail est regionalise en Belgique depuis 2014. "
        "Identifier la region competente (Bruxelles, Wallonie, Flandre) pour determiner les regles applicables. "
        "La justice de paix est competente pour les litiges locatifs (art. 591 C. jud.).",
    },
    "construction": {
        "jurisdiction": "Tribunal de premiere instance",
        "sub_types": [
            "responsabilite decennale",
            "malfacons",
            "retard de chantier",
            "architecte et entrepreneurs",
            "marches prives de travaux",
        ],
        "deadlines": [
            {
                "name": "Responsabilite decennale",
                "duration": "10 ans",
                "description": "Art. 1792 et 2270 C. civ. — responsabilite pour les gros ouvrages",
            },
            {
                "name": "Garantie des vices caches (construction)",
                "duration": "Bref delai (appreciation souveraine du juge)",
                "description": "Art. 1648 C. civ. — applicable aux malfacons cachees",
            },
            {
                "name": "Vices apparents",
                "duration": "A la reception provisoire",
                "description": "Jurisprudence — les reserves doivent etre emises lors de la reception provisoire",
            },
        ],
        "required_documents": [
            "Lettre de mandat signee",
            "Contrat d'entreprise / devis signe",
            "Plans et cahier des charges",
            "Proces-verbal de reception provisoire/definitive",
            "Rapport d'expertise technique",
            "Photos des malfacons",
            "Factures et preuves de paiement",
        ],
        "risk_points": [
            "Distinguer vices apparents (reception) et vices caches (bref delai)",
            "Identifier la responsabilite respective (architecte, entrepreneur, sous-traitant)",
            "Verifier les assurances professionnelles (loi Peeters-Borsus)",
            "Evaluer la necessite d'une expertise judiciaire",
            "Examiner les clauses limitatives de responsabilite",
        ],
        "legal_references": [
            "Code civil (art. 1787-1799 — contrat d'entreprise)",
            "Code civil (art. 1792 et 2270 — responsabilite decennale)",
            "Loi du 31 mai 2017 (Peeters-Borsus) — assurance responsabilite construction",
            "Loi du 9 mai 2019 (Peeters) — architectes et entrepreneurs",
        ],
        "strategy_notes": "En droit de la construction belge, la distinction entre reception provisoire et definitive est capitale. "
        "L'expertise judiciaire est souvent necessaire pour etablir les responsabilites techniques. "
        "Depuis 2018, l'assurance decennale est obligatoire (loi Peeters-Borsus).",
    },
    "societes": {
        "jurisdiction": "Tribunal de l'entreprise",
        "sub_types": [
            "constitution de societe",
            "responsabilite des administrateurs",
            "conflit entre associes",
            "dissolution et liquidation",
            "transformation de societe",
            "fusion et scission",
        ],
        "deadlines": [
            {
                "name": "Publication au Moniteur belge",
                "duration": "30 jours",
                "description": "Art. 2:7 CSA — publication des actes de societe",
            },
            {
                "name": "Depot des comptes annuels",
                "duration": "7 mois apres la cloture",
                "description": "Art. 3:12 CSA — depot aupres de la BNB",
            },
            {
                "name": "Action en responsabilite (administrateurs)",
                "duration": "5 ans",
                "description": "Art. 2:143 CSA — prescription de l'action en responsabilite",
            },
            {
                "name": "Exclusion/retrait d'associe",
                "duration": "Pas de delai fixe",
                "description": "Art. 2:63 et s. CSA — action en exclusion ou retrait devant le tribunal de l'entreprise",
            },
        ],
        "required_documents": [
            "Lettre de mandat signee",
            "Acte constitutif et statuts coordonnes",
            "Extrait BCE/KBO",
            "Comptes annuels des 3 derniers exercices",
            "Proces-verbaux des assemblees generales",
            "Convention d'actionnaires (le cas echeant)",
            "Registre des parts/actions",
        ],
        "risk_points": [
            "Verifier la conformite aux nouvelles dispositions du CSA (entree en vigueur 2020)",
            "Analyser les conflits d'interets des administrateurs (art. 5:76, 7:96 CSA)",
            "Evaluer la responsabilite des administrateurs (plafonds — art. 2:57 CSA)",
            "Verifier le respect de la procedure de sonnette d'alarme (art. 5:153, 7:228 CSA)",
            "Examiner les droits des actionnaires minoritaires",
        ],
        "legal_references": [
            "Code des societes et des associations (CSA) du 23 mars 2019",
            "Code judiciaire (art. 574 — competence du tribunal de l'entreprise)",
            "Loi du 16 mars 1803 — organisation du notariat",
            "Arrete royal du 29 avril 2019 — execution du CSA",
        ],
        "strategy_notes": "Le CSA a profondement reforme le droit des societes belge depuis 2020. "
        "La SRL (ancienne SPRL) est la forme de droit commun avec une grande liberte statutaire. "
        "Les plafonds de responsabilite des administrateurs (art. 2:57 CSA) sont une nouveaute majeure.",
    },
}


def _estimate_complexity(description: str, matter_type: str) -> str:
    """Estimate case complexity based on description analysis."""
    desc_lower = description.lower()
    complex_indicators = [
        "international",
        "transfrontalier",
        "multi-parties",
        "expertise",
        "cassation",
        "europeen",
        "constitutionnel",
        "class action",
        "groupe de societes",
        "fusion",
        "scission",
    ]
    simple_indicators = [
        "recouvrement",
        "injonction",
        "simple",
        "consentement mutuel",
        "non conteste",
        "amiable",
        "reconnaissance",
    ]

    complex_count = sum(1 for ind in complex_indicators if ind in desc_lower)
    simple_count = sum(1 for ind in simple_indicators if ind in desc_lower)

    if complex_count >= 2 or matter_type in ("administrative",):
        return "complex"
    if simple_count >= 2:
        return "simple"
    if complex_count >= 1:
        return "complex"
    if simple_count >= 1:
        return "simple"
    return "moderate"


# ── Endpoint 13: POST /dossier/assist-creation ───────────────────────


@router.post("/dossier/assist-creation", response_model=DossierCreationAssistResponse)
async def assist_dossier_creation(
    body: DossierCreationAssistRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> DossierCreationAssistResponse:
    """Assistance intelligente a la creation d'un dossier.

    Analyse le type de matiere et la description pour fournir des
    recommandations juridiques belges: juridiction competente, delais,
    documents requis, points de risque et references legales.
    """
    _tenant_id = current_user["tenant_id"]  # noqa: F841 — RLS via session

    try:
        matter = body.matter_type.lower().strip()
        knowledge = BELGIAN_LEGAL_KNOWLEDGE.get(matter)

        if knowledge is None:
            # Fallback to civil for unknown matter types
            knowledge = BELGIAN_LEGAL_KNOWLEDGE["civil"]
            suggested_jurisdiction = (
                f"A determiner (matiere '{body.matter_type}' non reconnue — "
                "verifier la competence selon le Code judiciaire)"
            )
            suggested_sub_type = None
        else:
            suggested_jurisdiction = knowledge["jurisdiction"]
            # Try to suggest sub_type from description keywords
            suggested_sub_type = None
            desc_lower = body.description.lower()
            for sub in knowledge.get("sub_types", []):
                if any(word in desc_lower for word in sub.split() if len(word) > 3):
                    suggested_sub_type = sub
                    break

        complexity = _estimate_complexity(body.description, matter)

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
    """Assistance intelligente a la creation d'un contact.

    Verifie les doublons potentiels, fournit des informations BCE
    si un numero d'entreprise est fourni, et genere des notes de
    conformite RGPD.
    """
    from packages.db.models.contact import Contact

    _tenant_id = current_user["tenant_id"]  # noqa: F841 — RLS via session

    try:
        suggested_fields: dict = {}
        bce_info: dict | None = None
        duplicate_warning: dict | None = None
        compliance_notes: list[str] = []
        relationship_suggestions: list[str] = []

        # ── Duplicate detection ──────────────────────────────────
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

        # ── BCE number handling (legal persons) ──────────────────
        if body.bce_number and body.type == "legal":
            # Normalize BCE number
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

            # Check for existing contacts with same BCE
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

        # ── Suggested fields based on type ───────────────────────
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

        # ── GDPR / Compliance notes ──────────────────────────────
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
