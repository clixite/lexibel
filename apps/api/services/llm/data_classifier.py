"""Data sensitivity classifier for GDPR-compliant LLM routing.

Classifies text into sensitivity tiers using regex and heuristics.
Does NOT use an LLM for classification (the text itself may be sensitive).

Belgian-specific patterns:
- NISS (Numéro de Registre National): XX.XX.XX-XXX.XX
- BCE/TVA (Banque-Carrefour des Entreprises): 0XXX.XXX.XXX
- Belgian phone numbers: +32 ...
- Belgian IBAN: BE## #### #### ####
- Belgian postal addresses: rue/avenue + 4-digit postal code
- Jurisprudence references: C.C., Cass., C.E., Trib., etc.
"""

import re
from dataclasses import dataclass, field
from enum import Enum


class DataSensitivity(str, Enum):
    """Data sensitivity tiers for GDPR routing."""

    PUBLIC = "public"  # Jurisprudence, codes, doctrine
    SEMI_SENSITIVE = "semi"  # Anonymized analyses, templates
    SENSITIVE = "sensitive"  # Client data, case files, documents
    CRITICAL = "critical"  # Criminal data, medical, minors


@dataclass
class ClassificationContext:
    """Optional context to help classification."""

    source: str = ""  # "case_file", "jurisprudence_db", "template", "user_input"
    case_id: str | None = None
    has_client_data: bool = False


@dataclass
class DetectedEntity:
    """An entity detected in the text."""

    entity_type: str  # "niss", "bce", "person_name", "address", etc.
    value: str
    start: int
    end: int
    confidence: float = 1.0


@dataclass
class ClassificationResult:
    """Result of data classification."""

    sensitivity: DataSensitivity
    detected_entities: list[DetectedEntity] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    allowed_providers: list[str] = field(default_factory=list)


# ── Regex patterns for Belgian PII ──

# NISS: XX.XX.XX-XXX.XX (Belgian national registry number)
_NISS_PATTERN = re.compile(r"\b\d{2}\.\d{2}\.\d{2}[-–]\d{3}\.\d{2}\b")

# BCE/TVA: 0XXX.XXX.XXX or BE0XXX.XXX.XXX
_BCE_PATTERN = re.compile(r"\b(?:BE)?0\d{3}[.\s]\d{3}[.\s]\d{3}\b")

# Belgian phone: +32 or 0032 followed by digits
_PHONE_BE_PATTERN = re.compile(r"(?:\+32|0032)[\s.\-/]?\d[\s.\-/]?\d{2,3}[\s.\-/]?\d{2}[\s.\-/]?\d{2}")

# Belgian IBAN: BE## #### #### ####
_IBAN_BE_PATTERN = re.compile(r"\bBE\d{2}[\s]?\d{4}[\s]?\d{4}[\s]?\d{4}\b")

# Email addresses
_EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")

# Date of birth patterns (DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY)
_DOB_PATTERN = re.compile(
    r"(?:né(?:e)?|geboren|date\s+de\s+naissance|geboortedatum)"
    r"[:\s]*(\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4})",
    re.IGNORECASE,
)

# Belgian postal address: street type + name + number + postal code
_ADDRESS_KEYWORDS = re.compile(
    r"\b(?:rue|avenue|boulevard|place|chaussée|allée|impasse|"
    r"straat|laan|dreef|plein|steenweg|weg)\b",
    re.IGNORECASE,
)
_POSTAL_CODE_BE = re.compile(r"\b[1-9]\d{3}\b")

# Internal reference patterns
_INTERNAL_REF_PATTERN = re.compile(
    r"(?:dossier\s*n[°o]|réf(?:érence)?[\s.:]*|notre\s+réf|votre\s+réf|"
    r"N/Réf|V/Réf|dossiernr)",
    re.IGNORECASE,
)

# ── Jurisprudence patterns (PUBLIC data) ──

_JURISPRUDENCE_PATTERNS = re.compile(
    r"\b(?:"
    r"C\.C\.\s*(?:n[°o])?\s*\d+"  # Cour constitutionnelle
    r"|Cass\.\s*\d{1,2}\s*(?:janv|févr|mars|avr|mai|juin|juill|août|sept|oct|nov|déc)"
    r"|C\.E\.\s*(?:n[°o])?\s*\d+"  # Conseil d'État
    r"|Trib\.\s*(?:civ|corr|comm|trav)"  # Tribunaux
    r"|J\.P\.\s*\w+"  # Justice de paix
    r"|C\.T\.\s*\w+"  # Cour du travail
    r"|Bruxelles\s*\(\d+[eè]?\s*ch\.\)"  # Cour d'appel
    r"|Mons\s*\(\d+[eè]?\s*ch\.\)"
    r"|Liège\s*\(\d+[eè]?\s*ch\.\)"
    r"|Gand\s*\(\d+[eè]?\s*ch\.\)"
    r"|Anvers\s*\(\d+[eè]?\s*ch\.\)"
    r"|arrêt\s+n[°o]\s*\d+/\d+"
    r"|ECLI:BE:\w+:\d+:\w+"
    r")\b",
    re.IGNORECASE,
)

# Legal codes (PUBLIC data)
_LEGAL_CODE_PATTERNS = re.compile(
    r"\b(?:"
    r"(?:art(?:icle)?\.?\s*\d+)"
    r"(?:\s*(?:C\.\s*(?:civ|pén|jud|com|soc)\.?|"
    r"Code\s+(?:civil|pénal|judiciaire|des\s+sociétés|"
    r"de\s+droit\s+économique)|"
    r"C\.D\.E\.|Const\.|"
    r"Loi\s+du\s+\d{1,2}\s+\w+\s+\d{4}|"
    r"A\.R\.\s+du|"
    r"Burgerlijk\s+Wetboek|Strafwetboek|Gerechtelijk\s+Wetboek))"
    r")\b",
    re.IGNORECASE,
)

# ── Sensitive keyword patterns ──

_HEALTH_KEYWORDS = re.compile(
    r"\b(?:diagnostic|maladie|hospitalisation|médecin|handicap|"
    r"traitement\s+médical|incapacité\s+de\s+travail|"
    r"certificat\s+médical|mutuelle|invalidité|"
    r"diagnose|ziekte|ziekenhuis|arts|behandeling)\b",
    re.IGNORECASE,
)

_CRIMINAL_KEYWORDS = re.compile(
    r"\b(?:casier\s+judiciaire|condamnation|détention|"
    r"infraction|délit|crime|récidive|"
    r"tribunal\s+correctionnel|cour\s+d'assises|"
    r"peine\s+(?:de\s+prison|d'emprisonnement)|"
    r"prévenu|inculpé|mis\s+en\s+examen|"
    r"strafregister|veroordeling|misdrijf)\b",
    re.IGNORECASE,
)

_MINOR_KEYWORDS = re.compile(
    r"\b(?:mineur|enfant|pupille|tuteur|"
    r"tribunal\s+de\s+la\s+jeunesse|"
    r"protection\s+de\s+la\s+jeunesse|"
    r"aide\s+à\s+la\s+jeunesse|"
    r"minderjarige|kind|voogd|jeugdrechtbank)\b",
    re.IGNORECASE,
)

# Person name heuristic: capitalized words after legal context
_LEGAL_CONTEXT_NAME = re.compile(
    r"(?:(?:Maître|Me|M\.|Mme|Mr|Mlle)\s+)"
    r"([A-Z][a-zàâäéèêëïîôùûüç]+(?:\s+[A-Z][a-zàâäéèêëïîôùûüç]+){1,3})"
)

# Standalone proper names (2+ capitalized words not at sentence start)
_PROPER_NAME_PATTERN = re.compile(
    r"(?<=[a-z,;:]\s)"
    r"([A-Z][a-zàâäéèêëïîôùûüç]+\s+[A-Z][a-zàâäéèêëïîôùûüç]+)"
)


# ── Provider routing rules ──

_PROVIDER_RULES: dict[DataSensitivity, list[str]] = {
    DataSensitivity.CRITICAL: ["mistral", "gemini"],
    DataSensitivity.SENSITIVE: ["mistral", "gemini", "anthropic", "openai"],
    DataSensitivity.SEMI_SENSITIVE: ["mistral", "gemini", "anthropic", "openai", "deepseek"],
    DataSensitivity.PUBLIC: ["mistral", "gemini", "anthropic", "openai", "deepseek", "glm", "kimi"],
}


class DataClassifier:
    """Classifies text data sensitivity for GDPR-compliant LLM routing.

    Uses regex-based pattern detection — never sends data to an LLM for
    classification, since the data itself may be sensitive.
    """

    def classify(
        self, text: str, context: ClassificationContext | None = None
    ) -> ClassificationResult:
        """Analyze text and return sensitivity level with detected entities."""
        entities: list[DetectedEntity] = []
        reasons: list[str] = []

        # If context explicitly says it has client data, start at SENSITIVE
        if context and context.has_client_data:
            reasons.append("Context indicates client data present")

        # If context says it's from jurisprudence DB, start at PUBLIC
        if context and context.source == "jurisprudence_db":
            reasons.append("Source is published jurisprudence database")
            return ClassificationResult(
                sensitivity=DataSensitivity.PUBLIC,
                detected_entities=entities,
                reasons=reasons,
                allowed_providers=_PROVIDER_RULES[DataSensitivity.PUBLIC],
            )

        # ── Detect CRITICAL patterns ──

        # Health data
        for m in _HEALTH_KEYWORDS.finditer(text):
            entities.append(
                DetectedEntity("health_keyword", m.group(), m.start(), m.end())
            )
            reasons.append(f"Health-related keyword: '{m.group()}'")

        # Criminal data
        for m in _CRIMINAL_KEYWORDS.finditer(text):
            entities.append(
                DetectedEntity("criminal_keyword", m.group(), m.start(), m.end())
            )
            reasons.append(f"Criminal-related keyword: '{m.group()}'")

        # Minors
        for m in _MINOR_KEYWORDS.finditer(text):
            entities.append(
                DetectedEntity("minor_keyword", m.group(), m.start(), m.end())
            )
            reasons.append(f"Minor-related keyword: '{m.group()}'")

        # NISS (always CRITICAL — this is the Belgian equivalent of SSN)
        for m in _NISS_PATTERN.finditer(text):
            entities.append(
                DetectedEntity("niss", m.group(), m.start(), m.end())
            )
            reasons.append(f"Belgian NISS detected: {m.group()[:5]}***")

        # ── Detect SENSITIVE patterns ──

        # Person names (legal context)
        for m in _LEGAL_CONTEXT_NAME.finditer(text):
            entities.append(
                DetectedEntity("person_name", m.group(), m.start(), m.end(), confidence=0.9)
            )
            reasons.append(f"Person name in legal context: '{m.group()[:10]}...'")

        # Standalone proper names
        for m in _PROPER_NAME_PATTERN.finditer(text):
            name = m.group(1)
            # Filter out common legal terms that look like proper names
            if name.lower() not in {
                "code civil", "code pénal", "cour appel", "conseil état",
                "moniteur belge", "union européenne",
            }:
                entities.append(
                    DetectedEntity("person_name", name, m.start(1), m.end(1), confidence=0.6)
                )

        # Internal references
        for m in _INTERNAL_REF_PATTERN.finditer(text):
            entities.append(
                DetectedEntity("internal_ref", m.group(), m.start(), m.end())
            )
            reasons.append("Internal case/file reference detected")

        # Date of birth
        for m in _DOB_PATTERN.finditer(text):
            entities.append(
                DetectedEntity("date_of_birth", m.group(1), m.start(1), m.end(1))
            )
            reasons.append("Date of birth detected")

        # ── Detect SEMI-SENSITIVE patterns ──

        # BCE/TVA numbers
        for m in _BCE_PATTERN.finditer(text):
            entities.append(
                DetectedEntity("bce", m.group(), m.start(), m.end())
            )
            reasons.append(f"BCE/TVA number: {m.group()}")

        # Phone numbers
        for m in _PHONE_BE_PATTERN.finditer(text):
            entities.append(
                DetectedEntity("phone", m.group(), m.start(), m.end())
            )
            reasons.append("Belgian phone number detected")

        # IBAN
        for m in _IBAN_BE_PATTERN.finditer(text):
            entities.append(
                DetectedEntity("iban", m.group(), m.start(), m.end())
            )
            reasons.append("Belgian IBAN detected")

        # Email
        for m in _EMAIL_PATTERN.finditer(text):
            entities.append(
                DetectedEntity("email", m.group(), m.start(), m.end())
            )
            reasons.append("Email address detected")

        # Addresses
        addr_matches = list(_ADDRESS_KEYWORDS.finditer(text))
        postal_matches = list(_POSTAL_CODE_BE.finditer(text))
        if addr_matches and postal_matches:
            entities.append(
                DetectedEntity(
                    "address",
                    text[addr_matches[0].start() : postal_matches[0].end()],
                    addr_matches[0].start(),
                    postal_matches[0].end(),
                    confidence=0.7,
                )
            )
            reasons.append("Belgian postal address detected")

        # ── Detect PUBLIC patterns ──

        has_jurisprudence = bool(_JURISPRUDENCE_PATTERNS.search(text))
        has_legal_codes = bool(_LEGAL_CODE_PATTERNS.search(text))
        if has_jurisprudence:
            reasons.append("Published jurisprudence reference found")
        if has_legal_codes:
            reasons.append("Legal code reference found")

        # ── Determine final sensitivity ──

        # Text is "substantive" if it has meaningful content beyond whitespace
        # and generic instructions. Empty/trivial text → PUBLIC.
        stripped = text.strip()
        text_has_substance = len(stripped) > 20 and not stripped.isascii() or any(
            c.isalpha() for c in stripped
        )
        # Also consider purely legal reference text as public
        has_only_legal_refs = (has_jurisprudence or has_legal_codes) and not entities
        if has_only_legal_refs:
            text_has_substance = False

        sensitivity = self._determine_sensitivity(
            entities, reasons, context, text_has_substance
        )

        return ClassificationResult(
            sensitivity=sensitivity,
            detected_entities=entities,
            reasons=reasons,
            allowed_providers=_PROVIDER_RULES[sensitivity],
        )

    def _determine_sensitivity(
        self,
        entities: list[DetectedEntity],
        reasons: list[str],
        context: ClassificationContext | None,
        text_has_substance: bool = True,
    ) -> DataSensitivity:
        """Determine the highest sensitivity level from detected entities.

        GDPR precautionary principle: in case of doubt, classify at the
        HIGHER level. Non-trivial text without detected entities defaults
        to SENSITIVE, not PUBLIC.
        """
        entity_types = {e.entity_type for e in entities}

        # CRITICAL: NISS, health, criminal, minors
        critical_types = {"niss", "health_keyword", "criminal_keyword", "minor_keyword"}
        if entity_types & critical_types:
            return DataSensitivity.CRITICAL

        # SENSITIVE: person names, internal refs, DOB
        sensitive_types = {"person_name", "internal_ref", "date_of_birth"}
        if entity_types & sensitive_types:
            return DataSensitivity.SENSITIVE

        # Context says client data
        if context and context.has_client_data:
            return DataSensitivity.SENSITIVE

        # SEMI-SENSITIVE: BCE, phone, IBAN, email, address
        semi_types = {"bce", "phone", "iban", "email", "address"}
        if entity_types & semi_types:
            return DataSensitivity.SEMI_SENSITIVE

        # PUBLIC: only if text is empty/trivial or only contains legal references
        if not text_has_substance:
            return DataSensitivity.PUBLIC

        # Default: SENSITIVE (GDPR precautionary principle)
        # In case of doubt, classify at the HIGHER level.
        return DataSensitivity.SENSITIVE

    def get_allowed_providers(self, sensitivity: DataSensitivity) -> list[str]:
        """Return providers authorized for this sensitivity level."""
        return _PROVIDER_RULES[sensitivity]
