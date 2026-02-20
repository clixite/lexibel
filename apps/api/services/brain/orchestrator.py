"""Brain Orchestrator — Central AI intelligence coordinator for case management.

Analyzes case data, generates insights, creates smart actions, and provides
proactive intelligence to lawyers about their cases.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.models.brain_action import BrainAction
from packages.db.models.brain_insight import BrainInsight
from packages.db.models.calendar_event import CalendarEvent
from packages.db.models.call_record import CallRecord
from packages.db.models.case import Case
from packages.db.models.case_contact import CaseContact
from packages.db.models.cloud_document import CloudDocument
from packages.db.models.contact import Contact
from packages.db.models.document_case_link import DocumentCaseLink
from packages.db.models.email_message import EmailMessage
from packages.db.models.email_thread import EmailThread
from packages.db.models.time_entry import TimeEntry
from packages.db.models.timeline_event import TimelineEvent

from apps.api.services.brain.case_analyzer import (
    CaseAnalyzer,
    CaseHealth,
    CompletenessReport,
    RiskAssessment,
    StrategySuggestion,
)
from apps.api.services.brain.communication_scorer import (
    CommunicationHealth,
    CommunicationScorer,
)
from apps.api.services.brain.deadline_intelligence import (
    DeadlineAnalysis,
    DeadlineIntelligence,
    WorkloadPrediction,
)


# ---------------------------------------------------------------------------
# Orchestrator Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class CaseAnalysis:
    """Complete analysis result for a single case."""

    case_id: str
    case_reference: str
    risk_assessment: RiskAssessment
    completeness: CompletenessReport
    health: CaseHealth
    strategies: list[StrategySuggestion] = field(default_factory=list)
    deadline_analysis: DeadlineAnalysis | None = None
    communication_health: CommunicationHealth | None = None
    generated_at: str = ""


@dataclass
class InsightResult:
    """A single AI-generated insight."""

    insight_type: str  # deadline, document_gap, billing, communication, conflict
    severity: str  # low, medium, high, critical
    title: str
    description: str
    case_id: str
    case_reference: str
    suggested_actions: list[str] = field(default_factory=list)


@dataclass
class ActionSuggestion:
    """A smart action suggestion for a case."""

    action_type: str  # alert, draft, suggestion, auto_send
    title: str
    description: str
    priority: str  # critical, urgent, normal
    confidence: float  # 0.0-1.0
    trigger_source: str  # case_analysis, deadline, communication, billing, document
    case_id: str
    case_reference: str
    action_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class DeadlineSummary:
    """Summary of upcoming deadlines for the dashboard."""

    total: int
    critical: int
    urgent: int
    deadlines: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class BrainSummary:
    """Dashboard-level intelligence summary."""

    total_active_cases: int
    risk_distribution: dict[str, int]  # low/medium/high/critical -> count
    upcoming_deadlines_7d: DeadlineSummary
    upcoming_deadlines_14d: DeadlineSummary
    upcoming_deadlines_30d: DeadlineSummary
    pending_actions: int
    recent_insights: list[InsightResult] = field(default_factory=list)
    workload_prediction: WorkloadPrediction | None = None
    revenue_at_risk_cents: int = 0
    summary: str = ""
    generated_at: str = ""


# ---------------------------------------------------------------------------
# BrainOrchestrator
# ---------------------------------------------------------------------------


class BrainOrchestrator:
    """Central coordinator for all Brain intelligence features.

    Orchestrates case analysis, insight generation, action suggestions,
    and dashboard-level intelligence by composing the CaseAnalyzer,
    DeadlineIntelligence, and CommunicationScorer services.
    """

    def __init__(self) -> None:
        self.case_analyzer = CaseAnalyzer()
        self.deadline_intel = DeadlineIntelligence()
        self.comm_scorer = CommunicationScorer()

    # ------------------------------------------------------------------
    # Full Case Analysis
    # ------------------------------------------------------------------

    async def analyze_case(
        self,
        session: AsyncSession,
        case_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> CaseAnalysis:
        """Perform a full intelligence analysis of a single case.

        Fetches all case data, contacts, documents, timeline, and time entries,
        then runs risk assessment, completeness analysis, health scoring,
        strategy suggestions, deadline analysis, and communication health.

        Args:
            session: SQLAlchemy async session.
            case_id: UUID of the case to analyze.
            tenant_id: UUID of the tenant (for RLS compliance).

        Returns:
            CaseAnalysis with all intelligence components.
        """
        # Fetch data
        case_data = await self._fetch_case(session, case_id, tenant_id)
        if case_data is None:
            return CaseAnalysis(
                case_id=str(case_id),
                case_reference="",
                risk_assessment=RiskAssessment(
                    overall_score=0, level="low", summary="Dossier introuvable"
                ),
                completeness=CompletenessReport(
                    matter_type="",
                    score=0,
                    total_elements=0,
                    present_count=0,
                    missing_count=0,
                    summary="Dossier introuvable",
                ),
                health=CaseHealth(
                    overall_score=0,
                    status="critical",
                    summary="Dossier introuvable",
                ),
                generated_at=datetime.utcnow().isoformat(),
            )

        contacts = await self._fetch_contacts(session, case_id, tenant_id)
        documents = await self._fetch_documents(session, case_id, tenant_id)
        timeline = await self._fetch_timeline(session, case_id, tenant_id)
        time_entries = await self._fetch_time_entries(session, case_id, tenant_id)
        calendar_events = await self._fetch_calendar_events(session, case_id, tenant_id)
        emails = await self._fetch_emails(session, case_id, tenant_id)
        calls = await self._fetch_calls(session, case_id, tenant_id)

        # Enrich case_data with billing info
        case_data_enriched = self._enrich_case_with_billing(case_data, time_entries)

        # Run analyses
        risk = self.case_analyzer.assess_risk(
            case_data_enriched, contacts, timeline, documents
        )
        completeness = self.case_analyzer.analyze_completeness(
            case_data_enriched, contacts, documents
        )
        health = self.case_analyzer.calculate_case_health(
            case_data_enriched, contacts, timeline, time_entries
        )
        strategies = self.case_analyzer.suggest_strategy(
            case_data_enriched, contacts, timeline
        )
        deadlines = self.deadline_intel.analyze_deadlines(
            case_data_enriched, timeline, calendar_events
        )
        comm_health = self.comm_scorer.score_communication_health(
            str(case_id), emails, calls, contacts
        )

        return CaseAnalysis(
            case_id=str(case_id),
            case_reference=case_data.get("reference", ""),
            risk_assessment=risk,
            completeness=completeness,
            health=health,
            strategies=strategies,
            deadline_analysis=deadlines,
            communication_health=comm_health,
            generated_at=datetime.utcnow().isoformat(),
        )

    # ------------------------------------------------------------------
    # Insight Generation
    # ------------------------------------------------------------------

    async def generate_insights(
        self,
        session: AsyncSession,
        case_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> list[InsightResult]:
        """Generate AI insights for a case.

        Produces insights on deadline proximity, document gaps, billing
        anomalies, communication gaps, and conflict indicators.

        Args:
            session: SQLAlchemy async session.
            case_id: UUID of the case.
            tenant_id: UUID of the tenant.

        Returns:
            List of InsightResult sorted by severity.
        """
        case_data = await self._fetch_case(session, case_id, tenant_id)
        if case_data is None:
            return []

        contacts = await self._fetch_contacts(session, case_id, tenant_id)
        documents = await self._fetch_documents(session, case_id, tenant_id)
        timeline = await self._fetch_timeline(session, case_id, tenant_id)
        time_entries = await self._fetch_time_entries(session, case_id, tenant_id)
        emails = await self._fetch_emails(session, case_id, tenant_id)
        calls = await self._fetch_calls(session, case_id, tenant_id)

        case_ref = case_data.get("reference", "")
        case_id_str = str(case_id)
        case_data_enriched = self._enrich_case_with_billing(case_data, time_entries)

        insights: list[InsightResult] = []

        # 1. Deadline proximity alerts
        insights.extend(
            self._deadline_insights(case_data_enriched, timeline, case_id_str, case_ref)
        )

        # 2. Document gap analysis
        insights.extend(
            self._document_gap_insights(
                case_data_enriched, documents, case_id_str, case_ref
            )
        )

        # 3. Billing anomalies
        insights.extend(
            self._billing_insights(
                case_data_enriched, time_entries, case_id_str, case_ref
            )
        )

        # 4. Communication gaps
        insights.extend(
            self._communication_insights(case_id_str, case_ref, emails, calls, contacts)
        )

        # 5. Contact/conflict indicators
        insights.extend(self._contact_insights(contacts, case_id_str, case_ref))

        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        insights.sort(key=lambda i: severity_order.get(i.severity, 99))

        return insights

    def _deadline_insights(
        self,
        case_data: dict[str, Any],
        timeline: list[dict[str, Any]],
        case_id: str,
        case_ref: str,
    ) -> list[InsightResult]:
        """Generate deadline-related insights."""
        insights: list[InsightResult] = []
        today = date.today()

        for event in timeline:
            event_date_raw = event.get("event_date")
            if event_date_raw is None:
                continue
            event_date = self._parse_date(event_date_raw)
            if event_date is None:
                continue

            title = event.get("title", "")
            title_lower = title.lower()

            is_deadline = event.get("category", "") in (
                "deadline",
                "hearing",
                "audience",
            ) or any(
                kw in title_lower
                for kw in ("délai", "audience", "conclusions", "échéance")
            )
            if not is_deadline:
                continue

            days = (event_date - today).days

            if days < 0:
                if not event.get("is_validated", False):
                    insights.append(
                        InsightResult(
                            insight_type="deadline",
                            severity="critical",
                            title=f"Délai dépassé : {title}",
                            description=(
                                f"Le délai '{title}' du {event_date.isoformat()} "
                                f"est dépassé de {abs(days)} jour(s)."
                            ),
                            case_id=case_id,
                            case_reference=case_ref,
                            suggested_actions=[
                                "Vérifier si le délai a été respecté",
                                "Contacter le greffe si nécessaire",
                            ],
                        )
                    )
            elif days <= 3:
                insights.append(
                    InsightResult(
                        insight_type="deadline",
                        severity="critical",
                        title=f"Délai imminent : {title}",
                        description=(
                            f"Le délai '{title}' expire dans {days} jour(s) "
                            f"({event_date.isoformat()}). Action immédiate requise."
                        ),
                        case_id=case_id,
                        case_reference=case_ref,
                        suggested_actions=[
                            "Préparer et déposer le document requis",
                            "Confirmer avec le client si nécessaire",
                        ],
                    )
                )
            elif days <= 7:
                insights.append(
                    InsightResult(
                        insight_type="deadline",
                        severity="high",
                        title=f"Délai approchant : {title}",
                        description=(
                            f"Le délai '{title}' expire dans {days} jours "
                            f"({event_date.isoformat()})."
                        ),
                        case_id=case_id,
                        case_reference=case_ref,
                        suggested_actions=["Planifier la préparation du dossier"],
                    )
                )

        return insights

    def _document_gap_insights(
        self,
        case_data: dict[str, Any],
        documents: list[dict[str, Any]],
        case_id: str,
        case_ref: str,
    ) -> list[InsightResult]:
        """Generate document gap insights."""
        completeness = self.case_analyzer.analyze_completeness(case_data, [], documents)

        insights: list[InsightResult] = []

        if completeness.missing_critical:
            insights.append(
                InsightResult(
                    insight_type="document_gap",
                    severity="high",
                    title="Documents critiques manquants",
                    description=(
                        f"Les documents suivants sont manquants pour un dossier "
                        f"de type '{completeness.matter_type}' : "
                        f"{', '.join(completeness.missing_critical)}."
                    ),
                    case_id=case_id,
                    case_reference=case_ref,
                    suggested_actions=[
                        f"Obtenir : {doc}" for doc in completeness.missing_critical
                    ],
                )
            )

        missing_optional = [
            e.label_fr
            for e in completeness.elements
            if not e.present and e.importance == "important"
        ]
        if missing_optional:
            insights.append(
                InsightResult(
                    insight_type="document_gap",
                    severity="medium",
                    title="Documents importants manquants",
                    description=(
                        f"Documents importants manquants : "
                        f"{', '.join(missing_optional)}."
                    ),
                    case_id=case_id,
                    case_reference=case_ref,
                    suggested_actions=[f"Demander : {doc}" for doc in missing_optional],
                )
            )

        return insights

    def _billing_insights(
        self,
        case_data: dict[str, Any],
        time_entries: list[dict[str, Any]],
        case_id: str,
        case_ref: str,
    ) -> list[InsightResult]:
        """Generate billing-related insights."""
        insights: list[InsightResult] = []

        if not time_entries:
            status = case_data.get("status", "open")
            if status in ("in_progress", "pending"):
                insights.append(
                    InsightResult(
                        insight_type="billing",
                        severity="medium",
                        title="Aucune prestation enregistrée",
                        description=(
                            "Ce dossier est en cours de traitement mais aucune "
                            "prestation n'a été enregistrée."
                        ),
                        case_id=case_id,
                        case_reference=case_ref,
                        suggested_actions=[
                            "Saisir les prestations effectuées",
                            "Vérifier si le dossier est en forfait",
                        ],
                    )
                )
            return insights

        # Check for large amounts of unbilled time
        draft_minutes = sum(
            e.get("duration_minutes", 0)
            for e in time_entries
            if e.get("status") == "draft"
        )

        if draft_minutes > 480:  # > 8 hours unbilled
            insights.append(
                InsightResult(
                    insight_type="billing",
                    severity="high",
                    title="Volume important de temps non facturé",
                    description=(
                        f"{draft_minutes} minutes ({draft_minutes / 60:.1f}h) "
                        f"de prestations en brouillon à soumettre."
                    ),
                    case_id=case_id,
                    case_reference=case_ref,
                    suggested_actions=[
                        "Soumettre les prestations en brouillon",
                        "Préparer une facture intermédiaire",
                    ],
                )
            )

        # Check for old draft entries
        today = date.today()
        old_drafts = [
            e
            for e in time_entries
            if e.get("status") == "draft"
            and self._parse_date(e.get("date")) is not None
            and (today - self._parse_date(e.get("date"))).days > 30  # type: ignore[operator]
        ]
        if old_drafts:
            insights.append(
                InsightResult(
                    insight_type="billing",
                    severity="medium",
                    title="Prestations anciennes non soumises",
                    description=(
                        f"{len(old_drafts)} prestation(s) en brouillon datant "
                        f"de plus de 30 jours."
                    ),
                    case_id=case_id,
                    case_reference=case_ref,
                    suggested_actions=[
                        "Réviser et soumettre les anciennes prestations",
                    ],
                )
            )

        return insights

    def _communication_insights(
        self,
        case_id: str,
        case_ref: str,
        emails: list[dict[str, Any]],
        calls: list[dict[str, Any]],
        contacts: list[dict[str, Any]],
    ) -> list[InsightResult]:
        """Generate communication-related insights."""
        health = self.comm_scorer.score_communication_health(
            case_id, emails, calls, contacts
        )

        insights: list[InsightResult] = []

        for gap in health.gaps:
            severity = "high" if gap.severity == "critical" else "medium"
            insights.append(
                InsightResult(
                    insight_type="communication",
                    severity=severity,
                    title=f"Rupture de communication : {gap.contact_name}",
                    description=gap.recommendation,
                    case_id=case_id,
                    case_reference=case_ref,
                    suggested_actions=[
                        f"Contacter {gap.contact_name} par email ou téléphone",
                        "Planifier un rendez-vous de suivi",
                    ],
                )
            )

        return insights

    def _contact_insights(
        self,
        contacts: list[dict[str, Any]],
        case_id: str,
        case_ref: str,
    ) -> list[InsightResult]:
        """Generate contact/conflict-related insights."""
        insights: list[InsightResult] = []

        has_client = any(c.get("role") == "client" for c in contacts)
        has_adverse = any(c.get("role") == "adverse" for c in contacts)

        if not has_client:
            insights.append(
                InsightResult(
                    insight_type="conflict",
                    severity="high",
                    title="Aucun client associé au dossier",
                    description=(
                        "Ce dossier n'a pas de client associé. "
                        "La facturation et le suivi sont impossibles."
                    ),
                    case_id=case_id,
                    case_reference=case_ref,
                    suggested_actions=["Associer un contact client au dossier"],
                )
            )

        if not has_adverse:
            insights.append(
                InsightResult(
                    insight_type="conflict",
                    severity="low",
                    title="Partie adverse non identifiée",
                    description=(
                        "Aucune partie adverse n'est enregistrée. "
                        "Cela peut être normal selon le type de dossier."
                    ),
                    case_id=case_id,
                    case_reference=case_ref,
                    suggested_actions=[
                        "Vérifier si une partie adverse doit être identifiée"
                    ],
                )
            )

        return insights

    # ------------------------------------------------------------------
    # Brain Summary (Dashboard)
    # ------------------------------------------------------------------

    async def get_brain_summary(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
    ) -> BrainSummary:
        """Generate dashboard-level intelligence summary.

        Aggregates data across all active cases to produce risk distribution,
        deadline summaries, pending actions, recent insights, workload
        prediction, and revenue at risk.

        Args:
            session: SQLAlchemy async session.
            tenant_id: UUID of the tenant.

        Returns:
            BrainSummary with comprehensive dashboard data.
        """
        today = date.today()

        # Fetch active cases
        active_cases = await self._fetch_active_cases(session, tenant_id)
        total_active = len(active_cases)

        # Risk distribution — analyze each case
        risk_dist: dict[str, int] = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        all_deadlines: list[dict[str, Any]] = []
        revenue_at_risk = 0

        for case_data in active_cases:
            cid = case_data.get("id")
            if cid is None:
                continue
            case_uuid = uuid.UUID(str(cid)) if not isinstance(cid, uuid.UUID) else cid

            contacts = await self._fetch_contacts(session, case_uuid, tenant_id)
            timeline = await self._fetch_timeline(session, case_uuid, tenant_id)
            documents = await self._fetch_documents(session, case_uuid, tenant_id)
            time_entries = await self._fetch_time_entries(session, case_uuid, tenant_id)

            case_enriched = self._enrich_case_with_billing(case_data, time_entries)

            # Risk assessment
            risk = self.case_analyzer.assess_risk(
                case_enriched, contacts, timeline, documents
            )
            risk_dist[risk.level] = risk_dist.get(risk.level, 0) + 1

            # Collect deadlines for workload prediction
            case_ref = case_data.get("reference", "")
            for event in timeline:
                event_date = self._parse_date(event.get("event_date"))
                if event_date is None:
                    continue
                title_lower = event.get("title", "").lower()
                is_deadline = event.get("category", "") in (
                    "deadline",
                    "hearing",
                    "audience",
                ) or any(
                    kw in title_lower
                    for kw in ("délai", "audience", "conclusions", "échéance")
                )
                if is_deadline and event_date >= today:
                    all_deadlines.append(
                        {
                            "deadline_date": event_date,
                            "title": event.get("title", ""),
                            "case_reference": case_ref,
                            "case_id": str(case_uuid),
                        }
                    )

            # Revenue at risk: unbilled time on high/critical risk cases
            if risk.level in ("high", "critical"):
                unbilled_cents = sum(
                    (e.get("duration_minutes", 0) / 60)
                    * (e.get("hourly_rate_cents", 0) or 0)
                    for e in time_entries
                    if e.get("status") in ("draft", "submitted")
                )
                revenue_at_risk += int(unbilled_cents)

        # Deadline summaries
        deadlines_7d = self._filter_deadlines_by_days(all_deadlines, today, 7)
        deadlines_14d = self._filter_deadlines_by_days(all_deadlines, today, 14)
        deadlines_30d = self._filter_deadlines_by_days(all_deadlines, today, 30)

        # Pending actions count
        pending_actions = await self._count_pending_actions(session, tenant_id)

        # Recent insights from DB
        recent_db_insights = await self._fetch_recent_insights(session, tenant_id)

        # Workload prediction
        workload = self.deadline_intel.predict_workload(all_deadlines)

        summary = self._build_brain_summary_text(
            total_active, risk_dist, deadlines_7d, pending_actions, revenue_at_risk
        )

        return BrainSummary(
            total_active_cases=total_active,
            risk_distribution=risk_dist,
            upcoming_deadlines_7d=deadlines_7d,
            upcoming_deadlines_14d=deadlines_14d,
            upcoming_deadlines_30d=deadlines_30d,
            pending_actions=pending_actions,
            recent_insights=recent_db_insights,
            workload_prediction=workload,
            revenue_at_risk_cents=revenue_at_risk,
            summary=summary,
            generated_at=datetime.utcnow().isoformat(),
        )

    # ------------------------------------------------------------------
    # Smart Action Suggestions
    # ------------------------------------------------------------------

    async def suggest_actions(
        self,
        session: AsyncSession,
        case_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> list[ActionSuggestion]:
        """Generate smart action suggestions for a case.

        Based on case status, timeline, matter type, and communication
        patterns, produces priority-ranked action suggestions.

        Args:
            session: SQLAlchemy async session.
            case_id: UUID of the case.
            tenant_id: UUID of the tenant.

        Returns:
            List of ActionSuggestion ordered by priority.
        """
        case_data = await self._fetch_case(session, case_id, tenant_id)
        if case_data is None:
            return []

        contacts = await self._fetch_contacts(session, case_id, tenant_id)
        timeline = await self._fetch_timeline(session, case_id, tenant_id)
        documents = await self._fetch_documents(session, case_id, tenant_id)
        time_entries = await self._fetch_time_entries(session, case_id, tenant_id)
        emails = await self._fetch_emails(session, case_id, tenant_id)
        calls = await self._fetch_calls(session, case_id, tenant_id)

        case_ref = case_data.get("reference", "")
        case_id_str = str(case_id)
        case_enriched = self._enrich_case_with_billing(case_data, time_entries)

        actions: list[ActionSuggestion] = []

        # Strategy-based actions
        strategies = self.case_analyzer.suggest_strategy(
            case_enriched, contacts, timeline
        )
        for strat in strategies:
            priority = "urgent" if strat.priority == "critical" else strat.priority
            if priority not in ("critical", "urgent", "normal"):
                priority = "normal"
            actions.append(
                ActionSuggestion(
                    action_type="suggestion",
                    title=strat.title,
                    description=strat.description,
                    priority=priority,
                    confidence=0.8,
                    trigger_source="case_analysis",
                    case_id=case_id_str,
                    case_reference=case_ref,
                    action_data={
                        "category": strat.category,
                        "rationale": strat.rationale,
                    },
                )
            )

        # Deadline-based actions
        deadline_analysis = self.deadline_intel.analyze_deadlines(
            case_enriched, timeline
        )
        for dl in deadline_analysis.deadlines:
            if dl.urgency in ("critical", "urgent"):
                actions.append(
                    ActionSuggestion(
                        action_type="alert",
                        title=f"Délai {dl.urgency} : {dl.title}",
                        description=(
                            f"Le délai '{dl.title}' expire le {dl.deadline_date.isoformat()} "
                            f"({dl.days_remaining} jour(s) restants)."
                        ),
                        priority="critical" if dl.urgency == "critical" else "urgent",
                        confidence=0.95,
                        trigger_source="deadline",
                        case_id=case_id_str,
                        case_reference=case_ref,
                        action_data={
                            "deadline_date": dl.deadline_date.isoformat(),
                            "days_remaining": dl.days_remaining,
                            "category": dl.category,
                        },
                    )
                )

        # Communication-based actions
        comm_health = self.comm_scorer.score_communication_health(
            case_id_str, emails, calls, contacts
        )
        for gap in comm_health.gaps:
            if gap.severity == "critical":
                actions.append(
                    ActionSuggestion(
                        action_type="alert",
                        title=f"Contact perdu : {gap.contact_name}",
                        description=gap.recommendation,
                        priority="urgent",
                        confidence=0.85,
                        trigger_source="communication",
                        case_id=case_id_str,
                        case_reference=case_ref,
                        action_data={
                            "contact_name": gap.contact_name,
                            "role": gap.role,
                            "days_since_contact": gap.days_since_contact,
                        },
                    )
                )

        # Billing-based actions
        unbilled_minutes = case_enriched.get("unbilled_minutes", 0)
        if unbilled_minutes > 480:
            actions.append(
                ActionSuggestion(
                    action_type="suggestion",
                    title="Facturation en retard",
                    description=(
                        f"{unbilled_minutes} minutes ({unbilled_minutes / 60:.1f}h) "
                        f"de prestations non facturées. Préparez une facture."
                    ),
                    priority="normal",
                    confidence=0.9,
                    trigger_source="billing",
                    case_id=case_id_str,
                    case_reference=case_ref,
                    action_data={"unbilled_minutes": unbilled_minutes},
                )
            )

        # Document-based actions
        completeness = self.case_analyzer.analyze_completeness(
            case_enriched, contacts, documents
        )
        if completeness.missing_critical:
            actions.append(
                ActionSuggestion(
                    action_type="suggestion",
                    title="Documents critiques manquants",
                    description=(
                        f"Obtenez les documents suivants : "
                        f"{', '.join(completeness.missing_critical)}."
                    ),
                    priority="urgent",
                    confidence=0.85,
                    trigger_source="document",
                    case_id=case_id_str,
                    case_reference=case_ref,
                    action_data={"missing": completeness.missing_critical},
                )
            )

        # Sort by priority
        priority_order = {"critical": 0, "urgent": 1, "normal": 2}
        actions.sort(key=lambda a: priority_order.get(a.priority, 99))

        return actions

    # ------------------------------------------------------------------
    # Data Fetching (async DB queries)
    # ------------------------------------------------------------------

    @staticmethod
    async def _fetch_case(
        session: AsyncSession,
        case_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> dict[str, Any] | None:
        """Fetch a case and return as dict."""
        result = await session.execute(
            select(Case).where(
                Case.id == case_id,
                Case.tenant_id == tenant_id,
            )
        )
        case = result.scalar_one_or_none()
        if case is None:
            return None
        return {
            "id": case.id,
            "reference": case.reference,
            "court_reference": case.court_reference,
            "title": case.title,
            "matter_type": case.matter_type,
            "status": case.status,
            "jurisdiction": case.jurisdiction,
            "responsible_user_id": case.responsible_user_id,
            "opened_at": case.opened_at,
            "closed_at": case.closed_at,
            "metadata": case.metadata_,
        }

    @staticmethod
    async def _fetch_contacts(
        session: AsyncSession,
        case_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> list[dict[str, Any]]:
        """Fetch contacts linked to a case with their roles."""
        result = await session.execute(
            select(Contact, CaseContact.role)
            .join(CaseContact, CaseContact.contact_id == Contact.id)
            .where(
                CaseContact.case_id == case_id,
                CaseContact.tenant_id == tenant_id,
            )
        )
        rows = result.all()
        return [
            {
                "id": contact.id,
                "contact_id": contact.id,
                "full_name": contact.full_name,
                "email": contact.email,
                "phone_e164": contact.phone_e164,
                "type": contact.type,
                "role": role,
            }
            for contact, role in rows
        ]

    @staticmethod
    async def _fetch_documents(
        session: AsyncSession,
        case_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> list[dict[str, Any]]:
        """Fetch documents linked to a case."""
        result = await session.execute(
            select(CloudDocument, DocumentCaseLink.link_type)
            .join(
                DocumentCaseLink,
                DocumentCaseLink.cloud_document_id == CloudDocument.id,
            )
            .where(
                DocumentCaseLink.case_id == case_id,
                CloudDocument.tenant_id == tenant_id,
            )
        )
        rows = result.all()
        return [
            {
                "id": doc.id,
                "name": doc.name,
                "mime_type": doc.mime_type,
                "provider": doc.provider,
                "link_type": link_type,
                "is_indexed": doc.is_indexed,
                "size_bytes": doc.size_bytes,
            }
            for doc, link_type in rows
        ]

    @staticmethod
    async def _fetch_timeline(
        session: AsyncSession,
        case_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> list[dict[str, Any]]:
        """Fetch timeline events for a case."""
        result = await session.execute(
            select(TimelineEvent)
            .where(
                TimelineEvent.case_id == case_id,
                TimelineEvent.tenant_id == tenant_id,
            )
            .order_by(TimelineEvent.event_date.asc())
        )
        events = result.scalars().all()
        return [
            {
                "id": ev.id,
                "event_date": ev.event_date,
                "event_time": ev.event_time,
                "category": ev.category,
                "title": ev.title,
                "description": ev.description,
                "actors": ev.actors,
                "source_type": ev.source_type,
                "confidence_score": ev.confidence_score,
                "is_validated": ev.is_validated,
                "is_key_event": ev.is_key_event,
            }
            for ev in events
        ]

    @staticmethod
    async def _fetch_time_entries(
        session: AsyncSession,
        case_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> list[dict[str, Any]]:
        """Fetch time entries for a case."""
        result = await session.execute(
            select(TimeEntry)
            .where(
                TimeEntry.case_id == case_id,
                TimeEntry.tenant_id == tenant_id,
            )
            .order_by(TimeEntry.date.desc())
        )
        entries = result.scalars().all()
        return [
            {
                "id": entry.id,
                "date": entry.date,
                "duration_minutes": entry.duration_minutes,
                "billable": entry.billable,
                "status": entry.status,
                "source": entry.source,
                "hourly_rate_cents": entry.hourly_rate_cents,
                "description": entry.description,
            }
            for entry in entries
        ]

    @staticmethod
    async def _fetch_calendar_events(
        session: AsyncSession,
        case_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> list[dict[str, Any]]:
        """Fetch calendar events linked to a case."""
        result = await session.execute(
            select(CalendarEvent)
            .where(
                CalendarEvent.case_id == case_id,
                CalendarEvent.tenant_id == tenant_id,
            )
            .order_by(CalendarEvent.start_time.asc())
        )
        events = result.scalars().all()
        return [
            {
                "id": ev.id,
                "title": ev.title,
                "description": ev.description,
                "start_time": ev.start_time,
                "end_time": ev.end_time,
                "location": ev.location,
                "is_all_day": ev.is_all_day,
            }
            for ev in events
        ]

    @staticmethod
    async def _fetch_emails(
        session: AsyncSession,
        case_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> list[dict[str, Any]]:
        """Fetch emails linked to a case via email threads."""
        result = await session.execute(
            select(EmailMessage)
            .join(EmailThread, EmailThread.id == EmailMessage.thread_id)
            .where(
                EmailThread.case_id == case_id,
                EmailThread.tenant_id == tenant_id,
            )
            .order_by(EmailMessage.received_at.asc())
        )
        messages = result.scalars().all()
        return [
            {
                "id": msg.id,
                "subject": msg.subject,
                "from_address": msg.from_address,
                "to_addresses": msg.to_addresses,
                "body_text": msg.body_text,
                "received_at": msg.received_at,
                "is_read": msg.is_read,
                "is_important": msg.is_important,
            }
            for msg in messages
        ]

    @staticmethod
    async def _fetch_calls(
        session: AsyncSession,
        case_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> list[dict[str, Any]]:
        """Fetch call records linked to a case."""
        result = await session.execute(
            select(CallRecord)
            .where(
                CallRecord.case_id == case_id,
                CallRecord.tenant_id == tenant_id,
            )
            .order_by(CallRecord.started_at.asc())
        )
        calls = result.scalars().all()
        return [
            {
                "id": call.id,
                "direction": call.direction,
                "caller_number": call.caller_number,
                "callee_number": call.callee_number,
                "duration_seconds": call.duration_seconds,
                "call_type": call.call_type,
                "started_at": call.started_at,
                "ended_at": call.ended_at,
                "metadata": call.metadata_,
            }
            for call in calls
        ]

    @staticmethod
    async def _fetch_active_cases(
        session: AsyncSession,
        tenant_id: uuid.UUID,
    ) -> list[dict[str, Any]]:
        """Fetch all active cases for a tenant."""
        result = await session.execute(
            select(Case)
            .where(
                Case.tenant_id == tenant_id,
                Case.status.in_(["open", "in_progress", "pending"]),
            )
            .order_by(Case.created_at.desc())
        )
        cases = result.scalars().all()
        return [
            {
                "id": c.id,
                "reference": c.reference,
                "court_reference": c.court_reference,
                "title": c.title,
                "matter_type": c.matter_type,
                "status": c.status,
                "jurisdiction": c.jurisdiction,
                "responsible_user_id": c.responsible_user_id,
                "opened_at": c.opened_at,
                "closed_at": c.closed_at,
                "metadata": c.metadata_,
            }
            for c in cases
        ]

    @staticmethod
    async def _count_pending_actions(
        session: AsyncSession,
        tenant_id: uuid.UUID,
    ) -> int:
        """Count pending brain actions for a tenant."""
        result = await session.execute(
            select(func.count())
            .select_from(BrainAction)
            .where(
                BrainAction.tenant_id == tenant_id,
                BrainAction.status == "pending",
            )
        )
        return result.scalar_one()

    @staticmethod
    async def _fetch_recent_insights(
        session: AsyncSession,
        tenant_id: uuid.UUID,
        limit: int = 20,
    ) -> list[InsightResult]:
        """Fetch recent insights from the database."""
        result = await session.execute(
            select(BrainInsight, Case.reference)
            .join(Case, Case.id == BrainInsight.case_id)
            .where(
                BrainInsight.tenant_id == tenant_id,
                BrainInsight.dismissed.is_(False),
            )
            .order_by(BrainInsight.created_at.desc())
            .limit(limit)
        )
        rows = result.all()
        return [
            InsightResult(
                insight_type=insight.insight_type,
                severity=insight.severity,
                title=insight.title,
                description=insight.description,
                case_id=str(insight.case_id),
                case_reference=case_ref,
                suggested_actions=insight.suggested_actions or [],
            )
            for insight, case_ref in rows
        ]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _enrich_case_with_billing(
        case_data: dict[str, Any],
        time_entries: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Enrich case data dict with computed billing metrics."""
        enriched = dict(case_data)

        total_minutes = sum(e.get("duration_minutes", 0) for e in time_entries)
        unbilled_minutes = sum(
            e.get("duration_minutes", 0)
            for e in time_entries
            if e.get("status") in ("draft", "submitted")
        )

        # Find most recent invoiced entry date as proxy for last invoice
        invoiced_dates = [
            e.get("date")
            for e in time_entries
            if e.get("status") == "invoiced" and e.get("date") is not None
        ]
        last_invoice_date = max(invoiced_dates) if invoiced_dates else None

        enriched["total_time_minutes"] = total_minutes
        enriched["unbilled_minutes"] = unbilled_minutes
        enriched["last_invoice_date"] = last_invoice_date

        return enriched

    @staticmethod
    def _parse_date(value: Any) -> date | None:
        """Parse a date from various input types."""
        if value is None:
            return None
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str):
            try:
                return date.fromisoformat(value)
            except (ValueError, TypeError):
                return None
        return None

    @staticmethod
    def _filter_deadlines_by_days(
        deadlines: list[dict[str, Any]],
        today: date,
        days: int,
    ) -> DeadlineSummary:
        """Filter deadlines within the next N days and return a summary."""
        cutoff = today + timedelta(days=days)
        filtered = []
        critical = 0
        urgent = 0

        for dl in deadlines:
            dl_date = dl.get("deadline_date")
            if isinstance(dl_date, str):
                try:
                    dl_date = date.fromisoformat(dl_date)
                except (ValueError, TypeError):
                    continue
            if not isinstance(dl_date, date):
                continue

            if today <= dl_date <= cutoff:
                remaining = (dl_date - today).days
                if remaining <= 3:
                    critical += 1
                elif remaining <= 7:
                    urgent += 1
                filtered.append(dl)

        return DeadlineSummary(
            total=len(filtered),
            critical=critical,
            urgent=urgent,
            deadlines=filtered,
        )

    @staticmethod
    def _build_brain_summary_text(
        total_cases: int,
        risk_dist: dict[str, int],
        deadlines_7d: DeadlineSummary,
        pending_actions: int,
        revenue_at_risk: int,
    ) -> str:
        """Build dashboard summary text in French."""
        parts: list[str] = []

        parts.append(f"{total_cases} dossier(s) actif(s)")

        high_risk = risk_dist.get("high", 0) + risk_dist.get("critical", 0)
        if high_risk > 0:
            parts.append(f"{high_risk} à risque élevé/critique")

        if deadlines_7d.total > 0:
            parts.append(f"{deadlines_7d.total} délai(s) dans les 7 prochains jours")
            if deadlines_7d.critical > 0:
                parts.append(f"dont {deadlines_7d.critical} critique(s)")

        if pending_actions > 0:
            parts.append(f"{pending_actions} action(s) en attente")

        if revenue_at_risk > 0:
            revenue_eur = revenue_at_risk / 100
            parts.append(f"{revenue_eur:,.0f} EUR de revenus à risque")

        return " — ".join(parts) + "."
