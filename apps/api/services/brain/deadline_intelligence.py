"""Deadline Intelligence — Smart deadline tracking and proactive alerts.

Analyzes case timelines to identify upcoming deadlines, suggest filing dates,
and predict potential scheduling conflicts based on Belgian legal procedures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class DeadlineItem:
    """A single deadline extracted from case data."""

    case_id: str
    case_reference: str
    title: str
    deadline_date: date
    days_remaining: int
    urgency: str  # critical, urgent, attention, normal
    source: str  # timeline, calendar, legal_rule
    category: str  # conclusions, audience, appel, opposition, prescription, other
    description: str = ""
    conflicting_deadlines: list[str] = field(default_factory=list)


@dataclass
class FilingSuggestion:
    """Suggested optimal filing date."""

    deadline_date: date
    suggested_filing_date: date
    buffer_days: int
    reason: str


@dataclass
class DeadlineAnalysis:
    """Complete deadline analysis for a case or set of cases."""

    deadlines: list[DeadlineItem] = field(default_factory=list)
    critical_count: int = 0
    urgent_count: int = 0
    conflicts: list[DeadlineConflict] = field(default_factory=list)
    filing_suggestions: list[FilingSuggestion] = field(default_factory=list)
    summary: str = ""


@dataclass
class DeadlineConflict:
    """Two deadlines that conflict in timing."""

    deadline_a: str
    deadline_b: str
    date_a: date
    date_b: date
    overlap_days: int
    severity: str  # high, medium, low
    recommendation: str


@dataclass
class LegalDeadline:
    """A Belgian legal deadline computed from an event."""

    name: str
    description_fr: str
    legal_basis: str  # Article reference
    event_date: date
    deadline_date: date
    calendar_days: int
    is_business_days: bool
    category: str  # appel, opposition, cassation, citation, conclusions, prescription


@dataclass
class WeekWorkload:
    """Workload for a single week."""

    week_start: date
    week_end: date
    deadline_count: int
    deadlines: list[str] = field(default_factory=list)
    is_overloaded: bool = False


@dataclass
class WorkloadPrediction:
    """Workload prediction for the upcoming weeks."""

    weeks: list[WeekWorkload] = field(default_factory=list)
    peak_week: date | None = None
    peak_count: int = 0
    total_deadlines: int = 0
    overload_warnings: list[str] = field(default_factory=list)
    summary: str = ""


# ---------------------------------------------------------------------------
# Belgian Legal Deadline Definitions
# ---------------------------------------------------------------------------

# Belgian legal deadlines by event type
# Reference: Code Judiciaire (C.J.) and Code d'Instruction Criminelle (C.I.Cr.)
BELGIAN_LEGAL_DEADLINES: dict[str, list[dict[str, Any]]] = {
    "judgment": [
        {
            "name": "appel",
            "description_fr": "Délai d'appel",
            "legal_basis": "Art. 1051 C.J.",
            "calendar_days": 30,
            "is_business_days": False,
            "category": "appel",
        },
        {
            "name": "cassation",
            "description_fr": "Pourvoi en cassation",
            "legal_basis": "Art. 1073 C.J.",
            "calendar_days": 90,
            "is_business_days": False,
            "category": "cassation",
        },
        {
            "name": "opposition",
            "description_fr": "Délai d'opposition (défaut)",
            "legal_basis": "Art. 1048 C.J.",
            "calendar_days": 30,
            "is_business_days": False,
            "category": "opposition",
        },
    ],
    "citation": [
        {
            "name": "comparution_citation",
            "description_fr": "Délai de comparution après citation",
            "legal_basis": "Art. 707 C.J.",
            "calendar_days": 8,
            "is_business_days": False,
            "category": "citation",
        },
    ],
    "penal_judgment": [
        {
            "name": "appel_penal",
            "description_fr": "Délai d'appel en matière pénale",
            "legal_basis": "Art. 203 C.I.Cr.",
            "calendar_days": 30,
            "is_business_days": False,
            "category": "appel",
        },
        {
            "name": "opposition_penale",
            "description_fr": "Délai d'opposition en matière pénale",
            "legal_basis": "Art. 187 C.I.Cr.",
            "calendar_days": 15,
            "is_business_days": False,
            "category": "opposition",
        },
        {
            "name": "cassation_penale",
            "description_fr": "Pourvoi en cassation (pénal)",
            "legal_basis": "Art. 373 C.I.Cr.",
            "calendar_days": 15,
            "is_business_days": False,
            "category": "cassation",
        },
    ],
    "notification": [
        {
            "name": "recours_fiscal",
            "description_fr": "Réclamation contre une cotisation fiscale",
            "legal_basis": "Art. 371 CIR 92",
            "calendar_days": 186,
            "is_business_days": False,
            "category": "opposition",
        },
    ],
    "dismissal": [
        {
            "name": "contestation_licenciement",
            "description_fr": "Contestation du licenciement manifestement déraisonnable",
            "legal_basis": "CCT n°109",
            "calendar_days": 365,
            "is_business_days": False,
            "category": "prescription",
        },
    ],
}

# Prescription periods by matter type (in years)
PRESCRIPTION_PERIODS: dict[str, list[dict[str, Any]]] = {
    "civil": [
        {
            "name": "prescription_10_ans",
            "description_fr": "Prescription ordinaire (actions personnelles)",
            "legal_basis": "Art. 2262bis §1 C. civ.",
            "years": 10,
        },
        {
            "name": "prescription_extra_contractuelle",
            "description_fr": "Responsabilité extracontractuelle",
            "legal_basis": "Art. 2262bis §1 al. 2 C. civ.",
            "years": 5,
        },
    ],
    "penal": [
        {
            "name": "prescription_delit",
            "description_fr": "Prescription de l'action publique (délit)",
            "legal_basis": "Art. 21 T.P. C.I.Cr.",
            "years": 5,
        },
        {
            "name": "prescription_crime",
            "description_fr": "Prescription de l'action publique (crime)",
            "legal_basis": "Art. 21 T.P. C.I.Cr.",
            "years": 10,
        },
    ],
    "commercial": [
        {
            "name": "prescription_commerciale",
            "description_fr": "Prescription commerciale ordinaire",
            "legal_basis": "Art. 2262bis §1 C. civ.",
            "years": 10,
        },
    ],
    "family": [
        {
            "name": "prescription_aliments",
            "description_fr": "Arriérés de pension alimentaire",
            "legal_basis": "Art. 2277 C. civ.",
            "years": 5,
        },
    ],
    "fiscal": [
        {
            "name": "prescription_impot",
            "description_fr": "Prescription ordinaire en matière fiscale",
            "legal_basis": "Art. 354 CIR 92",
            "years": 3,
        },
        {
            "name": "prescription_fraude",
            "description_fr": "Prescription étendue (fraude fiscale)",
            "legal_basis": "Art. 354 al. 2 CIR 92",
            "years": 7,
        },
    ],
    "social": [
        {
            "name": "prescription_salaire",
            "description_fr": "Arriérés de salaire",
            "legal_basis": "Art. 15 Loi du 3/7/1978",
            "years": 1,
        },
        {
            "name": "prescription_sociale",
            "description_fr": "Actions en matière de droit du travail",
            "legal_basis": "Art. 15 Loi du 3/7/1978",
            "years": 5,
        },
    ],
}

# Urgency classification thresholds (calendar days)
URGENCY_THRESHOLDS = {
    "critical": 3,
    "urgent": 7,
    "attention": 14,
}

# Maximum comfortable deadlines per week before overload
MAX_DEADLINES_PER_WEEK = 5


# ---------------------------------------------------------------------------
# DeadlineIntelligence
# ---------------------------------------------------------------------------


class DeadlineIntelligence:
    """Smart deadline tracking and proactive alerting for Belgian legal practice.

    Analyzes case timelines, computes statutory deadlines from Belgian law,
    identifies scheduling conflicts, and predicts workload distribution.
    """

    # ------------------------------------------------------------------
    # Deadline Analysis
    # ------------------------------------------------------------------

    def analyze_deadlines(
        self,
        case_data: dict[str, Any],
        timeline_events: list[dict[str, Any]],
        calendar_events: list[dict[str, Any]] | None = None,
    ) -> DeadlineAnalysis:
        """Analyze all deadlines for a case.

        Extracts deadlines from timeline events and calendar events, calculates
        days remaining, assesses urgency, identifies conflicts, and suggests
        optimal filing dates.

        Args:
            case_data: Serialized Case model fields.
            timeline_events: Timeline events for the case.
            calendar_events: Optional calendar events for the case.

        Returns:
            DeadlineAnalysis with sorted deadlines and conflict information.
        """
        today = date.today()
        case_id = str(case_data.get("id", ""))
        case_ref = case_data.get("reference", "")
        calendar_events = calendar_events or []

        deadlines: list[DeadlineItem] = []

        # Extract from timeline events
        for event in timeline_events:
            deadline = self._extract_deadline_from_event(
                event, case_id, case_ref, today
            )
            if deadline is not None:
                deadlines.append(deadline)

        # Extract from calendar events
        for cal_event in calendar_events:
            deadline = self._extract_deadline_from_calendar(
                cal_event, case_id, case_ref, today
            )
            if deadline is not None:
                deadlines.append(deadline)

        # Sort by deadline date
        deadlines.sort(key=lambda d: d.deadline_date)

        # Filter to upcoming deadlines only (and recently past for warnings)
        relevant = [d for d in deadlines if d.days_remaining >= -7]

        # Identify conflicts
        conflicts = self._find_conflicts(relevant)

        # Mark conflicting deadlines on items
        for conflict in conflicts:
            for dl in relevant:
                if dl.title in (conflict.deadline_a, conflict.deadline_b):
                    other = (
                        conflict.deadline_b
                        if dl.title == conflict.deadline_a
                        else conflict.deadline_a
                    )
                    if other not in dl.conflicting_deadlines:
                        dl.conflicting_deadlines.append(other)

        # Generate filing suggestions
        filing_suggestions = self._suggest_filing_dates(relevant)

        critical_count = sum(1 for d in relevant if d.urgency == "critical")
        urgent_count = sum(1 for d in relevant if d.urgency == "urgent")

        summary = self._build_deadline_summary(
            relevant, critical_count, urgent_count, conflicts
        )

        return DeadlineAnalysis(
            deadlines=relevant,
            critical_count=critical_count,
            urgent_count=urgent_count,
            conflicts=conflicts,
            filing_suggestions=filing_suggestions,
            summary=summary,
        )

    def _extract_deadline_from_event(
        self,
        event: dict[str, Any],
        case_id: str,
        case_ref: str,
        today: date,
    ) -> DeadlineItem | None:
        """Extract a deadline item from a timeline event."""
        event_date = self._parse_date(event.get("event_date"))
        if event_date is None:
            return None

        category = event.get("category", "")
        title = event.get("title", "")
        title_lower = title.lower()

        # Detect deadline-type events
        is_deadline = category in ("deadline", "hearing", "audience") or any(
            kw in title_lower
            for kw in (
                "délai",
                "audience",
                "deadline",
                "échéance",
                "conclusions",
                "comparution",
                "plaidoiries",
                "jugement",
            )
        )
        if not is_deadline:
            return None

        days_remaining = (event_date - today).days
        urgency = self._classify_urgency(days_remaining)

        # Determine category
        dl_category = "other"
        if "conclusion" in title_lower:
            dl_category = "conclusions"
        elif "audience" in title_lower or "plaidoirie" in title_lower:
            dl_category = "audience"
        elif "appel" in title_lower:
            dl_category = "appel"
        elif "opposition" in title_lower:
            dl_category = "opposition"
        elif "prescription" in title_lower:
            dl_category = "prescription"

        return DeadlineItem(
            case_id=case_id,
            case_reference=case_ref,
            title=title,
            deadline_date=event_date,
            days_remaining=days_remaining,
            urgency=urgency,
            source="timeline",
            category=dl_category,
            description=event.get("description", ""),
        )

    def _extract_deadline_from_calendar(
        self,
        cal_event: dict[str, Any],
        case_id: str,
        case_ref: str,
        today: date,
    ) -> DeadlineItem | None:
        """Extract a deadline item from a calendar event."""
        start_time = cal_event.get("start_time")
        if start_time is None:
            return None

        if isinstance(start_time, str):
            try:
                event_date = datetime.fromisoformat(start_time).date()
            except (ValueError, TypeError):
                return None
        elif isinstance(start_time, datetime):
            event_date = start_time.date()
        elif isinstance(start_time, date):
            event_date = start_time
        else:
            return None

        title = cal_event.get("title", "")
        title_lower = title.lower()

        # Calendar events are considered deadlines if they match legal keywords
        is_legal = any(
            kw in title_lower
            for kw in (
                "audience",
                "plaidoiries",
                "conclusions",
                "délai",
                "tribunal",
                "cour",
                "chambre",
                "greffe",
                "médiation",
                "expertise",
            )
        )
        if not is_legal:
            return None

        days_remaining = (event_date - today).days
        urgency = self._classify_urgency(days_remaining)

        return DeadlineItem(
            case_id=case_id,
            case_reference=case_ref,
            title=title,
            deadline_date=event_date,
            days_remaining=days_remaining,
            urgency=urgency,
            source="calendar",
            category="audience" if "audience" in title_lower else "other",
            description=cal_event.get("description", "") or "",
        )

    # ------------------------------------------------------------------
    # Belgian Legal Deadlines
    # ------------------------------------------------------------------

    def get_belgian_legal_deadlines(
        self,
        matter_type: str,
        event_type: str,
        event_date: date | str,
    ) -> list[LegalDeadline]:
        """Compute Belgian legal deadlines from a triggering event.

        Uses statutory deadline definitions from the Code Judiciaire,
        Code d'Instruction Criminelle, and other Belgian legal sources.

        Args:
            matter_type: Type of legal matter (civil, penal, etc.).
            event_type: Type of triggering event (judgment, citation, etc.).
            event_date: Date of the triggering event.

        Returns:
            List of computed LegalDeadline objects.
        """
        parsed_date = self._parse_date(event_date)
        if parsed_date is None:
            return []

        deadlines: list[LegalDeadline] = []

        # Get deadlines for the event type
        event_deadlines = BELGIAN_LEGAL_DEADLINES.get(event_type, [])
        for dl_def in event_deadlines:
            deadline_date = parsed_date + timedelta(days=dl_def["calendar_days"])

            deadlines.append(
                LegalDeadline(
                    name=dl_def["name"],
                    description_fr=dl_def["description_fr"],
                    legal_basis=dl_def["legal_basis"],
                    event_date=parsed_date,
                    deadline_date=deadline_date,
                    calendar_days=dl_def["calendar_days"],
                    is_business_days=dl_def["is_business_days"],
                    category=dl_def["category"],
                )
            )

        # Add prescription deadlines for the matter type
        prescriptions = PRESCRIPTION_PERIODS.get(matter_type, [])
        for pres_def in prescriptions:
            years = pres_def["years"]
            # Approximate: use 365.25 days per year
            pres_date = parsed_date + timedelta(days=int(years * 365.25))

            deadlines.append(
                LegalDeadline(
                    name=pres_def["name"],
                    description_fr=pres_def["description_fr"],
                    legal_basis=pres_def["legal_basis"],
                    event_date=parsed_date,
                    deadline_date=pres_date,
                    calendar_days=int(years * 365.25),
                    is_business_days=False,
                    category="prescription",
                )
            )

        # Sort by deadline date
        deadlines.sort(key=lambda d: d.deadline_date)

        return deadlines

    # ------------------------------------------------------------------
    # Workload Prediction
    # ------------------------------------------------------------------

    def predict_workload(
        self,
        all_cases_deadlines: list[dict[str, Any]],
    ) -> WorkloadPrediction:
        """Predict workload distribution for the next 4 weeks.

        Analyzes deadlines across all cases to identify peak periods,
        overload risks, and distribution patterns.

        Args:
            all_cases_deadlines: List of deadline dicts with 'deadline_date',
                'title', and 'case_reference' keys.

        Returns:
            WorkloadPrediction with weekly breakdown and warnings.
        """
        today = date.today()
        weeks: list[WeekWorkload] = []

        # Build 4 weeks starting from the current Monday
        current_monday = today - timedelta(days=today.weekday())

        for week_offset in range(4):
            week_start = current_monday + timedelta(weeks=week_offset)
            week_end = week_start + timedelta(days=6)

            week_deadlines: list[str] = []
            for dl in all_cases_deadlines:
                dl_date = self._parse_date(dl.get("deadline_date"))
                if dl_date is None:
                    continue
                if week_start <= dl_date <= week_end:
                    label = f"{dl.get('case_reference', '?')} — {dl.get('title', '?')}"
                    week_deadlines.append(label)

            count = len(week_deadlines)
            is_overloaded = count > MAX_DEADLINES_PER_WEEK

            weeks.append(
                WeekWorkload(
                    week_start=week_start,
                    week_end=week_end,
                    deadline_count=count,
                    deadlines=week_deadlines,
                    is_overloaded=is_overloaded,
                )
            )

        # Identify peak week
        peak_week = None
        peak_count = 0
        total_deadlines = 0
        overload_warnings: list[str] = []

        for week in weeks:
            total_deadlines += week.deadline_count
            if week.deadline_count > peak_count:
                peak_count = week.deadline_count
                peak_week = week.week_start
            if week.is_overloaded:
                overload_warnings.append(
                    f"Semaine du {week.week_start.isoformat()} : "
                    f"{week.deadline_count} délais (surcharge)"
                )

        summary = self._build_workload_summary(
            total_deadlines, peak_week, peak_count, overload_warnings
        )

        return WorkloadPrediction(
            weeks=weeks,
            peak_week=peak_week,
            peak_count=peak_count,
            total_deadlines=total_deadlines,
            overload_warnings=overload_warnings,
            summary=summary,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

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
    def _classify_urgency(days_remaining: int) -> str:
        """Classify deadline urgency based on days remaining."""
        if days_remaining < 0:
            return "critical"  # Overdue
        if days_remaining <= URGENCY_THRESHOLDS["critical"]:
            return "critical"
        if days_remaining <= URGENCY_THRESHOLDS["urgent"]:
            return "urgent"
        if days_remaining <= URGENCY_THRESHOLDS["attention"]:
            return "attention"
        return "normal"

    @staticmethod
    def _find_conflicts(deadlines: list[DeadlineItem]) -> list[DeadlineConflict]:
        """Find scheduling conflicts between deadlines.

        Two deadlines are considered conflicting if they fall on the same day
        or within 1 calendar day of each other.
        """
        conflicts: list[DeadlineConflict] = []
        seen: set[tuple[str, str]] = set()

        for i, dl_a in enumerate(deadlines):
            for dl_b in deadlines[i + 1 :]:
                if dl_a.case_id == dl_b.case_id and dl_a.title == dl_b.title:
                    continue  # Skip duplicate

                pair_key = tuple(sorted([dl_a.title, dl_b.title]))
                if pair_key in seen:
                    continue

                diff = abs((dl_a.deadline_date - dl_b.deadline_date).days)
                if diff <= 1:
                    severity = "high" if diff == 0 else "medium"
                    recommendation = (
                        f"Deux délais coïncident "
                        f"({'même jour' if diff == 0 else 'jours consécutifs'}). "
                        f"Planifiez la préparation en amont."
                    )
                    conflicts.append(
                        DeadlineConflict(
                            deadline_a=dl_a.title,
                            deadline_b=dl_b.title,
                            date_a=dl_a.deadline_date,
                            date_b=dl_b.deadline_date,
                            overlap_days=diff,
                            severity=severity,
                            recommendation=recommendation,
                        )
                    )
                    seen.add(pair_key)

        return conflicts

    @staticmethod
    def _suggest_filing_dates(
        deadlines: list[DeadlineItem],
    ) -> list[FilingSuggestion]:
        """Suggest optimal filing dates with buffer before each deadline."""
        suggestions: list[FilingSuggestion] = []
        today = date.today()

        for dl in deadlines:
            if dl.days_remaining <= 0:
                continue  # Cannot file for past deadlines

            # Suggest filing 2 business days before deadline
            # Simple heuristic: subtract 3 calendar days (accounts for weekends)
            buffer_days = min(3, dl.days_remaining - 1)
            if buffer_days < 1:
                buffer_days = 0

            suggested = dl.deadline_date - timedelta(days=buffer_days)

            # Do not suggest a date in the past
            if suggested < today:
                suggested = today

            # Avoid weekends
            if suggested.weekday() == 5:  # Saturday
                suggested -= timedelta(days=1)
            elif suggested.weekday() == 6:  # Sunday
                suggested -= timedelta(days=2)

            if suggested < today:
                suggested = today

            reason = (
                f"Dépôt recommandé {buffer_days} jour(s) avant l'échéance du "
                f"{dl.deadline_date.isoformat()} pour {dl.title}"
            )

            suggestions.append(
                FilingSuggestion(
                    deadline_date=dl.deadline_date,
                    suggested_filing_date=suggested,
                    buffer_days=buffer_days,
                    reason=reason,
                )
            )

        return suggestions

    @staticmethod
    def _build_deadline_summary(
        deadlines: list[DeadlineItem],
        critical_count: int,
        urgent_count: int,
        conflicts: list[DeadlineConflict],
    ) -> str:
        """Build a human-readable deadline summary in French."""
        total = len(deadlines)
        if total == 0:
            return "Aucun délai identifié pour ce dossier."

        parts: list[str] = [f"{total} délai(s) identifié(s)"]
        if critical_count > 0:
            parts.append(f"{critical_count} critique(s)")
        if urgent_count > 0:
            parts.append(f"{urgent_count} urgent(s)")
        if conflicts:
            parts.append(f"{len(conflicts)} conflit(s) de calendrier")

        return " — ".join(parts) + "."

    @staticmethod
    def _build_workload_summary(
        total: int,
        peak_week: date | None,
        peak_count: int,
        warnings: list[str],
    ) -> str:
        """Build workload prediction summary in French."""
        if total == 0:
            return "Aucun délai dans les 4 prochaines semaines."

        summary = f"{total} délai(s) dans les 4 prochaines semaines."

        if peak_week:
            summary += (
                f" Semaine la plus chargée : {peak_week.isoformat()} "
                f"({peak_count} délai(s))."
            )

        if warnings:
            summary += f" Attention : {len(warnings)} semaine(s) en surcharge."

        return summary
