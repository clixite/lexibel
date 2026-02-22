"""Belgian legal deadline calculator.

Computes prescription, appeal, opposition, cassation, and procedural
deadlines based on Belgian law (Code civil, Code judiciaire, Code pénal).

All deadlines account for:
- Belgian legal calendar (dies a quo excluded, dies ad quem included)
- Art. 53bis C.Jud.: if deadline falls on Saturday/Sunday/holiday → next business day
- Belgian public holidays (jours fériés légaux)

References:
- Prescription civile: Art. 2262bis ancien C.Civ. (10 ans, 5 ans contractuel)
- Prescription pénale: Art. 21-25 TPCPP
- Appel civil: Art. 1051 C.Jud. (1 mois)
- Opposition: Art. 1048 C.Jud. (1 mois)
- Pourvoi en cassation: Art. 1073 C.Jud. (3 mois)
- Délai de citation: Art. 707 C.Jud. (8 jours minimum)
- Requête civile: Art. 1133 C.Jud.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta


# ── Belgian public holidays ──


def _belgian_holidays(year: int) -> set[date]:
    """Belgian legal public holidays for a given year."""
    holidays = {
        date(year, 1, 1),  # Nouvel An
        date(year, 5, 1),  # Fête du Travail
        date(year, 7, 21),  # Fête nationale
        date(year, 8, 15),  # Assomption
        date(year, 11, 1),  # Toussaint
        date(year, 11, 11),  # Armistice
        date(year, 12, 25),  # Noël
    }
    # Easter-based holidays (Meeus algorithm)
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    el = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * el) // 451
    month = (h + el - 7 * m + 114) // 31
    day = ((h + el - 7 * m + 114) % 31) + 1
    easter = date(year, month, day)

    holidays.add(easter + timedelta(days=1))  # Lundi de Pâques
    holidays.add(easter + timedelta(days=39))  # Ascension
    holidays.add(easter + timedelta(days=50))  # Lundi de Pentecôte

    return holidays


def next_business_day(d: date) -> date:
    """Art. 53bis C.Jud.: if deadline falls on non-business day, extend to next one."""
    holidays = _belgian_holidays(d.year) | _belgian_holidays(d.year + 1)
    while d.weekday() >= 5 or d in holidays:  # 5=Saturday, 6=Sunday
        d += timedelta(days=1)
    return d


def add_months(start: date, months: int) -> date:
    """Add calendar months to a date (Belgian legal computation)."""
    month = start.month - 1 + months
    year = start.year + month // 12
    month = month % 12 + 1
    # Handle end-of-month (e.g., Jan 31 + 1 month = Feb 28)
    import calendar

    max_day = calendar.monthrange(year, month)[1]
    day = min(start.day, max_day)
    return date(year, month, day)


@dataclass
class Deadline:
    """A computed legal deadline."""

    title: str
    date: date
    legal_basis: str
    days_remaining: int
    urgency: str  # normal | warning | urgent | overdue
    category: str  # prescription | appeal | procedural | custom
    notes: str = ""


@dataclass
class DeadlineReport:
    """Full deadline analysis for a case."""

    case_id: str
    matter_type: str
    deadlines: list[Deadline] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ── Deadline definitions per matter type ──

PRESCRIPTION_RULES: dict[str, list[dict]] = {
    "civil": [
        {
            "title": "Prescription de droit commun",
            "months": 120,  # 10 ans
            "basis": "Art. 2262bis §1 ancien C.Civ.",
            "notes": "Action personnelle: 10 ans à compter du fait générateur",
        },
        {
            "title": "Prescription contractuelle courte",
            "months": 60,  # 5 ans
            "basis": "Art. 2262bis §1 al.2 ancien C.Civ.",
            "notes": "Réparation dommage contractuel: 5 ans à compter de la connaissance du dommage",
        },
    ],
    "commercial": [
        {
            "title": "Prescription commerciale de droit commun",
            "months": 120,
            "basis": "Art. 2262bis ancien C.Civ.",
            "notes": "10 ans — actions entre commerçants",
        },
    ],
    "penal": [
        {
            "title": "Prescription action publique — contravention",
            "months": 6,
            "basis": "Art. 24 TPCPP",
            "notes": "6 mois",
        },
        {
            "title": "Prescription action publique — délit",
            "months": 60,
            "basis": "Art. 21 TPCPP",
            "notes": "5 ans à compter de l'infraction",
        },
        {
            "title": "Prescription action publique — crime",
            "months": 120,
            "basis": "Art. 21 TPCPP",
            "notes": "10 ans (15 ans pour crimes graves)",
        },
    ],
    "family": [
        {
            "title": "Action en divorce — pas de prescription",
            "months": 0,
            "basis": "Art. 229 C.Civ.",
            "notes": "Imprescriptible. Séparation de fait ≥1 an pour cause irrémédiable",
        },
        {
            "title": "Pension alimentaire — arriérés",
            "months": 60,
            "basis": "Art. 2277 ancien C.Civ.",
            "notes": "5 ans pour les arriérés de pension",
        },
    ],
    "social": [
        {
            "title": "Action en paiement de rémunération",
            "months": 12,
            "basis": "Art. 15 Loi du 3/7/1978",
            "notes": "1 an après fin du contrat de travail",
        },
        {
            "title": "Prescription rémunération — droit commun",
            "months": 60,
            "basis": "Art. 2262bis ancien C.Civ.",
            "notes": "5 ans si le contrat est encore en cours",
        },
    ],
    "fiscal": [
        {
            "title": "Impôts directs — imposition ordinaire",
            "months": 36,
            "basis": "Art. 354 CIR 92",
            "notes": "3 ans à partir du 1er janvier de l'exercice d'imposition",
        },
        {
            "title": "Impôts directs — fraude",
            "months": 84,
            "basis": "Art. 354 al.2 CIR 92",
            "notes": "7 ans en cas de fraude fiscale",
        },
    ],
    "administrative": [
        {
            "title": "Recours au Conseil d'État",
            "months": 0,
            "basis": "Art. 4 Lois coordonnées CE",
            "notes": "60 jours à compter de la notification de l'acte",
        },
    ],
}

APPEAL_DEADLINES: list[dict] = [
    {
        "title": "Appel — jugement contradictoire",
        "months": 1,
        "basis": "Art. 1051 C.Jud.",
        "category": "appeal",
        "notes": "1 mois à compter de la signification du jugement",
    },
    {
        "title": "Opposition — jugement par défaut",
        "months": 1,
        "basis": "Art. 1048 C.Jud.",
        "category": "appeal",
        "notes": "1 mois à compter de la signification",
    },
    {
        "title": "Pourvoi en cassation",
        "months": 3,
        "basis": "Art. 1073 C.Jud.",
        "category": "appeal",
        "notes": "3 mois à compter de la signification de la décision",
    },
]

PROCEDURAL_DEADLINES: list[dict] = [
    {
        "title": "Délai de citation minimum",
        "days": 8,
        "basis": "Art. 707 C.Jud.",
        "category": "procedural",
        "notes": "8 jours minimum entre citation et audience",
    },
    {
        "title": "Délai de comparution volontaire",
        "days": 0,
        "basis": "Art. 706 C.Jud.",
        "category": "procedural",
        "notes": "Pas de délai — comparution immédiate possible",
    },
]


def _urgency(days_remaining: int) -> str:
    if days_remaining < 0:
        return "overdue"
    if days_remaining <= 7:
        return "urgent"
    if days_remaining <= 30:
        return "warning"
    return "normal"


def compute_prescription_deadlines(
    matter_type: str,
    start_date: date,
    today: date | None = None,
) -> list[Deadline]:
    """Compute prescription deadlines for a matter type from a start date."""
    today = today or date.today()
    rules = PRESCRIPTION_RULES.get(matter_type, PRESCRIPTION_RULES.get("civil", []))
    deadlines = []

    for rule in rules:
        if rule["months"] == 0:
            continue
        deadline_date = add_months(start_date, rule["months"])
        deadline_date = next_business_day(deadline_date)
        days_remaining = (deadline_date - today).days

        deadlines.append(
            Deadline(
                title=rule["title"],
                date=deadline_date,
                legal_basis=rule["basis"],
                days_remaining=days_remaining,
                urgency=_urgency(days_remaining),
                category="prescription",
                notes=rule["notes"],
            )
        )

    return deadlines


def compute_appeal_deadlines(
    judgment_date: date,
    today: date | None = None,
) -> list[Deadline]:
    """Compute appeal/opposition/cassation deadlines from judgment date."""
    today = today or date.today()
    deadlines = []

    for rule in APPEAL_DEADLINES:
        deadline_date = add_months(judgment_date, rule["months"])
        deadline_date = next_business_day(deadline_date)
        days_remaining = (deadline_date - today).days

        deadlines.append(
            Deadline(
                title=rule["title"],
                date=deadline_date,
                legal_basis=rule["basis"],
                days_remaining=days_remaining,
                urgency=_urgency(days_remaining),
                category=rule["category"],
                notes=rule["notes"],
            )
        )

    return deadlines


def compute_case_deadlines(
    matter_type: str,
    opened_at: date,
    metadata: dict | None = None,
    today: date | None = None,
) -> DeadlineReport:
    """Full deadline analysis for a case.

    Uses case metadata for additional dates:
    - metadata.key_dates.prescription_date
    - metadata.key_dates.judgment_date
    - metadata.key_dates.next_hearing
    """
    today = today or date.today()
    metadata = metadata or {}
    key_dates = metadata.get("key_dates", {})

    report = DeadlineReport(case_id="", matter_type=matter_type)

    # Prescription deadlines
    prescription_start = opened_at
    if key_dates.get("prescription_date"):
        try:
            prescription_start = date.fromisoformat(key_dates["prescription_date"])
        except (ValueError, TypeError):
            pass

    report.deadlines.extend(
        compute_prescription_deadlines(matter_type, prescription_start, today)
    )

    # Appeal deadlines (if judgment date exists)
    if key_dates.get("judgment_date"):
        try:
            judgment_date = date.fromisoformat(key_dates["judgment_date"])
            report.deadlines.extend(compute_appeal_deadlines(judgment_date, today))
        except (ValueError, TypeError):
            report.warnings.append("Date de jugement invalide dans les métadonnées")

    # Next hearing warning
    if key_dates.get("next_hearing"):
        try:
            hearing = date.fromisoformat(key_dates["next_hearing"])
            days_to_hearing = (hearing - today).days
            report.deadlines.append(
                Deadline(
                    title="Prochaine audience",
                    date=hearing,
                    legal_basis="Calendrier de procédure",
                    days_remaining=days_to_hearing,
                    urgency=_urgency(days_to_hearing),
                    category="procedural",
                    notes="Date fixée au calendrier",
                )
            )
        except (ValueError, TypeError):
            pass

    # Custom deadlines from metadata
    for custom in metadata.get("deadlines", []):
        try:
            dl_date = date.fromisoformat(custom["date"])
            days_remaining = (dl_date - today).days
            report.deadlines.append(
                Deadline(
                    title=custom.get("title", "Échéance"),
                    date=dl_date,
                    legal_basis=custom.get("legal_basis", "Convention / Ordonnance"),
                    days_remaining=days_remaining,
                    urgency=_urgency(days_remaining),
                    category="custom",
                    notes=custom.get("notes", ""),
                )
            )
        except (ValueError, TypeError, KeyError):
            pass

    # Sort by date
    report.deadlines.sort(key=lambda d: d.date)

    # Generate warnings
    overdue = [d for d in report.deadlines if d.urgency == "overdue"]
    urgent = [d for d in report.deadlines if d.urgency == "urgent"]

    if overdue:
        report.warnings.append(
            f"⚠ {len(overdue)} délai(s) dépassé(s) : {', '.join(d.title for d in overdue)}"
        )
    if urgent:
        report.warnings.append(
            f"🔴 {len(urgent)} délai(s) urgent(s) (<7j) : {', '.join(d.title for d in urgent)}"
        )

    return report
