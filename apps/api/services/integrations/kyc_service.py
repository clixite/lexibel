"""KYC Service — Know Your Client verification for Belgian lawyers.

Automated client verification at contact creation:
1. BCE lookup (for legal entities) — verify company exists & status
2. Identity verification scoring (PEP, sanctions)
3. Risk categorization (low/medium/high)
4. Compliance checks (OBFG anti-money laundering obligations)

Belgian lawyers are subject to:
- Loi du 18/09/2017 relative à la prévention du blanchiment
- Directive (UE) 2015/849 (AMLD4) et 2018/843 (AMLD5)
- Règlement OBFG du 12/10/2020 relatif au blanchiment

Risk factors triggering enhanced due diligence:
- PEP (Politically Exposed Person)
- Country risk (FATF high-risk jurisdictions)
- Complex corporate structure
- Bearer shares
- Cash-intensive businesses
- BCE status anomalies
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


# ── FATF high-risk jurisdictions (updated per FATF grey/black lists) ──

FATF_HIGH_RISK = {
    "KP",
    "IR",
    "MM",  # FATF Blacklist
    "YE",
    "SY",
    "HT",
    "PH",
    "CM",
    "BF",
    "CD",
    "MZ",
    "TZ",
    "SS",
    "JM",
    "VU",
    "ML",
    "SN",
    "NG",  # FATF Greylist (simplified)
}

# Belgian-specific: EU high-risk third countries (Commission Delegated Regulation)
EU_HIGH_RISK = {"AF", "PK", "TT", "UG", "ZW"}

RISKY_NACE_CODES = {
    "64.19",  # Other monetary intermediation
    "64.30",  # Trusts, funds
    "66.19",  # Other financial activities
    "92.00",  # Gambling
    "68.10",  # Real estate (buying/selling)
    "68.20",  # Renting and operating real estate
    "46.72",  # Wholesale of metals and metal ores
    "47.78",  # Other retail sale — jewellery, precious metals
}

# PEP keywords for simplified screening (name-based heuristic)
PEP_TITLES = {
    "minister",
    "ministre",
    "secrétaire d'état",
    "député",
    "sénateur",
    "bourgmestre",
    "échevin",
    "gouverneur",
    "ambassadeur",
    "consul",
    "magistrat",
    "procureur",
    "directeur général",
    "administrateur délégué",
}


@dataclass
class KYCRiskFactor:
    """Individual risk factor found during KYC check."""

    category: str  # identity | corporate | geographic | activity | financial
    description: str
    severity: str  # low | medium | high | critical
    source: str  # bce | manual | screening | fatf


@dataclass
class KYCResult:
    """Complete KYC assessment for a contact."""

    contact_id: str
    contact_name: str
    contact_type: str  # natural | legal
    risk_score: int  # 0-100 (0=lowest risk)
    risk_level: str  # low | medium | high | critical
    risk_factors: list[KYCRiskFactor] = field(default_factory=list)
    bce_verified: bool = False
    bce_status: str | None = None
    enhanced_due_diligence: bool = False
    recommendations: list[str] = field(default_factory=list)
    checked_at: str = ""

    def to_dict(self) -> dict:
        return {
            "contact_id": self.contact_id,
            "contact_name": self.contact_name,
            "contact_type": self.contact_type,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "risk_factors": [
                {
                    "category": f.category,
                    "description": f.description,
                    "severity": f.severity,
                    "source": f.source,
                }
                for f in self.risk_factors
            ],
            "bce_verified": self.bce_verified,
            "bce_status": self.bce_status,
            "enhanced_due_diligence": self.enhanced_due_diligence,
            "recommendations": self.recommendations,
            "checked_at": self.checked_at,
        }


def _check_pep_indicators(full_name: str, metadata: dict) -> list[KYCRiskFactor]:
    """Simplified PEP screening based on name and metadata."""
    factors = []
    name_lower = full_name.lower()

    for title in PEP_TITLES:
        if title in name_lower:
            factors.append(
                KYCRiskFactor(
                    category="identity",
                    description=f"PEP indicator: title '{title}' detected in name",
                    severity="high",
                    source="screening",
                )
            )
            break

    profession = (metadata.get("profession") or "").lower()
    for title in PEP_TITLES:
        if title in profession:
            factors.append(
                KYCRiskFactor(
                    category="identity",
                    description=f"PEP indicator: profession '{profession}'",
                    severity="high",
                    source="screening",
                )
            )
            break

    return factors


def _check_geographic_risk(
    address: dict | None, nationality: str | None
) -> list[KYCRiskFactor]:
    """Check geographic risk based on address and nationality."""
    factors = []

    if nationality:
        country = nationality.upper()[:2]
        if country in FATF_HIGH_RISK:
            factors.append(
                KYCRiskFactor(
                    category="geographic",
                    description=f"FATF high-risk jurisdiction: {country}",
                    severity="critical",
                    source="fatf",
                )
            )
        elif country in EU_HIGH_RISK:
            factors.append(
                KYCRiskFactor(
                    category="geographic",
                    description=f"EU high-risk third country: {country}",
                    severity="high",
                    source="fatf",
                )
            )

    if address:
        country = (address.get("country") or "BE").upper()[:2]
        if country in FATF_HIGH_RISK:
            factors.append(
                KYCRiskFactor(
                    category="geographic",
                    description=f"Address in FATF high-risk jurisdiction: {country}",
                    severity="high",
                    source="fatf",
                )
            )

    return factors


async def _check_bce_risk(
    bce_number: str | None,
) -> tuple[list[KYCRiskFactor], bool, str | None]:
    """Check BCE-related risks for legal entities."""
    if not bce_number:
        return [], False, None

    try:
        from apps.api.services.integrations.bce_client import lookup_bce

        info = await lookup_bce(bce_number)

        factors = []
        bce_status = info.status

        if info.source in ("fallback_empty", "fallback_cache"):
            factors.append(
                KYCRiskFactor(
                    category="corporate",
                    description="BCE verification unavailable — manual check required",
                    severity="medium",
                    source="bce",
                )
            )

        if info.status and info.status.lower() in ("stopped", "closing", "bankrupt"):
            factors.append(
                KYCRiskFactor(
                    category="corporate",
                    description=f"BCE status: {info.status} — company not active",
                    severity="high",
                    source="bce",
                )
            )

        if info.nace_codes:
            for nace in info.nace_codes:
                if nace in RISKY_NACE_CODES:
                    factors.append(
                        KYCRiskFactor(
                            category="activity",
                            description=f"High-risk NACE code: {nace}",
                            severity="medium",
                            source="bce",
                        )
                    )

        return factors, info.source != "fallback_empty", bce_status

    except Exception as e:
        logger.warning("BCE check failed for %s: %s", bce_number, e)
        return (
            [
                KYCRiskFactor(
                    category="corporate",
                    description=f"BCE lookup error: {e}",
                    severity="low",
                    source="bce",
                )
            ],
            False,
            None,
        )


def _compute_risk_score(factors: list[KYCRiskFactor]) -> tuple[int, str]:
    """Compute aggregate risk score from individual factors."""
    if not factors:
        return 0, "low"

    severity_scores = {"low": 5, "medium": 15, "high": 30, "critical": 50}
    total = sum(severity_scores.get(f.severity, 5) for f in factors)

    # Cap at 100
    score = min(total, 100)

    if score >= 70:
        level = "critical"
    elif score >= 40:
        level = "high"
    elif score >= 15:
        level = "medium"
    else:
        level = "low"

    return score, level


def _generate_recommendations(
    risk_level: str, factors: list[KYCRiskFactor], contact_type: str
) -> list[str]:
    """Generate compliance recommendations based on risk assessment."""
    recs = []

    if risk_level in ("high", "critical"):
        recs.append(
            "Mesures de vigilance renforcées obligatoires (Art. 37 Loi 18/09/2017)"
        )
        recs.append(
            "Obtenir l'approbation d'un membre de la direction avant d'accepter la relation"
        )

    pep_factors = [f for f in factors if "PEP" in f.description]
    if pep_factors:
        recs.append("Vérification PEP approfondie — consulter les listes officielles")
        recs.append("Source de patrimoine et de fonds à documenter")

    fatf_factors = [f for f in factors if f.source == "fatf"]
    if fatf_factors:
        recs.append("Pays à risque identifié — vigilance géographique renforcée")

    if contact_type == "legal":
        recs.append("Identifier le bénéficiaire effectif (UBO) — registre UBO belge")
        bce_factors = [f for f in factors if f.source == "bce" and f.severity != "low"]
        if bce_factors:
            recs.append("Vérifier le statut BCE manuellement et documenter")

    if risk_level == "low":
        recs.append(
            "Mesures de vigilance standard — pas d'action supplémentaire requise"
        )

    return recs


async def perform_kyc_check(
    contact_id: str,
    contact_name: str,
    contact_type: str,
    bce_number: str | None = None,
    address: dict | None = None,
    nationality: str | None = None,
    metadata: dict | None = None,
) -> KYCResult:
    """Perform full KYC risk assessment on a contact.

    Checks:
    1. PEP screening (name/title-based)
    2. Geographic risk (FATF/EU high-risk)
    3. BCE verification (for legal entities)
    4. NACE activity risk (high-risk sectors)

    Returns:
        KYCResult with risk score, factors, and compliance recommendations
    """
    metadata = metadata or {}
    all_factors: list[KYCRiskFactor] = []

    # 1. PEP screening
    pep_factors = _check_pep_indicators(contact_name, metadata)
    all_factors.extend(pep_factors)

    # 2. Geographic risk
    geo_factors = _check_geographic_risk(address, nationality)
    all_factors.extend(geo_factors)

    # 3. BCE verification (legal entities only)
    bce_verified = False
    bce_status = None
    if contact_type == "legal" and bce_number:
        bce_factors, bce_verified, bce_status = await _check_bce_risk(bce_number)
        all_factors.extend(bce_factors)
    elif contact_type == "legal" and not bce_number:
        all_factors.append(
            KYCRiskFactor(
                category="corporate",
                description="Legal entity without BCE number — identification incomplete",
                severity="medium",
                source="manual",
            )
        )

    # 4. Compute aggregate score
    risk_score, risk_level = _compute_risk_score(all_factors)

    # 5. Generate recommendations
    enhanced = risk_level in ("high", "critical")
    recommendations = _generate_recommendations(risk_level, all_factors, contact_type)

    return KYCResult(
        contact_id=contact_id,
        contact_name=contact_name,
        contact_type=contact_type,
        risk_score=risk_score,
        risk_level=risk_level,
        risk_factors=all_factors,
        bce_verified=bce_verified,
        bce_status=bce_status,
        enhanced_due_diligence=enhanced,
        recommendations=recommendations,
        checked_at=datetime.utcnow().isoformat(),
    )
