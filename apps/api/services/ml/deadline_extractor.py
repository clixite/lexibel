"""DeadlineExtractor — extract dates and deadlines from legal text.

Handles Belgian legal deadlines:
- Délai de citation: 8 jours (Art. 707 C.J.)
- Appel: 30 jours (Art. 1051 C.J.)
- Cassation: 3 mois (Art. 1073 C.J.)
- Opposition: 30 jours (Art. 1048 C.J.)
- Tierce opposition: 30 jours (Art. 1122 C.J.)
- Requête civile: 6 mois (Art. 1133 C.J.)

Belgian judicial calendar awareness:
- Procedural deadlines exclude weekends and Belgian public holidays
- If deadline falls on weekend/holiday, extends to next business day
"""
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Optional


@dataclass
class Deadline:
    """An extracted deadline from text."""
    text: str               # The matched text fragment
    date: Optional[str]     # ISO date string if computable
    deadline_type: str      # citation, appel, cassation, explicit_date, etc.
    confidence: float       # 0.0 to 1.0
    source_text: str = ""   # Surrounding context
    days: Optional[int] = None  # Number of days if a legal deadline


# ── Belgian public holidays (2026) ──

BELGIAN_HOLIDAYS_2026 = {
    date(2026, 1, 1),    # Nouvel An
    date(2026, 4, 5),    # Pâques (Easter Sunday)
    date(2026, 4, 6),    # Lundi de Pâques
    date(2026, 5, 1),    # Fête du travail
    date(2026, 5, 14),   # Ascension
    date(2026, 5, 25),   # Lundi de Pentecôte
    date(2026, 7, 21),   # Fête nationale
    date(2026, 8, 15),   # Assomption
    date(2026, 11, 1),   # Toussaint
    date(2026, 11, 11),  # Armistice
    date(2026, 12, 25),  # Noël
}


def _is_business_day(d: date) -> bool:
    """Check if a date is a Belgian business day."""
    if d.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    if d in BELGIAN_HOLIDAYS_2026:
        return False
    return True


def _next_business_day(d: date) -> date:
    """Get the next business day if d is not a business day."""
    while not _is_business_day(d):
        d += timedelta(days=1)
    return d


def _add_calendar_days(start: date, days: int) -> date:
    """Add calendar days and adjust to next business day if needed."""
    result = start + timedelta(days=days)
    return _next_business_day(result)


# ── Legal deadline definitions (Belgian Code Judiciaire) ──

LEGAL_DEADLINES = {
    "citation": {
        "days": 8,
        "patterns": [
            re.compile(r"\b(délai\s+de\s+citation|citation\s+à\s+\d+\s+jours?)\b", re.I),
            re.compile(r"\bArt\.?\s*707\s*C\.?\s*J\.?\b", re.I),
        ],
        "label": "Délai de citation (8 jours — Art. 707 C.J.)",
    },
    "appel": {
        "days": 30,
        "patterns": [
            re.compile(r"\b(délai\s+d.appel|appel\s+dans\s+(?:les\s+)?\d+\s+jours?)\b", re.I),
            re.compile(r"\bArt\.?\s*1051\s*C\.?\s*J\.?\b", re.I),
            re.compile(r"\b(interjeter\s+appel|faire\s+appel)\b", re.I),
        ],
        "label": "Délai d'appel (30 jours — Art. 1051 C.J.)",
    },
    "cassation": {
        "days": 90,
        "patterns": [
            re.compile(r"\b(pourvoi\s+en\s+cassation|délai\s+de\s+cassation)\b", re.I),
            re.compile(r"\bArt\.?\s*1073\s*C\.?\s*J\.?\b", re.I),
            re.compile(r"\b(cassation\s+dans\s+(?:les\s+)?\d+\s+mois)\b", re.I),
        ],
        "label": "Délai de cassation (3 mois — Art. 1073 C.J.)",
    },
    "opposition": {
        "days": 30,
        "patterns": [
            re.compile(r"\b(délai\s+d.opposition|opposition\s+dans\s+(?:les\s+)?\d+\s+jours?)\b", re.I),
            re.compile(r"\bArt\.?\s*1048\s*C\.?\s*J\.?\b", re.I),
            re.compile(r"\b(former\s+opposition)\b", re.I),
        ],
        "label": "Délai d'opposition (30 jours — Art. 1048 C.J.)",
    },
    "tierce_opposition": {
        "days": 30,
        "patterns": [
            re.compile(r"\b(tierce\s+opposition)\b", re.I),
            re.compile(r"\bArt\.?\s*1122\s*C\.?\s*J\.?\b", re.I),
        ],
        "label": "Tierce opposition (30 jours — Art. 1122 C.J.)",
    },
    "requete_civile": {
        "days": 180,
        "patterns": [
            re.compile(r"\b(requête\s+civile)\b", re.I),
            re.compile(r"\bArt\.?\s*1133\s*C\.?\s*J\.?\b", re.I),
        ],
        "label": "Requête civile (6 mois — Art. 1133 C.J.)",
    },
    "conclusions": {
        "days": None,  # Variable, extracted from text
        "patterns": [
            re.compile(r"\b(conclusions?\s+(?:dans|avant|pour)\s+le\s+\d{1,2}[./]\d{1,2}[./]\d{2,4})\b", re.I),
            re.compile(r"\b(calendrier\s+de\s+mise\s+en\s+état)\b", re.I),
        ],
        "label": "Délai de conclusions",
    },
}

# ── Explicit date patterns ──

DATE_PATTERNS = [
    # DD/MM/YYYY or DD.MM.YYYY
    (re.compile(r"\b(\d{1,2})[./](\d{1,2})[./](\d{4})\b"), "dmy"),
    # YYYY-MM-DD (ISO)
    (re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"), "ymd"),
    # "15 mars 2026", "3 janvier 2026"
    (re.compile(
        r"\b(\d{1,2})\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+(\d{4})\b",
        re.I,
    ), "fr_long"),
]

MONTH_FR = {
    "janvier": 1, "février": 2, "mars": 3, "avril": 4,
    "mai": 5, "juin": 6, "juillet": 7, "août": 8,
    "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12,
}

# ── N jours/mois patterns ──
RELATIVE_DEADLINE_PATTERN = re.compile(
    r"\b(?:dans|délai\s+de|endéans)\s+(?:les\s+)?(\d+)\s+(jours?|mois|semaines?)\b",
    re.I,
)


class DeadlineExtractor:
    """Extract dates and deadlines from Belgian legal text."""

    def extract(self, text: str, reference_date: Optional[date] = None) -> list[Deadline]:
        """Extract deadlines from text.

        Args:
            text: The text to analyze
            reference_date: Base date for relative deadlines (default: today)

        Returns:
            List of Deadline objects sorted by confidence (descending)
        """
        if not text or not text.strip():
            return []

        ref_date = reference_date or date.today()
        deadlines: list[Deadline] = []

        # 1. Check legal deadline patterns
        for dl_type, dl_info in LEGAL_DEADLINES.items():
            for pattern in dl_info["patterns"]:
                matches = pattern.finditer(text)
                for match in matches:
                    dl_date = None
                    days = dl_info["days"]

                    if days is not None:
                        computed = _add_calendar_days(ref_date, days)
                        dl_date = computed.isoformat()

                    # Get context (50 chars before and after)
                    start = max(0, match.start() - 50)
                    end = min(len(text), match.end() + 50)
                    context = text[start:end].strip()

                    deadlines.append(Deadline(
                        text=match.group(0),
                        date=dl_date,
                        deadline_type=dl_type,
                        confidence=0.85,
                        source_text=context,
                        days=days,
                    ))

        # 2. Extract explicit dates
        for pattern, fmt in DATE_PATTERNS:
            for match in pattern.finditer(text):
                try:
                    if fmt == "dmy":
                        d = int(match.group(1))
                        m = int(match.group(2))
                        y = int(match.group(3))
                    elif fmt == "ymd":
                        y = int(match.group(1))
                        m = int(match.group(2))
                        d = int(match.group(3))
                    elif fmt == "fr_long":
                        d = int(match.group(1))
                        m = MONTH_FR.get(match.group(2).lower(), 0)
                        y = int(match.group(3))
                    else:
                        continue

                    if m == 0:
                        continue

                    parsed_date = date(y, m, d)

                    # Check context for deadline indicators
                    start = max(0, match.start() - 80)
                    end = min(len(text), match.end() + 30)
                    context = text[start:end].strip()

                    is_deadline = bool(re.search(
                        r"(avant|pour|au\s+plus\s+tard|deadline|échéance|date\s+limite|audience|fixation)",
                        context,
                        re.I,
                    ))

                    deadlines.append(Deadline(
                        text=match.group(0),
                        date=parsed_date.isoformat(),
                        deadline_type="explicit_date" if not is_deadline else "explicit_deadline",
                        confidence=0.9 if is_deadline else 0.6,
                        source_text=context,
                    ))
                except (ValueError, IndexError):
                    continue

        # 3. Extract relative deadlines ("dans 15 jours", "endéans 8 jours")
        for match in RELATIVE_DEADLINE_PATTERN.finditer(text):
            amount = int(match.group(1))
            unit = match.group(2).lower()

            if unit.startswith("jour"):
                days = amount
            elif unit.startswith("semaine"):
                days = amount * 7
            elif unit.startswith("mois"):
                days = amount * 30
            else:
                continue

            computed = _add_calendar_days(ref_date, days)

            start = max(0, match.start() - 50)
            end = min(len(text), match.end() + 50)
            context = text[start:end].strip()

            deadlines.append(Deadline(
                text=match.group(0),
                date=computed.isoformat(),
                deadline_type="relative",
                confidence=0.75,
                source_text=context,
                days=days,
            ))

        # Deduplicate by (date, type) and sort by confidence
        seen: set[tuple] = set()
        unique: list[Deadline] = []
        for dl in deadlines:
            key = (dl.date, dl.deadline_type, dl.text)
            if key not in seen:
                seen.add(key)
                unique.append(dl)

        unique.sort(key=lambda d: d.confidence, reverse=True)
        return unique
