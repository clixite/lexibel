"""Brain helpers — shared constants and computation functions.

Used by all brain sub-routers for risk assessment, health scoring,
completeness evaluation, and strategy/action generation.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.schemas.brain import (
    ActionSuggestionResponse,
    CaseHealthResponse,
    CompletenessItem,
    CompletenessResponse,
    RiskAssessmentResponse,
    RiskFactor,
    StrategySuggestionResponse,
)
from packages.db.models.calendar_event import CalendarEvent
from packages.db.models.case import Case
from packages.db.models.evidence_link import EvidenceLink
from packages.db.models.interaction_event import InteractionEvent
from packages.db.models.invoice import Invoice
from packages.db.models.time_entry import TimeEntry
from packages.db.models.timeline_event import TimelineEvent

logger = logging.getLogger(__name__)


# ── Completeness checklists per matter type ───────────────────────────

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

DEFAULT_CHECKLIST = COMPLETENESS_CHECKLISTS["civil"]


# ── Score helpers ─────────────────────────────────────────────────────


def risk_level(score: int) -> str:
    """Return risk level string from numeric score."""
    if score >= 75:
        return "critical"
    if score >= 50:
        return "high"
    if score >= 25:
        return "medium"
    return "low"


def health_status(score: int) -> str:
    """Return health status string from numeric score."""
    if score >= 80:
        return "healthy"
    if score >= 60:
        return "attention_needed"
    if score >= 40:
        return "at_risk"
    return "critical"


def deadline_urgency(days: int) -> str:
    """Return urgency level for a deadline based on days remaining."""
    if days <= 2:
        return "critical"
    if days <= 7:
        return "urgent"
    if days <= 14:
        return "attention"
    return "normal"


# ── Risk assessment computation ───────────────────────────────────────


async def compute_risk_assessment(
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
            severity=risk_level(deadline_score),
        )
    )

    # Factor 2: Communication gap
    last_interaction = await session.scalar(
        select(func.max(InteractionEvent.occurred_at))
        .where(InteractionEvent.tenant_id == tenant_id)
        .where(InteractionEvent.case_id == case.id)
    )
    if last_interaction:
        days_silent = (now - last_interaction).days
    else:
        days_silent = 90
    comm_score = min(100, days_silent * 3)
    factors.append(
        RiskFactor(
            name="communication_gap",
            score=comm_score,
            weight=0.25,
            description=f"Aucune communication depuis {days_silent} jours",
            severity=risk_level(comm_score),
        )
    )

    # Factor 3: Document completeness
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
            severity=risk_level(doc_score),
        )
    )

    # Factor 4: Case age
    case_age_days = (now.date() - case.opened_at).days if case.opened_at else 0
    age_score = min(100, max(0, case_age_days - 90))
    factors.append(
        RiskFactor(
            name="case_age",
            score=age_score,
            weight=0.15,
            description=f"Dossier ouvert depuis {case_age_days} jours",
            severity=risk_level(age_score),
        )
    )

    # Factor 5: Billing health
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
            severity=risk_level(billing_score),
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
        level=risk_level(overall),
        factors=factors,
        recommendations=recommendations,
    )


# ── Completeness computation ──────────────────────────────────────────


async def compute_completeness(
    session: AsyncSession,
    case: Case,
    tenant_id: uuid.UUID,
) -> CompletenessResponse:
    """Evaluate case completeness based on matter type checklist."""
    from packages.db.models.case_contact import CaseContact

    checklist = COMPLETENESS_CHECKLISTS.get(case.matter_type, DEFAULT_CHECKLIST)

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

    presence_map = {
        "client_contact": (contact_count or 0) > 0,
        "adverse_contact": (adverse_count or 0) > 0,
        "mandate_letter": (doc_count or 0) > 0,
        "timeline_events": (timeline_count or 0) >= 2,
        "key_documents": (doc_count or 0) >= 3,
        "court_reference": bool(case.court_reference),
        "billing_setup": (invoice_count or 0) > 0
        or bool(case.metadata_.get("billing_rate")),
        "jurisdiction": bool(case.jurisdiction),
        "police_report": (doc_count or 0) > 0,
        "witness_list": False,
        "marriage_certificate": (doc_count or 0) > 0,
        "children_info": bool(case.metadata_.get("children")),
        "contract": (doc_count or 0) > 0,
        "financial_docs": (doc_count or 0) >= 2,
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


# ── Case health computation ──────────────────────────────────────────


async def compute_case_health(
    session: AsyncSession,
    case: Case,
    tenant_id: uuid.UUID,
) -> CaseHealthResponse:
    """Compute overall health score for a case."""
    now = datetime.now(timezone.utc)

    completeness = await compute_completeness(session, case, tenant_id)
    completeness_score = completeness.score

    recent_interactions = await session.scalar(
        select(func.count(InteractionEvent.id))
        .where(InteractionEvent.tenant_id == tenant_id)
        .where(InteractionEvent.case_id == case.id)
        .where(InteractionEvent.occurred_at >= now - timedelta(days=30))
    )
    activity_score = min(100, (recent_interactions or 0) * 15)

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
        else 50
    )

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
        status=health_status(overall),
        components=components,
        trend=trend,
    )


# ── Strategy & action suggestion generators ──────────────────────────


def generate_strategy_suggestions(
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


def generate_action_suggestions(
    case: Case,
    risk: RiskAssessmentResponse,
    health: CaseHealthResponse,
) -> list[ActionSuggestionResponse]:
    """Generate smart action suggestions based on analysis."""
    actions = []

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
