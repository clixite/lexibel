"""Case Analysis Engine — Deep analysis of individual lawyer cases.

Provides risk assessment, strategy suggestions, completeness scoring,
and intelligent recommendations based on Belgian legal practice.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class RiskFactor:
    """A single factor contributing to the overall risk score."""

    name: str
    score: float  # 0-100
    weight: float  # 0.0-1.0
    explanation: str
    category: str  # deadline, document, communication, billing, procedural


@dataclass
class RiskAssessment:
    """Complete risk assessment for a case."""

    overall_score: float  # 0-100
    level: str  # low, medium, high, critical
    factors: list[RiskFactor] = field(default_factory=list)
    summary: str = ""


@dataclass
class CompletenessElement:
    """A single element in the completeness analysis."""

    name: str
    label_fr: str
    present: bool
    required: bool
    importance: str  # critical, important, optional


@dataclass
class CompletenessReport:
    """Report on case completeness based on matter type."""

    matter_type: str
    score: float  # 0-100 percentage
    total_elements: int
    present_count: int
    missing_count: int
    elements: list[CompletenessElement] = field(default_factory=list)
    missing_critical: list[str] = field(default_factory=list)
    summary: str = ""


@dataclass
class StrategySuggestion:
    """AI-generated strategy suggestion for a case."""

    title: str
    description: str
    priority: str  # critical, high, medium, low
    rationale: str
    estimated_impact: str  # high, medium, low
    category: str  # procedural, negotiation, evidence, billing, communication


@dataclass
class HealthComponent:
    """A single component of the case health score."""

    name: str
    score: float  # 0-100
    weight: float
    details: str


@dataclass
class CaseHealth:
    """Overall health assessment of a case."""

    overall_score: float  # 0-100
    status: str  # healthy, attention_needed, at_risk, critical
    components: list[HealthComponent] = field(default_factory=list)
    summary: str = ""


# ---------------------------------------------------------------------------
# Required documents per matter type — Belgian legal practice
# ---------------------------------------------------------------------------

REQUIRED_DOCUMENTS: dict[str, list[dict[str, Any]]] = {
    "civil": [
        {
            "name": "contract",
            "label_fr": "Contrat",
            "importance": "critical",
            "keywords": ["contrat", "convention", "accord"],
        },
        {
            "name": "correspondence",
            "label_fr": "Correspondance",
            "importance": "important",
            "keywords": ["lettre", "courrier", "correspondance", "email"],
        },
        {
            "name": "id",
            "label_fr": "Pièce d'identité",
            "importance": "critical",
            "keywords": ["identité", "carte", "passeport", "id"],
        },
        {
            "name": "power_of_attorney",
            "label_fr": "Procuration",
            "importance": "critical",
            "keywords": ["procuration", "mandat", "pouvoir"],
        },
        {
            "name": "claim_calculation",
            "label_fr": "Calcul de la demande",
            "importance": "important",
            "keywords": [
                "calcul",
                "demande",
                "dommages",
                "intérêts",
                "créance",
            ],
        },
    ],
    "penal": [
        {
            "name": "complaint",
            "label_fr": "Plainte",
            "importance": "critical",
            "keywords": ["plainte", "dépôt", "pv"],
        },
        {
            "name": "police_report",
            "label_fr": "Procès-verbal de police",
            "importance": "critical",
            "keywords": ["procès-verbal", "pv", "police", "rapport"],
        },
        {
            "name": "id",
            "label_fr": "Pièce d'identité",
            "importance": "critical",
            "keywords": ["identité", "carte", "passeport", "id"],
        },
        {
            "name": "witness_statements",
            "label_fr": "Déclarations de témoins",
            "importance": "important",
            "keywords": ["témoin", "déclaration", "audition", "témoignage"],
        },
    ],
    "commercial": [
        {
            "name": "articles_of_association",
            "label_fr": "Statuts de la société",
            "importance": "critical",
            "keywords": ["statuts", "acte constitutif", "société"],
        },
        {
            "name": "financial_statements",
            "label_fr": "Comptes annuels",
            "importance": "important",
            "keywords": [
                "comptes annuels",
                "bilan",
                "financier",
                "comptable",
            ],
        },
        {
            "name": "contracts",
            "label_fr": "Contrats commerciaux",
            "importance": "critical",
            "keywords": [
                "contrat",
                "convention",
                "accord",
                "commande",
                "bon",
            ],
        },
        {
            "name": "correspondence",
            "label_fr": "Correspondance commerciale",
            "importance": "important",
            "keywords": [
                "lettre",
                "courrier",
                "email",
                "mise en demeure",
            ],
        },
    ],
    "family": [
        {
            "name": "civil_status",
            "label_fr": "Acte d'état civil",
            "importance": "critical",
            "keywords": [
                "état civil",
                "acte",
                "mariage",
                "naissance",
                "divorce",
            ],
        },
        {
            "name": "income_proof",
            "label_fr": "Preuve de revenus",
            "importance": "critical",
            "keywords": [
                "revenu",
                "salaire",
                "fiche de paie",
                "avertissement-extrait",
            ],
        },
        {
            "name": "property_inventory",
            "label_fr": "Inventaire du patrimoine",
            "importance": "important",
            "keywords": [
                "patrimoine",
                "inventaire",
                "immobilier",
                "mobilier",
                "bien",
            ],
        },
    ],
    "fiscal": [
        {
            "name": "tax_returns",
            "label_fr": "Déclarations fiscales",
            "importance": "critical",
            "keywords": [
                "déclaration",
                "fiscal",
                "impôt",
                "IPP",
                "ISOC",
            ],
        },
        {
            "name": "assessment_notice",
            "label_fr": "Avertissement-extrait de rôle",
            "importance": "critical",
            "keywords": [
                "avertissement",
                "extrait de rôle",
                "enrôlement",
                "cotisation",
            ],
        },
        {
            "name": "correspondence",
            "label_fr": "Correspondance avec l'administration",
            "importance": "important",
            "keywords": [
                "administration",
                "SPF",
                "finances",
                "contrôle",
                "rectification",
            ],
        },
    ],
    "social": [
        {
            "name": "employment_contract",
            "label_fr": "Contrat de travail",
            "importance": "critical",
            "keywords": ["contrat de travail", "emploi", "engagement"],
        },
        {
            "name": "payslips",
            "label_fr": "Fiches de paie",
            "importance": "important",
            "keywords": ["fiche de paie", "salaire", "rémunération"],
        },
        {
            "name": "medical_certificate",
            "label_fr": "Certificat médical",
            "importance": "important",
            "keywords": [
                "certificat",
                "médical",
                "incapacité",
                "maladie",
            ],
        },
    ],
}

# Status progression expectations (days from opening)
STATUS_TIMELINE: dict[str, dict[str, int]] = {
    "open": {"expected_max_days": 14},
    "in_progress": {"expected_max_days": 180},
    "pending": {"expected_max_days": 90},
}


# ---------------------------------------------------------------------------
# CaseAnalyzer
# ---------------------------------------------------------------------------


class CaseAnalyzer:
    """Deep case analysis engine for Belgian legal practice.

    Provides risk assessment, completeness scoring, strategy suggestions,
    and overall case health evaluation. All analysis is deterministic and
    rule-based — no LLM calls are made within this class.
    """

    # ------------------------------------------------------------------
    # Risk Assessment
    # ------------------------------------------------------------------

    def assess_risk(
        self,
        case_data: dict[str, Any],
        contacts: list[dict[str, Any]],
        timeline: list[dict[str, Any]],
        documents: list[dict[str, Any]],
    ) -> RiskAssessment:
        """Calculate comprehensive risk score for a case.

        Evaluates multiple risk factors including deadline proximity,
        missing documentation, adverse party representation, case aging,
        billing gaps, and communication gaps.

        Args:
            case_data: Serialized Case model fields.
            contacts: List of contacts linked to the case with roles.
            timeline: List of timeline events for the case.
            documents: List of documents linked to the case.

        Returns:
            RiskAssessment with overall score, level, and detailed factors.
        """
        factors: list[RiskFactor] = []

        factors.append(self._assess_deadline_risk(timeline))
        factors.append(self._assess_document_risk(case_data, documents))
        factors.append(self._assess_adverse_counsel_risk(contacts))
        factors.append(self._assess_case_age_risk(case_data))
        factors.append(self._assess_billing_risk(case_data))
        factors.append(self._assess_communication_risk(timeline, contacts))

        # Weighted average — only include factors with weight > 0
        total_weight = sum(f.weight for f in factors if f.weight > 0)
        if total_weight > 0:
            overall = sum(f.score * f.weight for f in factors) / total_weight
        else:
            overall = 0.0

        overall = min(100.0, max(0.0, overall))

        level = self._score_to_level(overall)

        return RiskAssessment(
            overall_score=round(overall, 1),
            level=level,
            factors=factors,
            summary=self._build_risk_summary(level, factors),
        )

    def _assess_deadline_risk(self, timeline: list[dict[str, Any]]) -> RiskFactor:
        """Evaluate risk from approaching deadlines."""
        today = date.today()
        closest_days = None

        for event in timeline:
            event_date = event.get("event_date")
            if event_date is None:
                continue
            if isinstance(event_date, str):
                try:
                    event_date = date.fromisoformat(event_date)
                except (ValueError, TypeError):
                    continue
            elif isinstance(event_date, datetime):
                event_date = event_date.date()

            days_until = (event_date - today).days
            if days_until >= 0:
                if closest_days is None or days_until < closest_days:
                    closest_days = days_until

        if closest_days is None:
            # No upcoming deadlines — mild concern (no tracking)
            return RiskFactor(
                name="deadline_proximity",
                score=30.0,
                weight=0.25,
                explanation="Aucun délai à venir identifié dans la chronologie",
                category="deadline",
            )

        if closest_days <= 3:
            score = 95.0
            explanation = (
                f"Délai critique dans {closest_days} jour(s) — action immédiate requise"
            )
        elif closest_days <= 7:
            score = 75.0
            explanation = (
                f"Délai urgent dans {closest_days} jours — préparation nécessaire"
            )
        elif closest_days <= 14:
            score = 45.0
            explanation = f"Délai dans {closest_days} jours — à surveiller"
        elif closest_days <= 30:
            score = 20.0
            explanation = f"Prochain délai dans {closest_days} jours"
        else:
            score = 5.0
            explanation = f"Prochain délai dans {closest_days} jours — sous contrôle"

        return RiskFactor(
            name="deadline_proximity",
            score=score,
            weight=0.25,
            explanation=explanation,
            category="deadline",
        )

    def _assess_document_risk(
        self,
        case_data: dict[str, Any],
        documents: list[dict[str, Any]],
    ) -> RiskFactor:
        """Evaluate risk from missing critical documents."""
        matter_type = case_data.get("matter_type", "civil")
        required = REQUIRED_DOCUMENTS.get(matter_type, REQUIRED_DOCUMENTS["civil"])

        doc_names_lower = [
            d.get("name", "").lower() for d in documents if d.get("name")
        ]
        doc_names_combined = " ".join(doc_names_lower)

        missing_critical = 0
        missing_important = 0

        for req in required:
            found = any(kw in doc_names_combined for kw in req.get("keywords", []))
            if not found:
                if req["importance"] == "critical":
                    missing_critical += 1
                elif req["importance"] == "important":
                    missing_important += 1

        total_required = len(required)

        if total_required == 0:
            score = 0.0
            explanation = "Aucun document requis pour ce type de dossier"
        elif missing_critical > 0:
            score = min(90.0, 50.0 + missing_critical * 20.0)
            explanation = (
                f"{missing_critical} document(s) critique(s) manquant(s), "
                f"{missing_important} document(s) importants manquant(s)"
            )
        elif missing_important > 0:
            score = min(50.0, 20.0 + missing_important * 15.0)
            explanation = f"{missing_important} document(s) important(s) manquant(s)"
        else:
            score = 5.0
            explanation = "Tous les documents requis sont présents"

        return RiskFactor(
            name="missing_documents",
            score=score,
            weight=0.20,
            explanation=explanation,
            category="document",
        )

    def _assess_adverse_counsel_risk(
        self, contacts: list[dict[str, Any]]
    ) -> RiskFactor:
        """Evaluate risk from no adverse party or no adverse counsel identified."""
        has_adverse = any(c.get("role") == "adverse" for c in contacts)
        has_client = any(c.get("role") == "client" for c in contacts)

        if not has_client:
            return RiskFactor(
                name="adverse_counsel",
                score=70.0,
                weight=0.10,
                explanation="Aucun client identifié dans le dossier",
                category="procedural",
            )

        if not has_adverse:
            return RiskFactor(
                name="adverse_counsel",
                score=40.0,
                weight=0.10,
                explanation="Aucune partie adverse identifiée — à vérifier",
                category="procedural",
            )

        return RiskFactor(
            name="adverse_counsel",
            score=5.0,
            weight=0.10,
            explanation="Partie adverse identifiée dans le dossier",
            category="procedural",
        )

    def _assess_case_age_risk(self, case_data: dict[str, Any]) -> RiskFactor:
        """Evaluate risk from case age vs current status."""
        today = date.today()
        opened_at = case_data.get("opened_at")
        status = case_data.get("status", "open")

        if opened_at is None:
            return RiskFactor(
                name="case_age",
                score=20.0,
                weight=0.15,
                explanation="Date d'ouverture inconnue",
                category="procedural",
            )

        if isinstance(opened_at, str):
            try:
                opened_at = date.fromisoformat(opened_at)
            except (ValueError, TypeError):
                return RiskFactor(
                    name="case_age",
                    score=20.0,
                    weight=0.15,
                    explanation="Date d'ouverture invalide",
                    category="procedural",
                )
        elif isinstance(opened_at, datetime):
            opened_at = opened_at.date()

        age_days = (today - opened_at).days
        expected = STATUS_TIMELINE.get(status, {}).get("expected_max_days", 180)

        if status in ("closed", "archived"):
            score = 0.0
            explanation = "Dossier clôturé"
        elif age_days > expected * 2:
            score = 85.0
            explanation = (
                f"Dossier ouvert depuis {age_days} jours en statut '{status}' "
                f"— largement au-delà du délai attendu ({expected}j)"
            )
        elif age_days > expected:
            ratio = age_days / expected
            score = min(70.0, 40.0 + (ratio - 1.0) * 30.0)
            explanation = (
                f"Dossier ouvert depuis {age_days} jours en statut '{status}' "
                f"— au-delà du délai attendu ({expected}j)"
            )
        else:
            ratio = age_days / expected if expected > 0 else 0
            score = ratio * 20.0
            explanation = (
                f"Dossier ouvert depuis {age_days} jours en statut '{status}' "
                f"— dans les délais normaux"
            )

        return RiskFactor(
            name="case_age",
            score=min(100.0, max(0.0, score)),
            weight=0.15,
            explanation=explanation,
            category="procedural",
        )

    def _assess_billing_risk(self, case_data: dict[str, Any]) -> RiskFactor:
        """Evaluate risk from billing gaps (time entries not invoiced)."""
        total_time_minutes = case_data.get("total_time_minutes", 0)
        unbilled_minutes = case_data.get("unbilled_minutes", 0)
        last_invoice_date = case_data.get("last_invoice_date")
        today = date.today()

        if total_time_minutes == 0:
            return RiskFactor(
                name="billing_gap",
                score=25.0,
                weight=0.15,
                explanation="Aucune prestation enregistrée — temps à saisir",
                category="billing",
            )

        unbilled_ratio = (
            unbilled_minutes / total_time_minutes if total_time_minutes > 0 else 0
        )

        if last_invoice_date:
            if isinstance(last_invoice_date, str):
                try:
                    last_invoice_date = date.fromisoformat(last_invoice_date)
                except (ValueError, TypeError):
                    last_invoice_date = None
            elif isinstance(last_invoice_date, datetime):
                last_invoice_date = last_invoice_date.date()

        days_since_invoice = None
        if last_invoice_date:
            days_since_invoice = (today - last_invoice_date).days

        score = 0.0

        # Unbilled time component
        if unbilled_ratio > 0.8:
            score += 50.0
        elif unbilled_ratio > 0.5:
            score += 30.0
        elif unbilled_ratio > 0.2:
            score += 15.0

        # Time since last invoice component
        if days_since_invoice is not None:
            if days_since_invoice > 90:
                score += 40.0
            elif days_since_invoice > 60:
                score += 25.0
            elif days_since_invoice > 30:
                score += 10.0
        elif total_time_minutes > 120:
            # Has time but never invoiced
            score += 35.0

        score = min(100.0, score)

        if score >= 60:
            explanation = (
                f"{unbilled_minutes} minutes non facturées "
                f"({unbilled_ratio:.0%} du temps total)"
            )
            if days_since_invoice:
                explanation += f" — dernière facture il y a {days_since_invoice} jours"
        elif score >= 30:
            explanation = "Facturation en retard — temps non facturé à vérifier"
        else:
            explanation = "Facturation à jour"

        return RiskFactor(
            name="billing_gap",
            score=score,
            weight=0.15,
            explanation=explanation,
            category="billing",
        )

    def _assess_communication_risk(
        self,
        timeline: list[dict[str, Any]],
        contacts: list[dict[str, Any]],
    ) -> RiskFactor:
        """Evaluate risk from communication gaps."""
        today = date.today()
        has_client = any(c.get("role") == "client" for c in contacts)

        if not has_client:
            return RiskFactor(
                name="communication_gap",
                score=40.0,
                weight=0.15,
                explanation="Pas de client identifié — communication impossible à évaluer",
                category="communication",
            )

        # Find most recent communication event
        comm_categories = {"email", "call", "meeting"}
        most_recent = None

        for event in timeline:
            category = event.get("category", "")
            if category not in comm_categories:
                continue
            event_date = event.get("event_date")
            if event_date is None:
                continue
            if isinstance(event_date, str):
                try:
                    event_date = date.fromisoformat(event_date)
                except (ValueError, TypeError):
                    continue
            elif isinstance(event_date, datetime):
                event_date = event_date.date()

            if most_recent is None or event_date > most_recent:
                most_recent = event_date

        if most_recent is None:
            return RiskFactor(
                name="communication_gap",
                score=60.0,
                weight=0.15,
                explanation="Aucune communication enregistrée dans le dossier",
                category="communication",
            )

        days_since = (today - most_recent).days

        if days_since > 30:
            score = 80.0
            explanation = (
                f"Aucune communication depuis {days_since} jours — "
                f"risque de perte de contact avec le client"
            )
        elif days_since > 14:
            score = 50.0
            explanation = (
                f"Dernière communication il y a {days_since} jours — suivi recommandé"
            )
        elif days_since > 7:
            score = 25.0
            explanation = f"Dernière communication il y a {days_since} jours"
        else:
            score = 5.0
            explanation = (
                f"Communication récente (il y a {days_since} jour(s)) — sous contrôle"
            )

        return RiskFactor(
            name="communication_gap",
            score=score,
            weight=0.15,
            explanation=explanation,
            category="communication",
        )

    # ------------------------------------------------------------------
    # Completeness Analysis
    # ------------------------------------------------------------------

    def analyze_completeness(
        self,
        case_data: dict[str, Any],
        contacts: list[dict[str, Any]],
        documents: list[dict[str, Any]],
        matter_type: str | None = None,
    ) -> CompletenessReport:
        """Check case completeness against required elements for the matter type.

        Compares documents present in the case against the standard checklist
        for the given matter type (civil, penal, commercial, family, fiscal, social).

        Args:
            case_data: Serialized Case model fields.
            contacts: Contacts linked to the case with roles.
            documents: Documents linked to the case.
            matter_type: Override matter type (defaults to case_data value).

        Returns:
            CompletenessReport with score, elements, and missing critical items.
        """
        mt = matter_type or case_data.get("matter_type", "civil")
        required = REQUIRED_DOCUMENTS.get(mt, REQUIRED_DOCUMENTS.get("civil", []))

        doc_names_lower = [
            d.get("name", "").lower() for d in documents if d.get("name")
        ]
        doc_names_combined = " ".join(doc_names_lower)

        elements: list[CompletenessElement] = []
        present_count = 0
        missing_critical: list[str] = []

        for req in required:
            found = any(kw in doc_names_combined for kw in req.get("keywords", []))
            elem = CompletenessElement(
                name=req["name"],
                label_fr=req["label_fr"],
                present=found,
                required=req["importance"] in ("critical", "important"),
                importance=req["importance"],
            )
            elements.append(elem)

            if found:
                present_count += 1
            elif req["importance"] == "critical":
                missing_critical.append(req["label_fr"])

        total = len(required)
        score = (present_count / total * 100.0) if total > 0 else 100.0

        if missing_critical:
            summary = (
                f"Dossier incomplet ({score:.0f}%) — "
                f"documents critiques manquants : {', '.join(missing_critical)}"
            )
        elif score < 100:
            summary = (
                f"Dossier partiellement complet ({score:.0f}%) — "
                f"documents importants manquants"
            )
        else:
            summary = "Dossier complet — tous les documents requis sont présents"

        return CompletenessReport(
            matter_type=mt,
            score=round(score, 1),
            total_elements=total,
            present_count=present_count,
            missing_count=total - present_count,
            elements=elements,
            missing_critical=missing_critical,
            summary=summary,
        )

    # ------------------------------------------------------------------
    # Strategy Suggestions
    # ------------------------------------------------------------------

    def suggest_strategy(
        self,
        case_data: dict[str, Any],
        contacts: list[dict[str, Any]],
        timeline: list[dict[str, Any]],
        matter_type: str | None = None,
    ) -> list[StrategySuggestion]:
        """Generate AI strategy suggestions based on case data.

        Produces rule-based strategy suggestions considering the matter type,
        current status, timeline events, and contact configuration.

        Args:
            case_data: Serialized Case model fields.
            contacts: Contacts linked to the case with roles.
            timeline: Timeline events for the case.
            matter_type: Override matter type.

        Returns:
            List of StrategySuggestion ordered by priority.
        """
        suggestions: list[StrategySuggestion] = []
        mt = matter_type or case_data.get("matter_type", "civil")
        status = case_data.get("status", "open")
        today = date.today()

        # --- Status-based suggestions ---
        if status == "open":
            suggestions.append(
                StrategySuggestion(
                    title="Compléter le dossier d'introduction",
                    description=(
                        "Le dossier est en statut 'ouvert'. Rassemblez toutes les pièces "
                        "nécessaires et vérifiez la complétude avant de passer en traitement."
                    ),
                    priority="high",
                    rationale="Un dossier incomplet retarde la procédure et augmente les risques",
                    estimated_impact="high",
                    category="procedural",
                )
            )

        if status == "pending":
            opened_at = case_data.get("opened_at")
            if opened_at:
                if isinstance(opened_at, str):
                    try:
                        opened_at = date.fromisoformat(opened_at)
                    except (ValueError, TypeError):
                        opened_at = None
                elif isinstance(opened_at, datetime):
                    opened_at = opened_at.date()
            if opened_at and (today - opened_at).days > 60:
                suggestions.append(
                    StrategySuggestion(
                        title="Relancer le dossier en attente",
                        description=(
                            "Ce dossier est en attente depuis plus de 60 jours. "
                            "Contactez le tribunal ou la partie adverse pour débloquer la situation."
                        ),
                        priority="high",
                        rationale="Les dossiers en attente prolongée risquent la péremption",
                        estimated_impact="high",
                        category="procedural",
                    )
                )

        # --- Contact-based suggestions ---
        has_adverse = any(c.get("role") == "adverse" for c in contacts)
        has_client = any(c.get("role") == "client" for c in contacts)

        if not has_adverse and status in ("open", "in_progress"):
            suggestions.append(
                StrategySuggestion(
                    title="Identifier la partie adverse",
                    description=(
                        "Aucune partie adverse n'est enregistrée. "
                        "Identifiez et ajoutez la partie adverse ainsi que son conseil éventuel."
                    ),
                    priority="high",
                    rationale="La connaissance de la partie adverse est essentielle pour la stratégie",
                    estimated_impact="medium",
                    category="procedural",
                )
            )

        if not has_client:
            suggestions.append(
                StrategySuggestion(
                    title="Lier un client au dossier",
                    description=(
                        "Aucun client n'est associé à ce dossier. "
                        "Associez le contact client pour assurer le suivi et la facturation."
                    ),
                    priority="critical",
                    rationale="Un dossier sans client ne peut être correctement géré ni facturé",
                    estimated_impact="high",
                    category="billing",
                )
            )

        # --- Matter-type-specific suggestions ---
        suggestions.extend(self._matter_type_suggestions(mt, case_data, timeline))

        # --- Communication suggestions ---
        recent_comms = self._count_recent_events(
            timeline, categories={"email", "call", "meeting"}, days=14
        )
        if recent_comms == 0 and has_client and status not in ("closed", "archived"):
            suggestions.append(
                StrategySuggestion(
                    title="Reprendre contact avec le client",
                    description=(
                        "Aucune communication dans les 14 derniers jours. "
                        "Envoyez un point de situation au client pour maintenir la relation."
                    ),
                    priority="medium",
                    rationale="Un silence prolongé peut générer de l'anxiété chez le client",
                    estimated_impact="medium",
                    category="communication",
                )
            )

        # --- Timeline-based suggestions ---
        if len(timeline) == 0 and status != "open":
            suggestions.append(
                StrategySuggestion(
                    title="Documenter la chronologie du dossier",
                    description=(
                        "La chronologie est vide. Ajoutez les événements clés "
                        "pour disposer d'une vue d'ensemble du dossier."
                    ),
                    priority="medium",
                    rationale="Une chronologie vide empêche l'analyse intelligente du dossier",
                    estimated_impact="medium",
                    category="evidence",
                )
            )

        # Sort by priority
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        suggestions.sort(key=lambda s: priority_order.get(s.priority, 99))

        return suggestions

    def _matter_type_suggestions(
        self,
        matter_type: str,
        case_data: dict[str, Any],
        timeline: list[dict[str, Any]],
    ) -> list[StrategySuggestion]:
        """Generate matter-type-specific suggestions."""
        suggestions: list[StrategySuggestion] = []
        status = case_data.get("status", "open")

        if matter_type == "civil" and status == "in_progress":
            suggestions.append(
                StrategySuggestion(
                    title="Vérifier le calendrier de mise en état",
                    description=(
                        "En matière civile, vérifiez les délais de conclusions "
                        "fixés par le calendrier de mise en état."
                    ),
                    priority="high",
                    rationale="Le non-respect du calendrier peut entraîner l'écartement des conclusions",
                    estimated_impact="high",
                    category="procedural",
                )
            )

        if matter_type == "penal":
            suggestions.append(
                StrategySuggestion(
                    title="Vérifier les délais de prescription",
                    description=(
                        "En matière pénale, vérifiez les délais de prescription "
                        "applicables (Art. 21-25 du Titre préliminaire du C.I.Cr.)."
                    ),
                    priority="high",
                    rationale="La prescription peut entraîner l'extinction de l'action publique",
                    estimated_impact="high",
                    category="procedural",
                )
            )

        if matter_type == "family" and status in ("open", "in_progress"):
            suggestions.append(
                StrategySuggestion(
                    title="Envisager la médiation familiale",
                    description=(
                        "En droit familial, la médiation peut aboutir à un accord plus rapidement "
                        "et à moindre coût qu'une procédure contentieuse."
                    ),
                    priority="medium",
                    rationale="La médiation est encouragée par la loi (Art. 1730 C.J.)",
                    estimated_impact="high",
                    category="negotiation",
                )
            )

        if matter_type == "fiscal":
            suggestions.append(
                StrategySuggestion(
                    title="Vérifier les voies de recours administratives",
                    description=(
                        "Avant toute action judiciaire, assurez-vous que les "
                        "réclamations administratives ont été correctement introduites."
                    ),
                    priority="high",
                    rationale="L'épuisement des voies administratives est un préalable obligatoire",
                    estimated_impact="high",
                    category="procedural",
                )
            )

        if matter_type == "commercial" and status == "open":
            suggestions.append(
                StrategySuggestion(
                    title="Évaluer une mise en demeure préalable",
                    description=(
                        "En matière commerciale, une mise en demeure préalable "
                        "est souvent requise et peut favoriser une résolution amiable."
                    ),
                    priority="high",
                    rationale="La mise en demeure interrompt certains délais et ouvre le droit à des intérêts",
                    estimated_impact="medium",
                    category="negotiation",
                )
            )

        if matter_type == "social":
            suggestions.append(
                StrategySuggestion(
                    title="Vérifier la compétence du tribunal du travail",
                    description=(
                        "Confirmez la compétence territoriale du tribunal du travail "
                        "et les règles de procédure spécifiques au droit social."
                    ),
                    priority="medium",
                    rationale="Le droit social belge prévoit des règles de compétence spécifiques",
                    estimated_impact="medium",
                    category="procedural",
                )
            )

        return suggestions

    # ------------------------------------------------------------------
    # Case Health
    # ------------------------------------------------------------------

    def calculate_case_health(
        self,
        case_data: dict[str, Any],
        contacts: list[dict[str, Any]],
        timeline: list[dict[str, Any]],
        time_entries: list[dict[str, Any]],
    ) -> CaseHealth:
        """Calculate the overall health score of a case.

        Combines multiple components: completeness, activity recency, billing
        status, communication quality, and deadline compliance into a single
        weighted health score.

        Args:
            case_data: Serialized Case model fields.
            contacts: Contacts linked to the case.
            timeline: Timeline events for the case.
            time_entries: Time entries for the case.

        Returns:
            CaseHealth with overall score, status, and component breakdown.
        """
        components: list[HealthComponent] = []

        # 1. Completeness component
        completeness = self._health_completeness(case_data, contacts)
        components.append(completeness)

        # 2. Activity recency component
        activity = self._health_activity(timeline, time_entries)
        components.append(activity)

        # 3. Billing status component
        billing = self._health_billing(time_entries)
        components.append(billing)

        # 4. Communication component
        communication = self._health_communication(timeline, contacts)
        components.append(communication)

        # 5. Deadline compliance component
        deadline = self._health_deadline_compliance(timeline)
        components.append(deadline)

        # Weighted overall
        total_weight = sum(c.weight for c in components)
        if total_weight > 0:
            overall = sum(c.score * c.weight for c in components) / total_weight
        else:
            overall = 50.0

        overall = min(100.0, max(0.0, round(overall, 1)))
        status = self._health_status(overall)

        return CaseHealth(
            overall_score=overall,
            status=status,
            components=components,
            summary=self._build_health_summary(status, components),
        )

    def _health_completeness(
        self,
        case_data: dict[str, Any],
        contacts: list[dict[str, Any]],
    ) -> HealthComponent:
        """Health component: case information completeness."""
        score = 100.0

        if not case_data.get("title"):
            score -= 20.0
        if not case_data.get("matter_type"):
            score -= 20.0
        if not case_data.get("jurisdiction"):
            score -= 10.0
        if not any(c.get("role") == "client" for c in contacts):
            score -= 30.0
        if not any(c.get("role") == "adverse" for c in contacts):
            score -= 10.0
        if (
            not case_data.get("court_reference")
            and case_data.get("status") == "in_progress"
        ):
            score -= 10.0

        return HealthComponent(
            name="completeness",
            score=max(0.0, score),
            weight=0.20,
            details=f"Complétude des informations du dossier : {max(0.0, score):.0f}%",
        )

    def _health_activity(
        self,
        timeline: list[dict[str, Any]],
        time_entries: list[dict[str, Any]],
    ) -> HealthComponent:
        """Health component: recent activity on the case."""
        today = date.today()
        most_recent = None

        # Check timeline events
        for event in timeline:
            event_date = event.get("event_date")
            if event_date is None:
                continue
            if isinstance(event_date, str):
                try:
                    event_date = date.fromisoformat(event_date)
                except (ValueError, TypeError):
                    continue
            elif isinstance(event_date, datetime):
                event_date = event_date.date()
            if most_recent is None or event_date > most_recent:
                most_recent = event_date

        # Check time entries
        for entry in time_entries:
            entry_date = entry.get("date")
            if entry_date is None:
                continue
            if isinstance(entry_date, str):
                try:
                    entry_date = date.fromisoformat(entry_date)
                except (ValueError, TypeError):
                    continue
            elif isinstance(entry_date, datetime):
                entry_date = entry_date.date()
            if most_recent is None or entry_date > most_recent:
                most_recent = entry_date

        if most_recent is None:
            return HealthComponent(
                name="activity",
                score=20.0,
                weight=0.25,
                details="Aucune activité enregistrée",
            )

        days_since = (today - most_recent).days

        if days_since <= 3:
            score = 100.0
        elif days_since <= 7:
            score = 85.0
        elif days_since <= 14:
            score = 65.0
        elif days_since <= 30:
            score = 40.0
        elif days_since <= 60:
            score = 20.0
        else:
            score = 5.0

        return HealthComponent(
            name="activity",
            score=score,
            weight=0.25,
            details=f"Dernière activité il y a {days_since} jour(s)",
        )

    def _health_billing(self, time_entries: list[dict[str, Any]]) -> HealthComponent:
        """Health component: billing status."""
        if not time_entries:
            return HealthComponent(
                name="billing",
                score=50.0,
                weight=0.20,
                details="Aucune prestation enregistrée",
            )

        total = len(time_entries)
        draft = sum(1 for e in time_entries if e.get("status") == "draft")
        submitted = sum(1 for e in time_entries if e.get("status") == "submitted")
        approved = sum(1 for e in time_entries if e.get("status") == "approved")
        invoiced = sum(1 for e in time_entries if e.get("status") == "invoiced")

        if total == 0:
            return HealthComponent(
                name="billing",
                score=50.0,
                weight=0.20,
                details="Aucune prestation enregistrée",
            )

        invoiced_ratio = invoiced / total
        processed_ratio = (approved + invoiced) / total

        if invoiced_ratio > 0.8:
            score = 95.0
        elif processed_ratio > 0.7:
            score = 75.0
        elif processed_ratio > 0.4:
            score = 55.0
        elif draft / total > 0.7:
            score = 30.0
        else:
            score = 40.0

        return HealthComponent(
            name="billing",
            score=score,
            weight=0.20,
            details=(
                f"{invoiced} facturée(s), {approved} approuvée(s), "
                f"{submitted} soumise(s), {draft} brouillon(s) sur {total} prestations"
            ),
        )

    def _health_communication(
        self,
        timeline: list[dict[str, Any]],
        contacts: list[dict[str, Any]],
    ) -> HealthComponent:
        """Health component: communication quality."""
        has_client = any(c.get("role") == "client" for c in contacts)
        if not has_client:
            return HealthComponent(
                name="communication",
                score=30.0,
                weight=0.20,
                details="Pas de client identifié",
            )

        recent_7d = self._count_recent_events(
            timeline, categories={"email", "call", "meeting"}, days=7
        )
        recent_30d = self._count_recent_events(
            timeline, categories={"email", "call", "meeting"}, days=30
        )

        if recent_7d >= 2:
            score = 95.0
        elif recent_7d >= 1:
            score = 80.0
        elif recent_30d >= 3:
            score = 60.0
        elif recent_30d >= 1:
            score = 40.0
        else:
            score = 10.0

        return HealthComponent(
            name="communication",
            score=score,
            weight=0.20,
            details=(
                f"{recent_7d} communication(s) cette semaine, {recent_30d} ce mois"
            ),
        )

    def _health_deadline_compliance(
        self, timeline: list[dict[str, Any]]
    ) -> HealthComponent:
        """Health component: deadline management."""
        today = date.today()
        overdue = 0
        upcoming = 0

        for event in timeline:
            event_date = event.get("event_date")
            if event_date is None:
                continue
            if isinstance(event_date, str):
                try:
                    event_date = date.fromisoformat(event_date)
                except (ValueError, TypeError):
                    continue
            elif isinstance(event_date, datetime):
                event_date = event_date.date()

            category = event.get("category", "")
            # Consider events that look like deadlines
            is_deadline = category in ("deadline", "hearing", "audience") or any(
                kw in event.get("title", "").lower()
                for kw in ("délai", "audience", "deadline", "échéance", "conclusions")
            )
            if not is_deadline:
                continue

            days_until = (event_date - today).days
            if days_until < 0:
                # Past deadline — check if it was validated (handled)
                if not event.get("is_validated", False):
                    overdue += 1
            elif days_until <= 7:
                upcoming += 1

        if overdue > 0:
            score = max(0.0, 30.0 - overdue * 15.0)
            details = f"{overdue} délai(s) dépassé(s), {upcoming} à venir cette semaine"
        elif upcoming > 2:
            score = 50.0
            details = f"{upcoming} délais à venir cette semaine — charge élevée"
        elif upcoming > 0:
            score = 75.0
            details = f"{upcoming} délai(s) à venir cette semaine"
        else:
            score = 95.0
            details = "Aucun délai critique à court terme"

        return HealthComponent(
            name="deadline_compliance",
            score=max(0.0, score),
            weight=0.15,
            details=details,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _score_to_level(score: float) -> str:
        """Convert a 0-100 risk score to a severity level."""
        if score >= 75:
            return "critical"
        if score >= 50:
            return "high"
        if score >= 25:
            return "medium"
        return "low"

    @staticmethod
    def _health_status(score: float) -> str:
        """Convert a 0-100 health score to a status label."""
        if score >= 75:
            return "healthy"
        if score >= 50:
            return "attention_needed"
        if score >= 25:
            return "at_risk"
        return "critical"

    @staticmethod
    def _count_recent_events(
        timeline: list[dict[str, Any]],
        categories: set[str],
        days: int,
    ) -> int:
        """Count timeline events of given categories within the last N days."""
        cutoff = date.today() - timedelta(days=days)
        count = 0
        for event in timeline:
            if event.get("category", "") not in categories:
                continue
            event_date = event.get("event_date")
            if event_date is None:
                continue
            if isinstance(event_date, str):
                try:
                    event_date = date.fromisoformat(event_date)
                except (ValueError, TypeError):
                    continue
            elif isinstance(event_date, datetime):
                event_date = event_date.date()
            if event_date >= cutoff:
                count += 1
        return count

    @staticmethod
    def _build_risk_summary(level: str, factors: list[RiskFactor]) -> str:
        """Build a human-readable risk summary in French."""
        level_labels = {
            "critical": "Risque critique",
            "high": "Risque élevé",
            "medium": "Risque modéré",
            "low": "Risque faible",
        }
        label = level_labels.get(level, "Risque inconnu")

        top_factors = sorted(
            [f for f in factors if f.score >= 40],
            key=lambda f: f.score * f.weight,
            reverse=True,
        )[:3]

        if top_factors:
            details = " ; ".join(f.explanation for f in top_factors)
            return f"{label}. Points d'attention : {details}"
        return f"{label}. Aucun facteur de risque majeur identifié."

    @staticmethod
    def _build_health_summary(status: str, components: list[HealthComponent]) -> str:
        """Build a human-readable health summary in French."""
        status_labels = {
            "healthy": "Dossier en bonne santé",
            "attention_needed": "Dossier nécessitant de l'attention",
            "at_risk": "Dossier à risque",
            "critical": "Dossier en état critique",
        }
        label = status_labels.get(status, "État inconnu")

        weak = sorted(
            [c for c in components if c.score < 50],
            key=lambda c: c.score,
        )[:3]

        if weak:
            details = " ; ".join(c.details for c in weak)
            return f"{label}. Points faibles : {details}"
        return f"{label}. Tous les indicateurs sont satisfaisants."
