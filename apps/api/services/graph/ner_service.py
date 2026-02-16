"""NER service — Named Entity Recognition for Belgian legal text.

Extracts entities using regex + pattern matching:
- PERSON: names (Jean Dupont, Maître X)
- ORGANIZATION: companies, institutions (SA, SPRL, ASBL)
- LOCATION: Belgian cities, addresses
- DATE: dates in various formats
- LEGAL_REFERENCE: articles de loi, jurisprudence citations
- MONETARY_AMOUNT: EUR amounts
- COURT: Belgian courts and tribunals
"""

import re
from dataclasses import dataclass, field


@dataclass
class Entity:
    """A named entity extracted from text."""

    text: str
    entity_type: str  # PERSON, ORGANIZATION, LOCATION, DATE, LEGAL_REFERENCE, MONETARY_AMOUNT, COURT
    start: int
    end: int
    confidence: float = 0.8
    normalized: str = ""  # Normalized form (e.g., court code)
    metadata: dict = field(default_factory=dict)


# ── Belgian Court patterns ──

COURT_PATTERNS = [
    (
        re.compile(r"\b(Tribunal\s+de\s+premi[èe]re\s+instance\s+de\s+\w+)\b", re.I),
        "COURT",
    ),
    (re.compile(r"\b(Rechtbank\s+van\s+eerste\s+aanleg\s+\w+)\b", re.I), "COURT"),
    (re.compile(r"\b(Cour\s+d.appel\s+de\s+\w+)\b", re.I), "COURT"),
    (re.compile(r"\b(Hof\s+van\s+[Bb]eroep\s+\w+)\b", re.I), "COURT"),
    (re.compile(r"\b(Cour\s+de\s+cassation)\b", re.I), "COURT"),
    (re.compile(r"\b(Hof\s+van\s+Cassatie)\b", re.I), "COURT"),
    (re.compile(r"\b(Cour\s+constitutionnelle)\b", re.I), "COURT"),
    (re.compile(r"\b(Grondwettelijk\s+Hof)\b", re.I), "COURT"),
    (re.compile(r"\b(Conseil\s+d.[EÉ]tat)\b", re.I), "COURT"),
    (re.compile(r"\b(Raad\s+van\s+State)\b", re.I), "COURT"),
    (re.compile(r"\b(Tribunal\s+de\s+commerce\s+de\s+\w+)\b", re.I), "COURT"),
    (re.compile(r"\b(Tribunal\s+du\s+travail\s+de\s+\w+)\b", re.I), "COURT"),
    (re.compile(r"\b(Justice\s+de\s+paix\s+de\s+\w+)\b", re.I), "COURT"),
    (re.compile(r"\b(Tribunal\s+de\s+l.entreprise\s+de\s+\w+)\b", re.I), "COURT"),
]

# ── Legal reference patterns ──

LEGAL_REF_PATTERNS = [
    # Article de loi: Art. 1382 C.C., Art. 707 C.J.
    (
        re.compile(
            r"\b(Art\.?\s*\d+(?:\s*(?:bis|ter|quater))?\s*(?:(?:du\s+)?C\.?\s*[A-Z]\.?(?:\s*[A-Z]\.?)?)?)\b",
            re.I,
        ),
        "LEGAL_REFERENCE",
    ),
    # Code references: Code civil, Code judiciaire
    (
        re.compile(
            r"\b(Code\s+(?:civil|judiciaire|pénal|de\s+commerce|des\s+sociétés))\b",
            re.I,
        ),
        "LEGAL_REFERENCE",
    ),
    # Jurisprudence: Cass., 15 mars 2026
    (re.compile(r"\b(Cass\.?,?\s*\d{1,2}\s+\w+\s+\d{4})\b", re.I), "LEGAL_REFERENCE"),
    # Belgian Monitor: M.B. 15/03/2026
    (
        re.compile(
            r"\b(M\.?\s*B\.?\s*(?:du\s+)?\d{1,2}[./]\d{1,2}[./]\d{2,4})\b", re.I
        ),
        "LEGAL_REFERENCE",
    ),
    # EU regulations: Règlement (UE) 2016/679
    (
        re.compile(r"\b(R[èe]glement\s*\((?:UE|CE)\)\s*\d{4}/\d+)\b", re.I),
        "LEGAL_REFERENCE",
    ),
    # Directive: Directive 2014/24/UE
    (re.compile(r"\b(Directive\s*\d{4}/\d+/(?:UE|CE))\b", re.I), "LEGAL_REFERENCE"),
    # Loi du DD/MM/YYYY
    (re.compile(r"\b([Ll]oi\s+du\s+\d{1,2}\s+\w+\s+\d{4})\b"), "LEGAL_REFERENCE"),
]

# ── Person patterns ──

PERSON_PATTERNS = [
    # Maître / Me
    (
        re.compile(r"\b(Ma[îi]tre\s+[A-ZÀ-Ü][a-zà-ÿ]+(?:\s+[A-ZÀ-Ü][a-zà-ÿ]+)?)\b"),
        "PERSON",
    ),
    (re.compile(r"\b(Me\.?\s+[A-ZÀ-Ü][a-zà-ÿ]+(?:\s+[A-ZÀ-Ü][a-zà-ÿ]+)?)\b"), "PERSON"),
    # Monsieur/Madame
    (
        re.compile(
            r"\b((?:Monsieur|Madame|M\.|Mme\.?)\s+[A-ZÀ-Ü][a-zà-ÿ]+(?:\s+[A-ZÀ-Ü][a-zà-ÿ]+)?)\b"
        ),
        "PERSON",
    ),
    # c/ pattern (parties in litigation): Dupont c/ Martin
    (re.compile(r"\b([A-ZÀ-Ü][a-zà-ÿ]+)\s+c/\s+([A-ZÀ-Ü][a-zà-ÿ]+)\b"), "PERSON_VS"),
]

# ── Organization patterns ──

ORG_PATTERNS = [
    # Belgian company forms
    (
        re.compile(
            r"\b([A-ZÀ-Ü][\w\s&.-]+(?:SA|S\.A\.|SPRL|S\.P\.R\.L\.|SRL|ASBL|A\.S\.B\.L\.|SCS|SNC|SCRL))\b"
        ),
        "ORGANIZATION",
    ),
    (
        re.compile(
            r"\b([A-ZÀ-Ü][\w\s&.-]+(?:NV|N\.V\.|BV|B\.V\.|BVBA|B\.V\.B\.A\.|VZW|V\.Z\.W\.))\b"
        ),
        "ORGANIZATION",
    ),
    # SPF / FOD (federal services)
    (re.compile(r"\b(SPF\s+\w+(?:\s+\w+)?)\b"), "ORGANIZATION"),
    (re.compile(r"\b(FOD\s+\w+(?:\s+\w+)?)\b"), "ORGANIZATION"),
    # Barreau / Ordre
    (
        re.compile(
            r"\b((?:Barreau|Ordre\s+des\s+avocats)\s+(?:de|du|d.)\s+\w+)\b", re.I
        ),
        "ORGANIZATION",
    ),
]

# ── Monetary patterns ──

MONETARY_PATTERNS = [
    (
        re.compile(
            r"\b(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?\s*(?:EUR|€|euros?))\b", re.I
        ),
        "MONETARY_AMOUNT",
    ),
    (
        re.compile(r"\b((?:EUR|€)\s*\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)\b", re.I),
        "MONETARY_AMOUNT",
    ),
]

# ── Date patterns ──

DATE_PATTERNS = [
    (re.compile(r"\b(\d{1,2}[./]\d{1,2}[./]\d{2,4})\b"), "DATE"),
    (re.compile(r"\b(\d{4}-\d{2}-\d{2})\b"), "DATE"),
    (
        re.compile(
            r"\b(\d{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+\d{4})\b",
            re.I,
        ),
        "DATE",
    ),
]

# ── Belgian location patterns ──

BELGIAN_CITIES = {
    "Bruxelles",
    "Brussel",
    "Anvers",
    "Antwerpen",
    "Liège",
    "Luik",
    "Gand",
    "Gent",
    "Charleroi",
    "Namur",
    "Namen",
    "Mons",
    "Bergen",
    "Bruges",
    "Brugge",
    "Leuven",
    "Louvain",
    "Hasselt",
    "Arlon",
    "Aarlen",
    "Tournai",
    "Doornik",
    "Wavre",
    "Waver",
    "Nivelles",
    "Nijvel",
    "Eupen",
    "Verviers",
    "Courtrai",
    "Kortrijk",
    "Mechelen",
    "Malines",
    "Louvain-la-Neuve",
}

LOCATION_PATTERN = re.compile(
    r"\b("
    + "|".join(re.escape(c) for c in sorted(BELGIAN_CITIES, key=len, reverse=True))
    + r")\b",
    re.I,
)


class NERService:
    """Named Entity Recognition for Belgian legal text."""

    def extract(self, text: str) -> list[Entity]:
        """Extract named entities from text.

        Args:
            text: Input text to analyze

        Returns:
            List of Entity objects sorted by position
        """
        if not text or not text.strip():
            return []

        entities: list[Entity] = []

        # 1. Courts (highest priority)
        for pattern, etype in COURT_PATTERNS:
            for match in pattern.finditer(text):
                entities.append(
                    Entity(
                        text=match.group(1),
                        entity_type=etype,
                        start=match.start(1),
                        end=match.end(1),
                        confidence=0.95,
                    )
                )

        # 2. Legal references
        for pattern, etype in LEGAL_REF_PATTERNS:
            for match in pattern.finditer(text):
                group = match.group(1) if match.lastindex else match.group(0)
                entities.append(
                    Entity(
                        text=group,
                        entity_type=etype,
                        start=match.start(),
                        end=match.end(),
                        confidence=0.9,
                    )
                )

        # 3. Persons
        for pattern, etype in PERSON_PATTERNS:
            for match in pattern.finditer(text):
                if etype == "PERSON_VS":
                    # Extract both parties
                    entities.append(
                        Entity(
                            text=match.group(1),
                            entity_type="PERSON",
                            start=match.start(1),
                            end=match.end(1),
                            confidence=0.85,
                            metadata={"role": "party"},
                        )
                    )
                    entities.append(
                        Entity(
                            text=match.group(2),
                            entity_type="PERSON",
                            start=match.start(2),
                            end=match.end(2),
                            confidence=0.85,
                            metadata={"role": "party"},
                        )
                    )
                else:
                    entities.append(
                        Entity(
                            text=match.group(1),
                            entity_type="PERSON",
                            start=match.start(1),
                            end=match.end(1),
                            confidence=0.85,
                        )
                    )

        # 4. Organizations
        for pattern, etype in ORG_PATTERNS:
            for match in pattern.finditer(text):
                entities.append(
                    Entity(
                        text=match.group(1).strip(),
                        entity_type=etype,
                        start=match.start(1),
                        end=match.end(1),
                        confidence=0.8,
                    )
                )

        # 5. Monetary amounts
        for pattern, etype in MONETARY_PATTERNS:
            for match in pattern.finditer(text):
                entities.append(
                    Entity(
                        text=match.group(1),
                        entity_type=etype,
                        start=match.start(1),
                        end=match.end(1),
                        confidence=0.95,
                    )
                )

        # 6. Dates
        for pattern, etype in DATE_PATTERNS:
            for match in pattern.finditer(text):
                entities.append(
                    Entity(
                        text=match.group(1),
                        entity_type=etype,
                        start=match.start(1),
                        end=match.end(1),
                        confidence=0.9,
                    )
                )

        # 7. Locations
        for match in LOCATION_PATTERN.finditer(text):
            entities.append(
                Entity(
                    text=match.group(1),
                    entity_type="LOCATION",
                    start=match.start(1),
                    end=match.end(1),
                    confidence=0.85,
                )
            )

        # Deduplicate overlapping entities (keep higher confidence)
        entities = self._deduplicate(entities)

        # Sort by position
        entities.sort(key=lambda e: e.start)
        return entities

    def _deduplicate(self, entities: list[Entity]) -> list[Entity]:
        """Remove overlapping entities, keeping higher confidence ones."""
        if not entities:
            return []

        # Sort by confidence desc, then by span length desc
        sorted_ents = sorted(
            entities, key=lambda e: (-e.confidence, -(e.end - e.start))
        )
        kept: list[Entity] = []
        used_spans: list[tuple[int, int]] = []

        for ent in sorted_ents:
            overlaps = False
            for start, end in used_spans:
                if ent.start < end and ent.end > start:
                    overlaps = True
                    break
            if not overlaps:
                kept.append(ent)
                used_spans.append((ent.start, ent.end))

        return kept
