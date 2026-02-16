"""DueDiligenceAgent — automated legal due diligence analysis.

Steps:
1. Gather case entities from events/documents
2. Extract entities (NER)
3. Search graph for entity history
4. Check World-Check/sanctions lists (stub)
5. Cross-reference with Belgian BCE/KBO (stub)
6. Generate risk report
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

from apps.api.services.graph.ner_service import NERService


@dataclass
class EntityRisk:
    """Risk assessment for a single entity."""

    entity_name: str
    entity_type: str  # PERSON, ORGANIZATION
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    risk_score: float  # 0.0 to 1.0
    flags: list[str] = field(default_factory=list)
    sanctions_hit: bool = False
    bce_status: str = ""  # active, dissolved, unknown
    sources: list[str] = field(default_factory=list)


@dataclass
class DueDiligenceReport:
    """Full due diligence report for a case."""

    case_id: str
    generated_at: str = ""
    entities: list[EntityRisk] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)
    sanctions_hits: int = 0
    overall_risk: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL
    recommendations: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    total_entities_checked: int = 0


# ── Sanctions / watchlist stubs ──

_SANCTIONS_LIST = {
    "sanctioned person": {"list": "EU Sanctions", "reason": "Financial sanctions"},
    "suspicious corp sa": {"list": "World-Check", "reason": "Money laundering"},
}

# ── BCE/KBO status stubs (Belgian business registry) ──

_BCE_REGISTRY = {
    "acme sa": {"status": "active", "bce_number": "0123.456.789", "sector": "Services"},
    "defunct sprl": {
        "status": "dissolved",
        "bce_number": "0987.654.321",
        "sector": "Unknown",
    },
}

# ── Risk keywords ──

_HIGH_RISK_KEYWORDS = [
    re.compile(r"\b(blanchiment|witwassen|money\s+laundering)\b", re.I),
    re.compile(r"\b(fraude|fraud|escroquerie)\b", re.I),
    re.compile(r"\b(faillite|faillissement|bankruptcy)\b", re.I),
    re.compile(r"\b(sanction|embargo|gel\s+des\s+avoirs)\b", re.I),
    re.compile(r"\b(terrorisme|terrorism|financement)\b", re.I),
]

_MEDIUM_RISK_KEYWORDS = [
    re.compile(r"\b(litige|dispute|contentieux)\b", re.I),
    re.compile(r"\b(impayé|onbetaald|unpaid)\b", re.I),
    re.compile(r"\b(mise\s+en\s+demeure|ingebrekestelling)\b", re.I),
]


class DueDiligenceAgent:
    """Automated legal due diligence analysis."""

    def __init__(self) -> None:
        self.ner = NERService()

    def analyze(
        self,
        case_id: str,
        tenant_id: str,
        events: list[dict] | None = None,
        documents_text: str = "",
    ) -> DueDiligenceReport:
        """Run full due diligence pipeline on a case.

        Args:
            case_id: Case ID
            tenant_id: Tenant UUID
            events: List of case events (each with 'content' or 'description')
            documents_text: Combined text from case documents

        Returns:
            DueDiligenceReport with risk assessment
        """
        report = DueDiligenceReport(
            case_id=case_id,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

        # 1. Gather text from events
        all_text = documents_text
        for event in events or []:
            text = (
                event.get("content")
                or event.get("description")
                or event.get("body")
                or ""
            )
            all_text += " " + text

        # 2. Extract entities via NER
        entities = self.ner.extract(all_text)
        persons = [e for e in entities if e.entity_type == "PERSON"]
        orgs = [e for e in entities if e.entity_type == "ORGANIZATION"]

        # 3-5. Check each entity
        checked_entities: list[EntityRisk] = []

        for person in persons:
            risk = self._check_entity(person.text, "PERSON", all_text)
            checked_entities.append(risk)

        for org in orgs:
            risk = self._check_entity(org.text, "ORGANIZATION", all_text)
            checked_entities.append(risk)

        # Deduplicate by name
        seen_names: set[str] = set()
        unique_entities: list[EntityRisk] = []
        for entity in checked_entities:
            name_lower = entity.entity_name.lower()
            if name_lower not in seen_names:
                seen_names.add(name_lower)
                unique_entities.append(entity)

        report.entities = unique_entities
        report.total_entities_checked = len(unique_entities)

        # 6. Aggregate risk
        report.sanctions_hits = sum(1 for e in unique_entities if e.sanctions_hit)
        report.risk_flags = self._extract_risk_flags(all_text)

        # Determine overall risk
        if report.sanctions_hits > 0:
            report.overall_risk = "CRITICAL"
        elif any(e.risk_level == "HIGH" for e in unique_entities):
            report.overall_risk = "HIGH"
        elif (
            any(e.risk_level == "MEDIUM" for e in unique_entities)
            or len(report.risk_flags) >= 2
        ):
            report.overall_risk = "MEDIUM"
        else:
            report.overall_risk = "LOW"

        # Generate recommendations
        report.recommendations = self._generate_recommendations(report)
        report.sources = ["NER extraction", "Sanctions check (stub)", "BCE/KBO (stub)"]

        return report

    def _check_entity(self, name: str, entity_type: str, context: str) -> EntityRisk:
        """Check a single entity against sanctions and BCE."""
        name_lower = name.lower().strip()
        flags: list[str] = []
        risk_score = 0.0
        sanctions_hit = False
        bce_status = ""

        # Check sanctions
        for sanctioned_name, info in _SANCTIONS_LIST.items():
            if sanctioned_name in name_lower or name_lower in sanctioned_name:
                sanctions_hit = True
                flags.append(f"Sanctions match: {info['list']} — {info['reason']}")
                risk_score = 1.0
                break

        # Check BCE/KBO for organizations
        if entity_type == "ORGANIZATION":
            for bce_name, info in _BCE_REGISTRY.items():
                if bce_name in name_lower or name_lower in bce_name:
                    bce_status = info["status"]
                    if info["status"] == "dissolved":
                        flags.append(f"BCE: dissolved company ({info['bce_number']})")
                        risk_score = max(risk_score, 0.6)
                    break

        # Check context for risk keywords
        for pattern in _HIGH_RISK_KEYWORDS:
            if pattern.search(context):
                risk_score = max(risk_score, 0.7)
                flags.append(f"High-risk keyword: {pattern.pattern}")
                break

        # Determine risk level
        if risk_score >= 0.9:
            risk_level = "CRITICAL"
        elif risk_score >= 0.6:
            risk_level = "HIGH"
        elif risk_score >= 0.3:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        return EntityRisk(
            entity_name=name,
            entity_type=entity_type,
            risk_level=risk_level,
            risk_score=risk_score,
            flags=flags,
            sanctions_hit=sanctions_hit,
            bce_status=bce_status,
            sources=["NER", "Sanctions DB", "BCE/KBO"],
        )

    def _extract_risk_flags(self, text: str) -> list[str]:
        """Extract risk flags from case text."""
        flags = []
        for pattern in _HIGH_RISK_KEYWORDS:
            matches = pattern.findall(text)
            if matches:
                flags.append(f"HIGH: {matches[0]}")

        for pattern in _MEDIUM_RISK_KEYWORDS:
            matches = pattern.findall(text)
            if matches:
                flags.append(f"MEDIUM: {matches[0]}")

        return flags

    def _generate_recommendations(self, report: DueDiligenceReport) -> list[str]:
        """Generate actionable recommendations based on findings."""
        recs = []

        if report.sanctions_hits > 0:
            recs.append(
                "URGENT: Sanctions match detected. Verify identity and consider declining representation."
            )
            recs.append(
                "Report to CTIF-CFI (Belgian Financial Intelligence Unit) if required."
            )

        high_risk = [e for e in report.entities if e.risk_level in ("HIGH", "CRITICAL")]
        if high_risk:
            recs.append(
                f"Enhanced due diligence required for {len(high_risk)} high-risk entities."
            )

        dissolved = [e for e in report.entities if e.bce_status == "dissolved"]
        if dissolved:
            recs.append(
                f"Verify legal standing: {len(dissolved)} entity(ies) marked as dissolved in BCE."
            )

        if not recs:
            recs.append(
                "Standard due diligence completed. No significant risks identified."
            )

        return recs
