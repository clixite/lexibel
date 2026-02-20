"""Document Intelligence — Smart document classification and analysis.

Classifies legal documents by type, extracts key metadata,
identifies important clauses, and detects potential issues.
Specialized for Belgian legal practice.
"""

import re
from dataclasses import dataclass, field
from datetime import date


# ── Data classes ──


@dataclass
class DocumentClassification:
    """Result of document classification."""

    document_type: str  # contract, judgment, correspondence, pleading, evidence, invoice, mandate, report
    sub_type: str  # e.g., lease_contract, employment_contract, purchase_agreement
    confidence: float
    language: str  # fr, nl, de, en
    metadata: dict = field(default_factory=dict)


@dataclass
class KeyClause:
    """An important clause extracted from a document."""

    clause_type: (
        str  # obligation, deadline, penalty, termination, jurisdiction, confidentiality
    )
    text: str
    page: int | None = None
    importance: str = "normal"  # critical, important, normal
    party: str | None = None  # Which party this clause affects


@dataclass
class DocumentAnalysisResult:
    """Complete document analysis result."""

    classification: DocumentClassification
    key_clauses: list[KeyClause] = field(default_factory=list)
    parties: list[str] = field(default_factory=list)
    dates: list[dict] = field(default_factory=list)  # [{date, context, type}]
    amounts: list[dict] = field(default_factory=list)  # [{amount, currency, context}]
    legal_references: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    summary_points: list[str] = field(default_factory=list)
    completeness_issues: list[str] = field(default_factory=list)


# ── Document type classification patterns ──

# Each entry: (compiled regex, weight) — higher weight = stronger indicator
CONTRACT_PATTERNS = [
    (re.compile(r"\bentre\s+les\s+soussignés\b", re.I), 0.30),
    (re.compile(r"\bil\s+est\s+convenu\b", re.I), 0.25),
    (re.compile(r"\bconditions\s+générales\b", re.I), 0.20),
    (re.compile(r"\bcontrat\s+de\b", re.I), 0.20),
    (re.compile(r"\bconvention\s+de\b", re.I), 0.20),
    (re.compile(r"\bles\s+parties\s+conviennent\b", re.I), 0.20),
    (re.compile(r"\bclause\s+résolutoire\b", re.I), 0.15),
    (re.compile(r"\ben\s+foi\s+de\s+quoi\b", re.I), 0.15),
    (re.compile(r"\bfait\s+en\s+\w+\s+exemplaires?\b", re.I), 0.15),
    (re.compile(r"\bdurée\s+du\s+contrat\b", re.I), 0.15),
    (re.compile(r"\brésiliation\b", re.I), 0.10),
    (re.compile(r"\bavenant\b", re.I), 0.10),
    (re.compile(r"\bstipulations?\b", re.I), 0.10),
    (re.compile(r"\bobligations?\s+(?:du|de\s+la|des)\b", re.I), 0.10),
]

JUDGMENT_PATTERNS = [
    (re.compile(r"\bau\s+nom\s+du\s+Roi\b", re.I), 0.35),
    (re.compile(r"\bin\s+naam\s+van\s+de\s+Koning\b", re.I), 0.35),
    (re.compile(r"\btribunal\s+de\b", re.I), 0.20),
    (re.compile(r"\bcour\s+d.appel\b", re.I), 0.25),
    (re.compile(r"\bcondamne\b", re.I), 0.20),
    (re.compile(r"\bordonne\b", re.I), 0.15),
    (re.compile(r"\bdéboute\b", re.I), 0.20),
    (re.compile(r"\bpar\s+ces\s+motifs\b", re.I), 0.25),
    (re.compile(r"\bvu\s+(?:la|le|les|l.)\b", re.I), 0.10),
    (re.compile(r"\battendu\s+que\b", re.I), 0.15),
    (re.compile(r"\bjugement\b", re.I), 0.15),
    (re.compile(r"\barrêt\b", re.I), 0.15),
    (re.compile(r"\bdéfendeur(?:esse)?\b", re.I), 0.15),
    (re.compile(r"\bdemandeur(?:esse)?\b", re.I), 0.15),
    (re.compile(r"\bpartie\s+civile\b", re.I), 0.10),
    (re.compile(r"\bministère\s+public\b", re.I), 0.10),
    (re.compile(r"\bdit\s+pour\s+droit\b", re.I), 0.25),
]

CORRESPONDENCE_PATTERNS = [
    (re.compile(r"\bMadame,?\s*Monsieur\b", re.I), 0.25),
    (re.compile(r"\bVeuillez\s+agréer\b", re.I), 0.30),
    (re.compile(r"\bcher\s+(?:Maître|Confrère)\b", re.I), 0.25),
    (re.compile(r"\bMaître\b", re.I), 0.10),
    (re.compile(r"\bcordialement\b", re.I), 0.15),
    (re.compile(r"\bsalutations\s+distinguées\b", re.I), 0.20),
    (re.compile(r"\bje\s+me\s+permets\s+de\b", re.I), 0.15),
    (re.compile(r"\bsuite\s+à\s+(?:votre|notre)\b", re.I), 0.15),
    (re.compile(r"\ben\s+réponse\s+à\b", re.I), 0.15),
    (re.compile(r"\bje\s+vous\s+prie\s+de\b", re.I), 0.10),
    (re.compile(r"\bpar\s+la\s+présente\b", re.I), 0.15),
    (re.compile(r"\bcopie\s+à\b", re.I), 0.10),
]

PLEADING_PATTERNS = [
    (re.compile(r"\bconclusions?\b", re.I), 0.20),
    (re.compile(r"\bmémoire\b", re.I), 0.20),
    (re.compile(r"\brequête\b", re.I), 0.20),
    (
        re.compile(
            r"\bconclusions?\s+(?:de\s+synthèse|additionnelles|après\s+réouverture)\b",
            re.I,
        ),
        0.30,
    ),
    (re.compile(r"\bplaise\s+au\s+tribunal\b", re.I), 0.35),
    (re.compile(r"\bpour\s+ces\s+motifs\b", re.I), 0.20),
    (re.compile(r"\bdire\s+pour\s+droit\b", re.I), 0.20),
    (re.compile(r"\ben\s+fait\b.*\ben\s+droit\b", re.I | re.S), 0.25),
    (re.compile(r"\bpartie\s+(?:concluante|adverse)\b", re.I), 0.20),
    (re.compile(r"\bsous\s+toutes\s+réserves\b", re.I), 0.15),
    (re.compile(r"\bcitation\s+directe\b", re.I), 0.20),
    (re.compile(r"\bassignation\b", re.I), 0.15),
]

EVIDENCE_PATTERNS = [
    (re.compile(r"\battestation\b", re.I), 0.25),
    (re.compile(r"\bcertificat\b", re.I), 0.20),
    (re.compile(r"\bprocès-verbal\b", re.I), 0.25),
    (re.compile(r"\bpièce\s+\d+\b", re.I), 0.15),
    (re.compile(r"\bje\s+soussigné\b", re.I), 0.25),
    (re.compile(r"\batteste\s+(?:sur|par|que)\b", re.I), 0.25),
    (re.compile(r"\bcertifie\s+(?:que|exact)\b", re.I), 0.20),
    (re.compile(r"\bconstat\b", re.I), 0.20),
    (re.compile(r"\bhuissier\s+de\s+justice\b", re.I), 0.20),
    (re.compile(r"\bexpertise\b", re.I), 0.15),
]

MANDATE_PATTERNS = [
    (re.compile(r"\bpouvoir\s+spécial\b", re.I), 0.30),
    (re.compile(r"\bprocuration\b", re.I), 0.30),
    (re.compile(r"\bmandat\b", re.I), 0.20),
    (re.compile(r"\bdonne\s+(?:pouvoir|mandat)\b", re.I), 0.25),
    (re.compile(r"\bmandataire\b", re.I), 0.15),
    (re.compile(r"\bmandant\b", re.I), 0.15),
    (re.compile(r"\bagir\s+en\s+(?:son|mon)\s+nom\b", re.I), 0.25),
    (re.compile(r"\breprésenter\b", re.I), 0.10),
]

INVOICE_PATTERNS = [
    (re.compile(r"\bfacture\b", re.I), 0.30),
    (re.compile(r"\bétat\s+de\s+frais\b", re.I), 0.30),
    (re.compile(r"\bhonoraires\b", re.I), 0.25),
    (re.compile(r"\bmontant\s+(?:total|HTVA|TVAC|dû)\b", re.I), 0.20),
    (re.compile(r"\bTVA\b"), 0.15),
    (re.compile(r"\bà\s+payer\b", re.I), 0.15),
    (re.compile(r"\béchéance\s+de\s+paiement\b", re.I), 0.20),
    (re.compile(r"\bnuméro\s+de\s+(?:compte|facture)\b", re.I), 0.15),
    (re.compile(r"\bBE\d{2}\s*\d{4}\s*\d{4}\s*\d{4}\b"), 0.15),  # Belgian IBAN
    (re.compile(r"\bprovision\b", re.I), 0.10),
]

REPORT_PATTERNS = [
    (re.compile(r"\brapport\s+(?:d.|de\s+)\b", re.I), 0.25),
    (re.compile(r"\bnote\s+(?:de\s+synthèse|interne)\b", re.I), 0.25),
    (re.compile(r"\banalyse\s+(?:de|du|des)\b", re.I), 0.15),
    (re.compile(r"\brecommandations?\b", re.I), 0.15),
    (re.compile(r"\bconclusion\b", re.I), 0.10),
    (re.compile(r"\brésumé\b", re.I), 0.10),
    (re.compile(r"\bintroduction\b", re.I), 0.10),
    (re.compile(r"\bsommaire\b", re.I), 0.15),
]

DOCUMENT_TYPE_PATTERNS = {
    "contract": CONTRACT_PATTERNS,
    "judgment": JUDGMENT_PATTERNS,
    "correspondence": CORRESPONDENCE_PATTERNS,
    "pleading": PLEADING_PATTERNS,
    "evidence": EVIDENCE_PATTERNS,
    "mandate": MANDATE_PATTERNS,
    "invoice": INVOICE_PATTERNS,
    "report": REPORT_PATTERNS,
}

# ── Contract sub-type patterns ──

CONTRACT_SUB_TYPES = {
    "lease_contract": [
        re.compile(r"\b(?:bail|contrat\s+de\s+(?:bail|location)|loyer)\b", re.I),
    ],
    "employment_contract": [
        re.compile(
            r"\b(?:contrat\s+de\s+travail|employeur|travailleur|salarié|rémunération\s+mensuelle)\b",
            re.I,
        ),
    ],
    "purchase_agreement": [
        re.compile(
            r"\b(?:vente|compromis\s+de\s+vente|acquéreur|vendeur|acte\s+de\s+vente)\b",
            re.I,
        ),
    ],
    "service_agreement": [
        re.compile(
            r"\b(?:contrat\s+de\s+(?:prestation|service)|prestations?\s+de\s+services?)\b",
            re.I,
        ),
    ],
    "partnership_agreement": [
        re.compile(
            r"\b(?:pacte\s+d.(?:associés|actionnaires)|convention\s+d.actionnaires)\b",
            re.I,
        ),
    ],
    "loan_agreement": [
        re.compile(
            r"\b(?:contrat\s+de\s+prêt|prêteur|emprunteur|remboursement)\b", re.I
        ),
    ],
    "settlement_agreement": [
        re.compile(
            r"\b(?:transaction|accord\s+amiable|conciliation|règlement\s+amiable)\b",
            re.I,
        ),
    ],
    "nda": [
        re.compile(
            r"\b(?:confidentialité|non-divulgation|NDA|secret\s+professionnel)\b", re.I
        ),
    ],
}

JUDGMENT_SUB_TYPES = {
    "civil_judgment": [
        re.compile(
            r"\b(?:tribunal\s+(?:civil|de\s+première\s+instance)|chambre\s+civile)\b",
            re.I,
        ),
    ],
    "commercial_judgment": [
        re.compile(r"\b(?:tribunal\s+(?:de\s+commerce|de\s+l.entreprise))\b", re.I),
    ],
    "labor_judgment": [
        re.compile(r"\b(?:tribunal\s+du\s+travail|chambre\s+sociale)\b", re.I),
    ],
    "criminal_judgment": [
        re.compile(
            r"\b(?:tribunal\s+(?:correctionnel|de\s+police)|chambre\s+pénale|prévenu)\b",
            re.I,
        ),
    ],
    "appeal_judgment": [
        re.compile(r"\b(?:cour\s+d.appel|arrêt)\b", re.I),
    ],
    "cassation_judgment": [
        re.compile(r"\b(?:cour\s+de\s+cassation|pourvoi)\b", re.I),
    ],
}

# ── Language detection patterns ──

FRENCH_INDICATORS = [
    re.compile(
        r"\b(?:le|la|les|du|des|un|une|de|en|est|sont|dans|pour|avec|sur|par|que|qui)\b",
        re.I,
    ),
    re.compile(
        r"\b(?:monsieur|madame|tribunal|jugement|contrat|entre|article)\b", re.I
    ),
]

DUTCH_INDICATORS = [
    re.compile(
        r"\b(?:de|het|een|van|in|op|met|voor|aan|bij|uit|worden|zijn|hebben)\b", re.I
    ),
    re.compile(
        r"\b(?:mijnheer|mevrouw|rechtbank|vonnis|overeenkomst|tussen|artikel)\b", re.I
    ),
]

GERMAN_INDICATORS = [
    re.compile(
        r"\b(?:der|die|das|ein|eine|und|ist|von|mit|für|auf|den|dem|sich)\b", re.I
    ),
    re.compile(r"\b(?:Vertrag|Gericht|Urteil|Herr|Frau|Artikel)\b", re.I),
]

# ── Clause extraction patterns ──

OBLIGATION_PATTERNS = [
    (
        re.compile(r"(?:^|[.;])\s*([^.;]*\b(?:doit|doivent)\s+[^.;]+)", re.I | re.M),
        "obligation",
    ),
    (
        re.compile(
            r"(?:^|[.;])\s*([^.;]*\b(?:s.engage\s+à|s.engagent\s+à)\s+[^.;]+)",
            re.I | re.M,
        ),
        "commitment",
    ),
    (
        re.compile(
            r"(?:^|[.;])\s*([^.;]*\b(?:est\s+tenu(?:e)?\s+de|sont\s+tenus?\s+de)\s+[^.;]+)",
            re.I | re.M,
        ),
        "obligation",
    ),
    (
        re.compile(r"(?:^|[.;])\s*([^.;]*\b(?:obligation\s+de)\s+[^.;]+)", re.I | re.M),
        "obligation",
    ),
    (
        re.compile(r"(?:^|[.;])\s*([^.;]*\b(?:devra|devront)\s+[^.;]+)", re.I | re.M),
        "future_obligation",
    ),
    (
        re.compile(
            r"(?:^|[.;])\s*([^.;]*\b(?:il\s+incombe\s+à)\s+[^.;]+)", re.I | re.M
        ),
        "obligation",
    ),
    (
        re.compile(
            r"(?:^|[.;])\s*([^.;]*\b(?:il\s+appartient\s+à)\s+[^.;]+)", re.I | re.M
        ),
        "obligation",
    ),
]

DEADLINE_CLAUSE_PATTERNS = [
    (
        re.compile(
            r"(?:^|[.;])\s*([^.;]*\b(?:dans\s+(?:un\s+)?délai\s+de)\s+[^.;]+)",
            re.I | re.M,
        ),
        "deadline",
    ),
    (
        re.compile(
            r"(?:^|[.;])\s*([^.;]*\b(?:au\s+plus\s+tard\s+le?)\s+[^.;]+)", re.I | re.M
        ),
        "deadline",
    ),
    (
        re.compile(r"(?:^|[.;])\s*([^.;]*\b(?:avant\s+le)\s+[^.;]+)", re.I | re.M),
        "deadline",
    ),
    (
        re.compile(r"(?:^|[.;])\s*([^.;]*\b(?:endéans)\s+[^.;]+)", re.I | re.M),
        "deadline",
    ),
]

PENALTY_CLAUSE_PATTERNS = [
    (
        re.compile(r"(?:^|[.;])\s*([^.;]*\b(?:clause\s+pénale)\s+[^.;]+)", re.I | re.M),
        "penalty",
    ),
    (
        re.compile(r"(?:^|[.;])\s*([^.;]*\b(?:pénalité\s+de)\s+[^.;]+)", re.I | re.M),
        "penalty",
    ),
    (
        re.compile(
            r"(?:^|[.;])\s*([^.;]*\b(?:dommages?\s+et\s+intérêts?\s+(?:forfaitaires?|conventionnels?))\s+[^.;]+)",
            re.I | re.M,
        ),
        "penalty",
    ),
    (
        re.compile(
            r"(?:^|[.;])\s*([^.;]*\b(?:indemnité\s+(?:forfaitaire|de\s+rupture))\s+[^.;]+)",
            re.I | re.M,
        ),
        "penalty",
    ),
    (
        re.compile(r"(?:^|[.;])\s*([^.;]*\b(?:astreinte)\s+[^.;]+)", re.I | re.M),
        "penalty",
    ),
]

TERMINATION_CLAUSE_PATTERNS = [
    (
        re.compile(r"(?:^|[.;])\s*([^.;]*\b(?:résiliation)\s+[^.;]+)", re.I | re.M),
        "termination",
    ),
    (
        re.compile(r"(?:^|[.;])\s*([^.;]*\b(?:résolution)\s+[^.;]+)", re.I | re.M),
        "termination",
    ),
    (
        re.compile(
            r"(?:^|[.;])\s*([^.;]*\b(?:fin\s+du\s+contrat)\s+[^.;]+)", re.I | re.M
        ),
        "termination",
    ),
    (
        re.compile(r"(?:^|[.;])\s*([^.;]*\b(?:préavis\s+de)\s+[^.;]+)", re.I | re.M),
        "termination",
    ),
    (
        re.compile(r"(?:^|[.;])\s*([^.;]*\b(?:dénonciation)\s+[^.;]+)", re.I | re.M),
        "termination",
    ),
]

JURISDICTION_CLAUSE_PATTERNS = [
    (
        re.compile(
            r"(?:^|[.;])\s*([^.;]*\b(?:compétence\s+(?:exclusive|territoriale))\s+[^.;]+)",
            re.I | re.M,
        ),
        "jurisdiction",
    ),
    (
        re.compile(
            r"(?:^|[.;])\s*([^.;]*\b(?:tribunaux?\s+(?:de|du|compétents?))\s+[^.;]+)",
            re.I | re.M,
        ),
        "jurisdiction",
    ),
    (
        re.compile(
            r"(?:^|[.;])\s*([^.;]*\b(?:attribution\s+(?:de\s+)?juridiction)\s+[^.;]+)",
            re.I | re.M,
        ),
        "jurisdiction",
    ),
    (
        re.compile(
            r"(?:^|[.;])\s*([^.;]*\b(?:clause\s+(?:attributive|d.arbitrage))\s+[^.;]+)",
            re.I | re.M,
        ),
        "jurisdiction",
    ),
    (
        re.compile(
            r"(?:^|[.;])\s*([^.;]*\b(?:droit\s+(?:belge|applicable))\s+[^.;]+)",
            re.I | re.M,
        ),
        "jurisdiction",
    ),
]

CONFIDENTIALITY_CLAUSE_PATTERNS = [
    (
        re.compile(r"(?:^|[.;])\s*([^.;]*\b(?:confidentialité)\s+[^.;]+)", re.I | re.M),
        "confidentiality",
    ),
    (
        re.compile(
            r"(?:^|[.;])\s*([^.;]*\b(?:secret\s+professionnel)\s+[^.;]+)", re.I | re.M
        ),
        "confidentiality",
    ),
    (
        re.compile(r"(?:^|[.;])\s*([^.;]*\b(?:non-divulgation)\s+[^.;]+)", re.I | re.M),
        "confidentiality",
    ),
    (
        re.compile(
            r"(?:^|[.;])\s*([^.;]*\b(?:informations?\s+confidentielles?)\s+[^.;]+)",
            re.I | re.M,
        ),
        "confidentiality",
    ),
]

# ── Entity extraction patterns ──

PARTY_PATTERNS = [
    # "entre X et Y" pattern
    re.compile(
        r"\bentre\s+(?:d.une\s+part,?\s+)?(.+?)\s+et\s+(?:d.autre\s+part,?\s+)?(.+?)(?:\.|,\s*il)",
        re.I,
    ),
    # "Monsieur/Madame X" pattern
    re.compile(
        r"\b((?:Monsieur|Madame|M\.|Mme\.?|Maître|Me\.?)\s+[A-ZÀ-Ü][a-zà-ÿ]+(?:\s+[A-ZÀ-Ü][a-zà-ÿ]+)*)\b"
    ),
    # Company names (SA, SPRL, SRL, etc.)
    re.compile(
        r"\b([A-ZÀ-Ü][\w\s&.-]+(?:SA|S\.A\.|SPRL|S\.P\.R\.L\.|SRL|ASBL|NV|BV|BVBA|VZW))\b"
    ),
    # "ci-après dénommé(e)" pattern
    re.compile(r"(.+?),?\s+ci-après\s+(?:dénommé|nommé|appelé)", re.I),
]

DATE_EXTRACTION_PATTERNS = [
    # DD/MM/YYYY or DD.MM.YYYY
    (re.compile(r"\b(\d{1,2})[./](\d{1,2})[./](\d{4})\b"), "dmy"),
    # YYYY-MM-DD (ISO)
    (re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"), "ymd"),
    # "15 mars 2026"
    (
        re.compile(
            r"\b(\d{1,2})\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+(\d{4})\b",
            re.I,
        ),
        "fr_long",
    ),
]

MONTH_FR = {
    "janvier": 1,
    "février": 2,
    "mars": 3,
    "avril": 4,
    "mai": 5,
    "juin": 6,
    "juillet": 7,
    "août": 8,
    "septembre": 9,
    "octobre": 10,
    "novembre": 11,
    "décembre": 12,
}

AMOUNT_PATTERNS = [
    re.compile(r"\b(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)\s*(?:EUR|€|euros?)\b", re.I),
    re.compile(r"(?:EUR|€)\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)\b", re.I),
]

LEGAL_REF_PATTERNS = [
    re.compile(
        r"\b(Art\.?\s*\d+(?:\s*(?:bis|ter|quater))?\s*(?:(?:du\s+)?C\.?\s*[A-Z]\.?(?:\s*[A-Z]\.?)?)?)\b",
        re.I,
    ),
    re.compile(
        r"\b(Code\s+(?:civil|judiciaire|pénal|de\s+commerce|des\s+sociétés))\b", re.I
    ),
    re.compile(r"\b(Loi\s+du\s+\d{1,2}\s+\w+\s+\d{4})\b", re.I),
    re.compile(r"\b(Règlement\s*\((?:UE|CE)\)\s*\d{4}/\d+)\b", re.I),
    re.compile(r"\b(Directive\s*\d{4}/\d+/(?:UE|CE))\b", re.I),
    re.compile(r"\b(M\.?\s*B\.?\s*(?:du\s+)?\d{1,2}[./]\d{1,2}[./]\d{2,4})\b", re.I),
]

# ── Risk detection patterns ──

AUTOMATIC_RENEWAL_PATTERN = re.compile(
    r"\b(?:renouvellement\s+(?:automatique|tacite)|tacite\s+reconduction)\b", re.I
)
EXCLUSIVE_JURISDICTION_PATTERN = re.compile(
    r"\b(?:compétence\s+exclusive|seul(?:s)?\s+compétent(?:s)?)\b", re.I
)
NON_COMPETE_PATTERN = re.compile(
    r"\b(?:clause\s+de\s+non-concurrence|non-concurrence)\b", re.I
)
ONE_SIDED_TERMINATION_PATTERN = re.compile(
    r"\b(?:résili(?:er|ation)\s+(?:unilatérale(?:ment)?|de\s+plein\s+droit|sans\s+(?:préavis|indemnité)))\b",
    re.I,
)
LIABILITY_LIMITATION_PATTERN = re.compile(
    r"\b(?:limitation\s+de\s+responsabilité|exonération\s+de\s+responsabilité|clause\s+limitative)\b",
    re.I,
)
INDEXATION_PATTERN = re.compile(
    r"\b(?:indexation|index\s+(?:santé|des\s+prix))\b", re.I
)
SOLIDARITE_PATTERN = re.compile(r"\b(?:solidairement|solidarité|in\s+solidum)\b", re.I)


# ── Completeness check requirements per document type ──

COMPLETENESS_REQUIREMENTS: dict[str, list[tuple[re.Pattern, str]]] = {
    "contract": [
        (re.compile(r"\bsignat(?:ure|é)\b", re.I), "Mention de signature absente"),
        (re.compile(r"\b(?:date|fait\s+(?:à|le))\b", re.I), "Date du contrat absente"),
        (
            re.compile(r"\b(?:entre|parties?)\b", re.I),
            "Identification des parties absente",
        ),
        (re.compile(r"\b(?:objet|portée)\b", re.I), "Objet du contrat absent"),
        (
            re.compile(r"\b(?:durée|terme|période)\b", re.I),
            "Durée du contrat non précisée",
        ),
        (
            re.compile(r"\b(?:prix|montant|rémunération|honoraires?)\b", re.I),
            "Conditions financières absentes",
        ),
        (
            re.compile(r"\b(?:résiliation|fin\s+du\s+contrat)\b", re.I),
            "Clause de résiliation absente",
        ),
        (
            re.compile(
                r"\b(?:tribunal|compétence|juridiction|droit\s+(?:belge|applicable))\b",
                re.I,
            ),
            "Clause de juridiction absente",
        ),
    ],
    "judgment": [
        (re.compile(r"\b(?:date|prononcé)\b", re.I), "Date du jugement absente"),
        (
            re.compile(r"\b(?:tribunal|cour|juridiction)\b", re.I),
            "Juridiction non identifiée",
        ),
        (
            re.compile(r"\b(?:par\s+ces\s+motifs|dispositif)\b", re.I),
            "Dispositif absent",
        ),
    ],
    "mandate": [
        (
            re.compile(r"\b(?:mandant|donneur\s+d.ordre)\b", re.I),
            "Mandant non identifié",
        ),
        (re.compile(r"\b(?:mandataire)\b", re.I), "Mandataire non identifié"),
        (
            re.compile(r"\b(?:objet|étendue|pouvoir)\b", re.I),
            "Étendue du mandat non précisée",
        ),
        (
            re.compile(r"\b(?:date|durée|validité)\b", re.I),
            "Durée/validité du mandat non précisée",
        ),
    ],
    "invoice": [
        (
            re.compile(r"\b(?:numéro|n°|no\.?)\s*(?:de\s+)?facture\b", re.I),
            "Numéro de facture absent",
        ),
        (re.compile(r"\b(?:date)\b", re.I), "Date de facture absente"),
        (re.compile(r"\b(?:TVA|BTW)\b", re.I), "Mention TVA absente"),
        (re.compile(r"\b(?:total|montant)\b", re.I), "Montant total absent"),
    ],
}


class DocumentIntelligence:
    """Intelligent classification and analysis of Belgian legal documents."""

    def classify(self, text: str, filename: str = "") -> DocumentClassification:
        """Classify a document by type, sub-type, and language.

        Uses keyword/pattern scoring to identify the most likely document type.
        Considers both text content and filename hints.

        Args:
            text: The document text content
            filename: Optional filename for additional classification hints

        Returns:
            DocumentClassification with type, sub-type, confidence, and language
        """
        if not text or not text.strip():
            return DocumentClassification(
                document_type="unknown",
                sub_type="unknown",
                confidence=0.0,
                language="fr",
            )

        # Score each document type
        scores: dict[str, float] = {}
        for doc_type, patterns in DOCUMENT_TYPE_PATTERNS.items():
            score = 0.0
            for pattern, weight in patterns:
                matches = pattern.findall(text)
                if matches:
                    # Diminishing returns for multiple matches
                    score += weight * min(len(matches), 3)
            scores[doc_type] = score

        # Filename hints
        filename_lower = filename.lower() if filename else ""
        filename_hints = {
            "contract": ["contrat", "convention", "bail", "accord"],
            "judgment": ["jugement", "arrêt", "ordonnance", "vonnis"],
            "correspondence": ["lettre", "courrier", "mail", "brief"],
            "pleading": ["conclusions", "requête", "mémoire", "assignation"],
            "evidence": ["attestation", "certificat", "pv", "constat"],
            "mandate": ["procuration", "mandat", "pouvoir"],
            "invoice": ["facture", "honoraires", "état", "frais"],
            "report": ["rapport", "note", "analyse"],
        }
        for doc_type, hints in filename_hints.items():
            for hint in hints:
                if hint in filename_lower:
                    scores[doc_type] = scores.get(doc_type, 0.0) + 0.20
                    break

        # Find best match
        best_type = max(scores, key=lambda k: scores[k])
        best_score = scores[best_type]

        # Calculate confidence
        total_score = sum(scores.values())
        if total_score > 0 and best_score > 0:
            confidence = min(best_score / total_score, 1.0)
            # Boost confidence if the score is strong in absolute terms
            if best_score > 0.5:
                confidence = min(confidence + 0.1, 1.0)
        else:
            best_type = "unknown"
            confidence = 0.0

        # Detect sub-type
        sub_type = self._detect_sub_type(text, best_type)

        # Detect language
        language = self._detect_language(text)

        return DocumentClassification(
            document_type=best_type,
            sub_type=sub_type,
            confidence=round(confidence, 2),
            language=language,
            metadata={
                "scores": {k: round(v, 3) for k, v in scores.items() if v > 0},
                "filename": filename,
            },
        )

    def analyze(self, text: str, filename: str = "") -> DocumentAnalysisResult:
        """Perform a full analysis of a legal document.

        Classifies the document, extracts entities, clauses, dates, amounts,
        legal references, and identifies risks and completeness issues.

        Args:
            text: The document text content
            filename: Optional filename for classification hints

        Returns:
            DocumentAnalysisResult with all extracted information
        """
        # Step 1: Classify
        classification = self.classify(text, filename)

        # Step 2: Extract key clauses
        key_clauses = self._extract_all_clauses(text, classification.document_type)

        # Step 3: Extract parties
        parties = self._extract_parties(text)

        # Step 4: Extract dates
        dates = self._extract_dates(text)

        # Step 5: Extract amounts
        amounts = self._extract_amounts(text)

        # Step 6: Extract legal references
        legal_references = self._extract_legal_references(text)

        # Step 7: Detect risks
        risks = self.detect_risks(text, classification.document_type)

        # Step 8: Generate summary points
        summary_points = self._generate_summary(
            classification, parties, dates, amounts, key_clauses, risks
        )

        # Step 9: Check completeness
        completeness_issues = self._check_completeness(
            text, classification.document_type
        )

        return DocumentAnalysisResult(
            classification=classification,
            key_clauses=key_clauses,
            parties=parties,
            dates=dates,
            amounts=amounts,
            legal_references=legal_references,
            risks=risks,
            summary_points=summary_points,
            completeness_issues=completeness_issues,
        )

    def extract_obligations(self, text: str) -> list[KeyClause]:
        """Extract obligation clauses from the document.

        Finds clauses where parties are obligated to perform actions,
        and flags any deadlines attached to those obligations.

        Args:
            text: The document text content

        Returns:
            List of KeyClause objects for each obligation found
        """
        if not text or not text.strip():
            return []

        obligations: list[KeyClause] = []
        seen_texts: set[str] = set()

        for pattern, sub_type in OBLIGATION_PATTERNS:
            for match in pattern.finditer(text):
                clause_text = match.group(1).strip()
                # Normalize whitespace
                clause_text = re.sub(r"\s+", " ", clause_text)

                # Skip if too short or duplicate
                if len(clause_text) < 15:
                    continue
                # Truncate very long clauses
                if len(clause_text) > 500:
                    clause_text = clause_text[:500] + "..."

                normalized = clause_text.lower().strip()
                if normalized in seen_texts:
                    continue
                seen_texts.add(normalized)

                # Try to identify which party
                party = self._identify_party_in_clause(clause_text)

                # Determine importance based on deadline presence
                has_deadline = bool(
                    re.search(
                        r"\b(?:dans\s+(?:un\s+)?délai|au\s+plus\s+tard|avant\s+le|endéans|jours?|mois)\b",
                        clause_text,
                        re.I,
                    )
                )
                importance = "important" if has_deadline else "normal"

                # Check if obligation has a penalty attached
                context_end = min(len(text), match.end() + 200)
                following_text = text[match.end() : context_end]
                if re.search(
                    r"\b(?:pénalité|clause\s+pénale|astreinte|dommages)\b",
                    following_text,
                    re.I,
                ):
                    importance = "critical"

                obligations.append(
                    KeyClause(
                        clause_type=f"obligation_{sub_type}",
                        text=clause_text,
                        importance=importance,
                        party=party,
                    )
                )

        return obligations

    def detect_risks(self, text: str, document_type: str) -> list[str]:
        """Detect potential risks in the document.

        Identifies concerning clauses and missing elements based on
        the document type. Focused on Belgian legal practice risks.

        Args:
            text: The document text content
            document_type: The classified document type

        Returns:
            List of risk description strings
        """
        if not text or not text.strip():
            return []

        risks: list[str] = []

        # ── General risks (all document types) ──

        # Penalty clauses
        for pattern, _ in PENALTY_CLAUSE_PATTERNS:
            if pattern.search(text):
                risks.append(
                    "Clause pénale détectée — vérifier la proportionnalité "
                    "(Art. 5.88 nouveau C.C.)"
                )
                break

        # Automatic renewal
        if AUTOMATIC_RENEWAL_PATTERN.search(text):
            risks.append(
                "Renouvellement tacite/automatique — vérifier le délai de "
                "dénonciation et les conditions de sortie"
            )

        # Exclusive jurisdiction
        if EXCLUSIVE_JURISDICTION_PATTERN.search(text):
            risks.append(
                "Clause de compétence exclusive — vérifier si conforme aux "
                "règles de compétence territoriale belges"
            )

        # Liability limitation
        if LIABILITY_LIMITATION_PATTERN.search(text):
            risks.append(
                "Clause limitative de responsabilité — vérifier la validité "
                "et la conformité au droit belge"
            )

        # Non-compete clause
        if NON_COMPETE_PATTERN.search(text):
            risks.append(
                "Clause de non-concurrence — vérifier les limites "
                "géographiques, temporelles et matérielles"
            )

        # One-sided termination
        if ONE_SIDED_TERMINATION_PATTERN.search(text):
            risks.append(
                "Résiliation unilatérale ou sans préavis détectée — "
                "vérifier l'équilibre contractuel"
            )

        # Joint liability
        if SOLIDARITE_PATTERN.search(text):
            risks.append(
                "Clause de solidarité détectée — évaluer les implications "
                "pour le client"
            )

        # ── Contract-specific risks ──
        if document_type == "contract":
            risks.extend(self._detect_contract_risks(text))

        # ── Short deadlines ──
        short_deadline = re.search(
            r"\b(?:dans\s+(?:un\s+)?délai\s+de\s+|endéans\s+)(\d+)\s+jours?\b",
            text,
            re.I,
        )
        if short_deadline:
            days = int(short_deadline.group(1))
            if days < 8:
                risks.append(
                    f"Délai très court détecté ({days} jours) — "
                    "vérifier la faisabilité et les conséquences du non-respect"
                )

        # ── Ambiguous terms ──
        ambiguous = re.findall(
            r"\b(?:raisonnable(?:ment)?|en\s+temps\s+utile|dans\s+un\s+délai\s+raisonnable|"
            r"éventuellement|si\s+nécessaire|le\s+cas\s+échéant)\b",
            text,
            re.I,
        )
        if len(ambiguous) > 2:
            risks.append(
                f"Termes ambigus multiples détectés ({len(ambiguous)} occurrences) — "
                "risque d'interprétation divergente"
            )

        return risks

    # ── Private helper methods ──

    def _detect_sub_type(self, text: str, document_type: str) -> str:
        """Detect the sub-type of a classified document."""
        sub_type_maps = {
            "contract": CONTRACT_SUB_TYPES,
            "judgment": JUDGMENT_SUB_TYPES,
        }

        sub_type_patterns = sub_type_maps.get(document_type, {})
        best_sub_type = "general"
        best_count = 0

        for sub_type, patterns in sub_type_patterns.items():
            count = 0
            for pattern in patterns:
                matches = pattern.findall(text)
                count += len(matches)
            if count > best_count:
                best_count = count
                best_sub_type = sub_type

        return best_sub_type

    def _detect_language(self, text: str) -> str:
        """Detect the primary language of the text (fr, nl, de, en)."""
        # Sample first 2000 chars for speed
        sample = text[:2000].lower()

        scores = {"fr": 0, "nl": 0, "de": 0, "en": 0}

        for pattern in FRENCH_INDICATORS:
            scores["fr"] += len(pattern.findall(sample))

        for pattern in DUTCH_INDICATORS:
            scores["nl"] += len(pattern.findall(sample))

        for pattern in GERMAN_INDICATORS:
            scores["de"] += len(pattern.findall(sample))

        # Basic English detection
        en_pattern = re.compile(
            r"\b(?:the|is|are|was|were|have|has|this|that|with|from|for|and|but|not)\b",
            re.I,
        )
        scores["en"] = len(en_pattern.findall(sample))

        best_lang = max(scores, key=lambda k: scores[k])
        return best_lang if scores[best_lang] > 0 else "fr"

    def _extract_all_clauses(self, text: str, document_type: str) -> list[KeyClause]:
        """Extract all types of key clauses from the document."""
        clauses: list[KeyClause] = []

        # Obligations
        clauses.extend(self.extract_obligations(text))

        # Deadlines
        clauses.extend(
            self._extract_clause_type(
                text, DEADLINE_CLAUSE_PATTERNS, "deadline", "important"
            )
        )

        # Penalties
        clauses.extend(
            self._extract_clause_type(
                text, PENALTY_CLAUSE_PATTERNS, "penalty", "critical"
            )
        )

        # Termination
        clauses.extend(
            self._extract_clause_type(
                text, TERMINATION_CLAUSE_PATTERNS, "termination", "important"
            )
        )

        # Jurisdiction
        clauses.extend(
            self._extract_clause_type(
                text, JURISDICTION_CLAUSE_PATTERNS, "jurisdiction", "normal"
            )
        )

        # Confidentiality
        clauses.extend(
            self._extract_clause_type(
                text, CONFIDENTIALITY_CLAUSE_PATTERNS, "confidentiality", "normal"
            )
        )

        return clauses

    def _extract_clause_type(
        self,
        text: str,
        patterns: list[tuple[re.Pattern, str]],
        clause_type: str,
        importance: str,
    ) -> list[KeyClause]:
        """Extract clauses of a specific type using pattern list."""
        clauses: list[KeyClause] = []
        seen_texts: set[str] = set()

        for pattern, _ in patterns:
            for match in pattern.finditer(text):
                clause_text = match.group(1).strip()
                clause_text = re.sub(r"\s+", " ", clause_text)

                if len(clause_text) < 10:
                    continue
                if len(clause_text) > 500:
                    clause_text = clause_text[:500] + "..."

                normalized = clause_text.lower().strip()
                if normalized in seen_texts:
                    continue
                seen_texts.add(normalized)

                party = self._identify_party_in_clause(clause_text)

                clauses.append(
                    KeyClause(
                        clause_type=clause_type,
                        text=clause_text,
                        importance=importance,
                        party=party,
                    )
                )

        return clauses

    def _extract_parties(self, text: str) -> list[str]:
        """Extract parties (persons and organizations) from the document."""
        parties: list[str] = []
        seen: set[str] = set()

        for pattern in PARTY_PATTERNS:
            for match in pattern.finditer(text):
                # Handle patterns with multiple groups
                for i in range(1, match.lastindex + 1 if match.lastindex else 2):
                    try:
                        party = match.group(i)
                    except IndexError:
                        continue
                    if party:
                        party = party.strip().rstrip(",")
                        party = re.sub(r"\s+", " ", party)
                        # Skip if too short or too long
                        if len(party) < 3 or len(party) > 100:
                            continue
                        normalized = party.lower()
                        if normalized not in seen:
                            seen.add(normalized)
                            parties.append(party)

        return parties

    def _extract_dates(self, text: str) -> list[dict]:
        """Extract dates with their context from the document."""
        dates: list[dict] = []
        seen: set[str] = set()

        for pattern, fmt in DATE_EXTRACTION_PATTERNS:
            for match in pattern.finditer(text):
                try:
                    if fmt == "dmy":
                        d, m, y = (
                            int(match.group(1)),
                            int(match.group(2)),
                            int(match.group(3)),
                        )
                    elif fmt == "ymd":
                        y, m, d = (
                            int(match.group(1)),
                            int(match.group(2)),
                            int(match.group(3)),
                        )
                    elif fmt == "fr_long":
                        d = int(match.group(1))
                        m = MONTH_FR.get(match.group(2).lower(), 0)
                        y = int(match.group(3))
                    else:
                        continue

                    if m == 0:
                        continue

                    parsed = date(y, m, d)
                    date_str = parsed.isoformat()

                    if date_str in seen:
                        continue
                    seen.add(date_str)

                    # Get context (preceding text for date type detection)
                    start = max(0, match.start() - 60)
                    context = text[start : match.start()].strip()

                    # Determine date type from context
                    date_type = "mention"
                    if re.search(
                        r"(?:avant|échéance|deadline|délai|au\s+plus\s+tard)",
                        context,
                        re.I,
                    ):
                        date_type = "deadline"
                    elif re.search(
                        r"(?:fait\s+(?:à|le)|date\s+du|signé\s+le)", context, re.I
                    ):
                        date_type = "document_date"
                    elif re.search(
                        r"(?:audience|comparution|plaidoirie)", context, re.I
                    ):
                        date_type = "hearing"
                    elif re.search(
                        r"(?:né(?:e)?\s+le|date\s+de\s+naissance)", context, re.I
                    ):
                        date_type = "birth_date"
                    elif re.search(
                        r"(?:début|entrée\s+en\s+vigueur|prend\s+effet)", context, re.I
                    ):
                        date_type = "start_date"
                    elif re.search(r"(?:fin|expir|terme|jusqu)", context, re.I):
                        date_type = "end_date"

                    dates.append(
                        {
                            "date": date_str,
                            "context": context[-80:] if len(context) > 80 else context,
                            "type": date_type,
                        }
                    )
                except (ValueError, IndexError):
                    continue

        return dates

    def _extract_amounts(self, text: str) -> list[dict]:
        """Extract monetary amounts from the document."""
        amounts: list[dict] = []
        seen: set[str] = set()

        for pattern in AMOUNT_PATTERNS:
            for match in pattern.finditer(text):
                raw = match.group(1)

                # Normalize: remove thousands separators, fix decimal
                # Belgian format uses . for thousands and , for decimals
                normalized = raw.replace(".", "").replace(",", ".")
                try:
                    value = float(normalized)
                except ValueError:
                    continue

                amount_key = f"{value:.2f}"
                if amount_key in seen:
                    continue
                seen.add(amount_key)

                # Get context
                start = max(0, match.start() - 60)
                context = text[start : match.start()].strip()
                context = context[-80:] if len(context) > 80 else context

                amounts.append(
                    {
                        "amount": value,
                        "currency": "EUR",
                        "context": context,
                        "raw": match.group(0),
                    }
                )

        return amounts

    def _extract_legal_references(self, text: str) -> list[str]:
        """Extract legal references (articles, laws, codes)."""
        references: list[str] = []
        seen: set[str] = set()

        for pattern in LEGAL_REF_PATTERNS:
            for match in pattern.finditer(text):
                ref = match.group(1).strip()
                normalized = ref.lower()
                if normalized not in seen and len(ref) > 3:
                    seen.add(normalized)
                    references.append(ref)

        return references

    def _identify_party_in_clause(self, clause_text: str) -> str | None:
        """Try to identify which party a clause affects."""
        # Look for explicit party references
        party_match = re.search(
            r"\b(le\s+(?:preneur|bailleur|vendeur|acquéreur|employeur|travailleur|"
            r"mandant|mandataire|prêteur|emprunteur|locataire|propriétaire|"
            r"client|prestataire|fournisseur))\b",
            clause_text,
            re.I,
        )
        if party_match:
            return party_match.group(1).strip()

        # Look for named parties (Monsieur/Madame/SA)
        name_match = re.search(
            r"\b((?:Monsieur|Madame|M\.|Mme\.?)\s+[A-ZÀ-Ü][a-zà-ÿ]+)\b",
            clause_text,
        )
        if name_match:
            return name_match.group(1).strip()

        return None

    def _detect_contract_risks(self, text: str) -> list[str]:
        """Detect risks specific to contract documents."""
        risks: list[str] = []

        # Indexation without cap
        if INDEXATION_PATTERN.search(text):
            if not re.search(r"\b(?:plafond|maximum|plafonné)\b", text, re.I):
                risks.append(
                    "Clause d'indexation sans plafond — risque d'augmentation "
                    "non maîtrisée"
                )

        # Missing force majeure clause
        if not re.search(r"\b(?:force\s+majeure|cas\s+fortuit)\b", text, re.I):
            risks.append(
                "Absence de clause de force majeure — recommander son inclusion"
            )

        # Missing GDPR clause for service contracts
        if re.search(r"\b(?:données\s+(?:à\s+caractère\s+)?personnel)", text, re.I):
            if not re.search(r"\b(?:RGPD|GDPR|règlement.*2016/679)\b", text, re.I):
                risks.append(
                    "Traitement de données personnelles mentionné sans "
                    "référence au RGPD — vérifier la conformité"
                )

        # Unilateral modification clause
        if re.search(
            r"\b(?:modifi(?:er|cation)\s+unilatérale(?:ment)?|se\s+réserve\s+le\s+droit\s+de\s+modifier)\b",
            text,
            re.I,
        ):
            risks.append(
                "Clause de modification unilatérale — potentiellement "
                "abusive en droit belge"
            )

        return risks

    def _generate_summary(
        self,
        classification: DocumentClassification,
        parties: list[str],
        dates: list[dict],
        amounts: list[dict],
        clauses: list[KeyClause],
        risks: list[str],
    ) -> list[str]:
        """Generate a list of summary points about the document."""
        summary: list[str] = []

        # Document type
        type_labels = {
            "contract": "Contrat",
            "judgment": "Décision de justice",
            "correspondence": "Correspondance",
            "pleading": "Pièce de procédure",
            "evidence": "Pièce probatoire",
            "mandate": "Mandat/Procuration",
            "invoice": "Facture/État de frais",
            "report": "Rapport/Note",
        }
        type_label = type_labels.get(
            classification.document_type, classification.document_type
        )
        summary.append(
            f"Type: {type_label} ({classification.sub_type}) — "
            f"confiance {classification.confidence:.0%}"
        )

        # Language
        lang_labels = {
            "fr": "Français",
            "nl": "Néerlandais",
            "de": "Allemand",
            "en": "Anglais",
        }
        summary.append(
            f"Langue: {lang_labels.get(classification.language, classification.language)}"
        )

        # Parties
        if parties:
            party_list = ", ".join(parties[:5])
            suffix = f" (+{len(parties) - 5} autres)" if len(parties) > 5 else ""
            summary.append(f"Parties identifiées: {party_list}{suffix}")

        # Key dates
        deadlines = [d for d in dates if d["type"] == "deadline"]
        if deadlines:
            summary.append(f"{len(deadlines)} échéance(s) identifiée(s)")

        # Amounts
        if amounts:
            total = sum(a["amount"] for a in amounts)
            summary.append(f"{len(amounts)} montant(s) — total: {total:,.2f} EUR")

        # Critical clauses
        critical = [c for c in clauses if c.importance == "critical"]
        if critical:
            summary.append(
                f"{len(critical)} clause(s) critique(s) nécessitant attention"
            )

        # Risks
        if risks:
            summary.append(f"{len(risks)} risque(s) identifié(s)")

        return summary

    def _check_completeness(self, text: str, document_type: str) -> list[str]:
        """Check document completeness based on type-specific requirements."""
        issues: list[str] = []
        requirements = COMPLETENESS_REQUIREMENTS.get(document_type, [])

        for pattern, issue_msg in requirements:
            if not pattern.search(text):
                issues.append(issue_msg)

        return issues
