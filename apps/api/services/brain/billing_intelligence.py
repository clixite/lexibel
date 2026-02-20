"""Billing Intelligence — Smart billing analysis and recommendations.

Detects unbilled work, suggests invoicing opportunities,
identifies billing anomalies, and optimizes revenue.
Designed for Belgian law firm billing practices.
"""

from dataclasses import dataclass, field
from datetime import datetime


# ── Data classes ──


@dataclass
class BillingAnomaly:
    """A billing anomaly detected in case data."""

    anomaly_type: (
        str  # unbilled_time, unusual_hours, missing_rate, overdue_invoice, low_recovery
    )
    severity: str  # low, medium, high
    description: str
    case_id: str | None = None
    amount_at_risk: float = 0.0
    recommended_action: str = ""


@dataclass
class InvoiceSuggestion:
    """A suggestion to create an invoice."""

    case_id: str
    case_title: str
    unbilled_hours: float
    estimated_amount: float
    last_invoice_date: str | None = None
    days_since_last_invoice: int = 0
    urgency: str = "normal"  # normal, recommended, overdue


@dataclass
class BillingReport:
    """Complete billing intelligence report."""

    total_unbilled_hours: float
    total_unbilled_amount: float
    anomalies: list[BillingAnomaly] = field(default_factory=list)
    invoice_suggestions: list[InvoiceSuggestion] = field(default_factory=list)
    monthly_trend: list[dict] = field(default_factory=list)  # [{month, hours, amount}]
    recovery_rate: float = 0.0  # percentage of billed vs worked hours
    recommendations: list[str] = field(default_factory=list)


# ── Thresholds and configuration ──

# Belgian law firm standard targets
RECOVERY_RATE_TARGET = 0.80  # 80% is typical Belgian law firm target
UNBILLED_HOURS_THRESHOLD = 10.0  # Flag cases with > 10 unbilled hours
DAYS_WITHOUT_INVOICE_THRESHOLD = 30  # Flag if no invoice in > 30 days
UNUSUAL_DAILY_HOURS = 12.0  # Flag if > 12h logged in a single day
MAX_REASONABLE_DAILY_HOURS = 16.0  # Clearly incorrect if exceeded
DEFAULT_HOURLY_RATE = 150.0  # Fallback rate for estimation (EUR)
OVERDUE_INVOICE_DAYS = 30  # Invoice considered overdue after 30 days
CRITICAL_OVERDUE_DAYS = 60  # Critical after 60 days


def _parse_datetime(value: object) -> datetime | None:
    """Parse a datetime from string or datetime object."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None
    return None


def _parse_date_str(value: object) -> str | None:
    """Parse a date and return ISO date string."""
    dt = _parse_datetime(value)
    if dt:
        return dt.date().isoformat()
    return None


def _safe_float(value: object, default: float = 0.0) -> float:
    """Safely convert a value to float."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


class BillingIntelligence:
    """Smart billing analysis for Belgian law firms.

    Analyzes time entries, invoices, and cases to detect billing
    opportunities, anomalies, and provide actionable recommendations.
    All data is passed in — no database dependencies.
    """

    def analyze_billing(
        self,
        time_entries: list[dict],
        invoices: list[dict],
        cases: list[dict],
    ) -> BillingReport:
        """Perform comprehensive billing analysis.

        Args:
            time_entries: List of time entry dicts with keys:
                id, case_id, hours, date, description, hourly_rate (optional),
                billed (bool, optional), user_id (optional)
            invoices: List of invoice dicts with keys:
                id, case_id, amount, date, status (draft/sent/paid/overdue),
                hours_covered (optional)
            cases: List of case dicts with keys:
                id, title, status (open/closed/archived), contact_id (optional),
                created_at (optional)

        Returns:
            BillingReport with anomalies, suggestions, and recommendations
        """
        # Build lookup structures
        case_map = {str(c.get("id", "")): c for c in cases}
        entries_by_case = self._group_entries_by_case(time_entries)
        invoices_by_case = self._group_invoices_by_case(invoices)

        # Calculate unbilled hours and amounts per case
        unbilled_by_case = self._calculate_unbilled_by_case(
            entries_by_case, invoices_by_case
        )

        # Total unbilled
        total_unbilled_hours = sum(v["hours"] for v in unbilled_by_case.values())
        total_unbilled_amount = sum(v["amount"] for v in unbilled_by_case.values())

        # Detect anomalies
        anomalies = self._detect_all_anomalies(
            time_entries, invoices, cases, entries_by_case, invoices_by_case, case_map
        )

        # Generate invoice suggestions
        invoice_suggestions = self.detect_unbilled_work(time_entries, invoices)

        # Enrich suggestions with case titles
        for suggestion in invoice_suggestions:
            case = case_map.get(suggestion.case_id)
            if case and not suggestion.case_title:
                suggestion.case_title = case.get("title", "")

        # Calculate monthly trend
        monthly_trend = self._calculate_monthly_trend(time_entries, invoices)

        # Calculate recovery rate
        recovery_rate = self.calculate_recovery_rate(time_entries, invoices)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            total_unbilled_hours,
            total_unbilled_amount,
            anomalies,
            invoice_suggestions,
            recovery_rate,
        )

        return BillingReport(
            total_unbilled_hours=round(total_unbilled_hours, 2),
            total_unbilled_amount=round(total_unbilled_amount, 2),
            anomalies=anomalies,
            invoice_suggestions=invoice_suggestions,
            monthly_trend=monthly_trend,
            recovery_rate=round(recovery_rate, 4),
            recommendations=recommendations,
        )

    def detect_unbilled_work(
        self,
        time_entries: list[dict],
        invoices: list[dict],
    ) -> list[InvoiceSuggestion]:
        """Detect unbilled work and generate invoice suggestions.

        Groups time entries by case, compares with issued invoices,
        and flags cases with significant unbilled work.

        Args:
            time_entries: List of time entry dicts
            invoices: List of invoice dicts

        Returns:
            List of InvoiceSuggestion sorted by urgency then amount
        """
        entries_by_case = self._group_entries_by_case(time_entries)
        invoices_by_case = self._group_invoices_by_case(invoices)

        now = datetime.now()
        suggestions: list[InvoiceSuggestion] = []

        for case_id, entries in entries_by_case.items():
            # Calculate total hours for this case
            total_hours = sum(_safe_float(e.get("hours")) for e in entries)

            # Calculate billed hours from invoices
            case_invoices = invoices_by_case.get(case_id, [])
            billed_hours = sum(
                _safe_float(inv.get("hours_covered")) for inv in case_invoices
            )

            # Also check if entries are individually marked as billed
            explicitly_billed_hours = sum(
                _safe_float(e.get("hours")) for e in entries if e.get("billed") is True
            )
            billed_hours = max(billed_hours, explicitly_billed_hours)

            unbilled_hours = max(total_hours - billed_hours, 0.0)

            if unbilled_hours < 1.0:
                continue

            # Estimate amount using average hourly rate from entries
            rates = [
                _safe_float(e.get("hourly_rate"))
                for e in entries
                if _safe_float(e.get("hourly_rate")) > 0
            ]
            avg_rate = sum(rates) / len(rates) if rates else DEFAULT_HOURLY_RATE
            estimated_amount = unbilled_hours * avg_rate

            # Find last invoice date
            last_invoice_date = None
            days_since = 0
            if case_invoices:
                invoice_dates = []
                for inv in case_invoices:
                    dt = _parse_datetime(inv.get("date"))
                    if dt:
                        invoice_dates.append(dt)
                if invoice_dates:
                    latest = max(invoice_dates)
                    last_invoice_date = latest.date().isoformat()
                    days_since = (now - latest).days

            # If no invoices at all, use earliest time entry date
            if not case_invoices:
                entry_dates = []
                for e in entries:
                    dt = _parse_datetime(e.get("date"))
                    if dt:
                        entry_dates.append(dt)
                if entry_dates:
                    days_since = (now - min(entry_dates)).days

            # Determine urgency
            urgency = "normal"
            if days_since > DAYS_WITHOUT_INVOICE_THRESHOLD and unbilled_hours > 5:
                urgency = "recommended"
            if (
                days_since > CRITICAL_OVERDUE_DAYS
                or unbilled_hours > UNBILLED_HOURS_THRESHOLD
            ):
                urgency = "overdue"

            suggestions.append(
                InvoiceSuggestion(
                    case_id=case_id,
                    case_title="",  # Will be enriched by caller
                    unbilled_hours=round(unbilled_hours, 2),
                    estimated_amount=round(estimated_amount, 2),
                    last_invoice_date=last_invoice_date,
                    days_since_last_invoice=days_since,
                    urgency=urgency,
                )
            )

        # Sort: overdue first, then recommended, then normal; within each by amount desc
        urgency_order = {"overdue": 0, "recommended": 1, "normal": 2}
        suggestions.sort(
            key=lambda s: (urgency_order.get(s.urgency, 2), -s.estimated_amount)
        )

        return suggestions

    def calculate_recovery_rate(
        self,
        time_entries: list[dict],
        invoices: list[dict],
    ) -> float:
        """Calculate the billing recovery rate.

        Recovery rate = billed hours / total worked hours.
        Belgian law firm target is typically >= 80%.

        Args:
            time_entries: List of time entry dicts
            invoices: List of invoice dicts

        Returns:
            Recovery rate as float between 0.0 and 1.0
        """
        total_hours = sum(_safe_float(e.get("hours")) for e in time_entries)
        if total_hours <= 0:
            return 0.0

        # Method 1: Sum hours_covered from invoices
        billed_from_invoices = sum(
            _safe_float(inv.get("hours_covered")) for inv in invoices
        )

        # Method 2: Sum hours from entries marked as billed
        billed_from_entries = sum(
            _safe_float(e.get("hours")) for e in time_entries if e.get("billed") is True
        )

        # Use the higher of the two methods
        billed_hours = max(billed_from_invoices, billed_from_entries)

        rate = billed_hours / total_hours
        return min(rate, 1.0)

    # ── Private helper methods ──

    def _group_entries_by_case(self, time_entries: list[dict]) -> dict[str, list[dict]]:
        """Group time entries by case_id."""
        groups: dict[str, list[dict]] = {}
        for entry in time_entries:
            case_id = str(entry.get("case_id", ""))
            if not case_id:
                continue
            groups.setdefault(case_id, []).append(entry)
        return groups

    def _group_invoices_by_case(self, invoices: list[dict]) -> dict[str, list[dict]]:
        """Group invoices by case_id."""
        groups: dict[str, list[dict]] = {}
        for inv in invoices:
            case_id = str(inv.get("case_id", ""))
            if not case_id:
                continue
            groups.setdefault(case_id, []).append(inv)
        return groups

    def _calculate_unbilled_by_case(
        self,
        entries_by_case: dict[str, list[dict]],
        invoices_by_case: dict[str, list[dict]],
    ) -> dict[str, dict]:
        """Calculate unbilled hours and estimated amount per case."""
        unbilled: dict[str, dict] = {}

        for case_id, entries in entries_by_case.items():
            total_hours = sum(_safe_float(e.get("hours")) for e in entries)

            case_invoices = invoices_by_case.get(case_id, [])
            billed_hours = sum(
                _safe_float(inv.get("hours_covered")) for inv in case_invoices
            )
            explicitly_billed = sum(
                _safe_float(e.get("hours")) for e in entries if e.get("billed") is True
            )
            billed_hours = max(billed_hours, explicitly_billed)

            unbilled_hours = max(total_hours - billed_hours, 0.0)

            # Estimate amount
            rates = [
                _safe_float(e.get("hourly_rate"))
                for e in entries
                if _safe_float(e.get("hourly_rate")) > 0
            ]
            avg_rate = sum(rates) / len(rates) if rates else DEFAULT_HOURLY_RATE
            estimated = unbilled_hours * avg_rate

            unbilled[case_id] = {
                "hours": unbilled_hours,
                "amount": estimated,
                "rate": avg_rate,
            }

        return unbilled

    def _detect_all_anomalies(
        self,
        time_entries: list[dict],
        invoices: list[dict],
        cases: list[dict],
        entries_by_case: dict[str, list[dict]],
        invoices_by_case: dict[str, list[dict]],
        case_map: dict[str, dict],
    ) -> list[BillingAnomaly]:
        """Detect all types of billing anomalies."""
        anomalies: list[BillingAnomaly] = []

        # 1. Unbilled time anomalies
        anomalies.extend(
            self._detect_unbilled_anomalies(entries_by_case, invoices_by_case, case_map)
        )

        # 2. Unusual hours anomalies
        anomalies.extend(self._detect_unusual_hours(time_entries, case_map))

        # 3. Missing rate anomalies
        anomalies.extend(self._detect_missing_rates(time_entries, case_map))

        # 4. Overdue invoice anomalies
        anomalies.extend(self._detect_overdue_invoices(invoices, case_map))

        # 5. Hours on closed cases
        anomalies.extend(self._detect_closed_case_entries(time_entries, case_map))

        # 6. No invoice with active work
        anomalies.extend(
            self._detect_stale_billing(entries_by_case, invoices_by_case, case_map)
        )

        # 7. Low recovery rate
        recovery = self.calculate_recovery_rate(time_entries, invoices)
        if recovery > 0 and recovery < RECOVERY_RATE_TARGET:
            anomalies.append(
                BillingAnomaly(
                    anomaly_type="low_recovery",
                    severity="high" if recovery < 0.60 else "medium",
                    description=(
                        f"Taux de recouvrement de {recovery:.0%} — "
                        f"en dessous de l'objectif de {RECOVERY_RATE_TARGET:.0%}"
                    ),
                    recommended_action=(
                        "Revoir les prestations non facturées et mettre à jour "
                        "la facturation. Envisager une revue mensuelle systématique."
                    ),
                )
            )

        return anomalies

    def _detect_unbilled_anomalies(
        self,
        entries_by_case: dict[str, list[dict]],
        invoices_by_case: dict[str, list[dict]],
        case_map: dict[str, dict],
    ) -> list[BillingAnomaly]:
        """Detect cases with significant unbilled time."""
        anomalies: list[BillingAnomaly] = []

        for case_id, entries in entries_by_case.items():
            total_hours = sum(_safe_float(e.get("hours")) for e in entries)

            case_invoices = invoices_by_case.get(case_id, [])
            billed_hours = sum(
                _safe_float(inv.get("hours_covered")) for inv in case_invoices
            )
            explicitly_billed = sum(
                _safe_float(e.get("hours")) for e in entries if e.get("billed") is True
            )
            billed_hours = max(billed_hours, explicitly_billed)

            unbilled = total_hours - billed_hours
            if unbilled > UNBILLED_HOURS_THRESHOLD:
                rates = [
                    _safe_float(e.get("hourly_rate"))
                    for e in entries
                    if _safe_float(e.get("hourly_rate")) > 0
                ]
                avg_rate = sum(rates) / len(rates) if rates else DEFAULT_HOURLY_RATE
                amount = unbilled * avg_rate

                case = case_map.get(case_id, {})
                case_title = case.get("title", case_id)

                severity = "high" if unbilled > 20 else "medium"

                anomalies.append(
                    BillingAnomaly(
                        anomaly_type="unbilled_time",
                        severity=severity,
                        description=(
                            f"{unbilled:.1f}h non facturées sur le dossier "
                            f"'{case_title}' (estimation: {amount:,.2f} EUR)"
                        ),
                        case_id=case_id,
                        amount_at_risk=round(amount, 2),
                        recommended_action=(
                            "Préparer et envoyer un état de frais pour les "
                            "prestations non facturées."
                        ),
                    )
                )

        return anomalies

    def _detect_unusual_hours(
        self,
        time_entries: list[dict],
        case_map: dict[str, dict],
    ) -> list[BillingAnomaly]:
        """Detect unusual working hours (weekends, excessive daily hours)."""
        anomalies: list[BillingAnomaly] = []

        # Group entries by (user_id, date) to detect daily totals
        daily_totals: dict[tuple[str, str], float] = {}
        daily_entries: dict[tuple[str, str], list[dict]] = {}

        for entry in time_entries:
            user_id = str(entry.get("user_id", "unknown"))
            dt = _parse_datetime(entry.get("date"))
            if not dt:
                continue
            date_str = dt.date().isoformat()
            key = (user_id, date_str)
            daily_totals[key] = daily_totals.get(key, 0.0) + _safe_float(
                entry.get("hours")
            )
            daily_entries.setdefault(key, []).append(entry)

        for (user_id, date_str), total_hours in daily_totals.items():
            # Check for excessive daily hours
            if total_hours > UNUSUAL_DAILY_HOURS:
                severity = (
                    "high" if total_hours > MAX_REASONABLE_DAILY_HOURS else "medium"
                )
                # Get case IDs for this day
                case_ids = {
                    str(e.get("case_id", ""))
                    for e in daily_entries[(user_id, date_str)]
                }
                case_ids_str = ", ".join(c for c in case_ids if c)

                anomalies.append(
                    BillingAnomaly(
                        anomaly_type="unusual_hours",
                        severity=severity,
                        description=(
                            f"{total_hours:.1f}h enregistrées le {date_str} "
                            f"(utilisateur: {user_id}) — "
                            f"dossiers: {case_ids_str}"
                        ),
                        recommended_action=(
                            "Vérifier les prestations de cette journée — "
                            "possible erreur de saisie."
                        ),
                    )
                )

            # Check for weekend work
            try:
                from datetime import date as date_cls

                parts = date_str.split("-")
                d = date_cls(int(parts[0]), int(parts[1]), int(parts[2]))
                if d.weekday() >= 5:  # Saturday or Sunday
                    day_name = "samedi" if d.weekday() == 5 else "dimanche"
                    anomalies.append(
                        BillingAnomaly(
                            anomaly_type="unusual_hours",
                            severity="low",
                            description=(
                                f"{total_hours:.1f}h enregistrées un {day_name} "
                                f"({date_str}, utilisateur: {user_id})"
                            ),
                            recommended_action=(
                                "Confirmer le travail le week-end et vérifier "
                                "la tarification applicable."
                            ),
                        )
                    )
            except (ValueError, IndexError):
                pass

        return anomalies

    def _detect_missing_rates(
        self,
        time_entries: list[dict],
        case_map: dict[str, dict],
    ) -> list[BillingAnomaly]:
        """Detect time entries without hourly rates."""
        missing_rate_entries: dict[str, int] = {}  # case_id -> count
        missing_rate_hours: dict[str, float] = {}  # case_id -> total hours

        for entry in time_entries:
            rate = _safe_float(entry.get("hourly_rate"))
            if rate <= 0:
                case_id = str(entry.get("case_id", "unknown"))
                missing_rate_entries[case_id] = missing_rate_entries.get(case_id, 0) + 1
                missing_rate_hours[case_id] = missing_rate_hours.get(
                    case_id, 0.0
                ) + _safe_float(entry.get("hours"))

        anomalies: list[BillingAnomaly] = []
        for case_id, count in missing_rate_entries.items():
            hours = missing_rate_hours[case_id]
            case = case_map.get(case_id, {})
            case_title = case.get("title", case_id)

            anomalies.append(
                BillingAnomaly(
                    anomaly_type="missing_rate",
                    severity="medium",
                    description=(
                        f"{count} prestation(s) sans taux horaire sur "
                        f"'{case_title}' ({hours:.1f}h)"
                    ),
                    case_id=case_id,
                    amount_at_risk=round(hours * DEFAULT_HOURLY_RATE, 2),
                    recommended_action=(
                        "Définir le taux horaire applicable pour ces prestations "
                        "avant facturation."
                    ),
                )
            )

        return anomalies

    def _detect_overdue_invoices(
        self,
        invoices: list[dict],
        case_map: dict[str, dict],
    ) -> list[BillingAnomaly]:
        """Detect overdue unpaid invoices."""
        anomalies: list[BillingAnomaly] = []
        now = datetime.now()

        for inv in invoices:
            status = str(inv.get("status", "")).lower()
            if status in ("paid", "cancelled", "draft"):
                continue

            inv_date = _parse_datetime(inv.get("date"))
            if not inv_date:
                continue

            days_old = (now - inv_date).days
            if days_old < OVERDUE_INVOICE_DAYS:
                continue

            amount = _safe_float(inv.get("amount"))
            case_id = str(inv.get("case_id", ""))
            case = case_map.get(case_id, {})
            case_title = case.get("title", case_id)

            severity = "high" if days_old > CRITICAL_OVERDUE_DAYS else "medium"

            anomalies.append(
                BillingAnomaly(
                    anomaly_type="overdue_invoice",
                    severity=severity,
                    description=(
                        f"Facture impayée depuis {days_old} jours sur "
                        f"'{case_title}' — montant: {amount:,.2f} EUR"
                    ),
                    case_id=case_id,
                    amount_at_risk=round(amount, 2),
                    recommended_action=(
                        "Envoyer un rappel de paiement. "
                        + (
                            "Envisager une mise en demeure."
                            if days_old > CRITICAL_OVERDUE_DAYS
                            else "Contacter le client."
                        )
                    ),
                )
            )

        return anomalies

    def _detect_closed_case_entries(
        self,
        time_entries: list[dict],
        case_map: dict[str, dict],
    ) -> list[BillingAnomaly]:
        """Detect time entries logged on closed/archived cases."""
        anomalies: list[BillingAnomaly] = []
        closed_case_hours: dict[str, float] = {}

        for entry in time_entries:
            case_id = str(entry.get("case_id", ""))
            case = case_map.get(case_id, {})
            status = str(case.get("status", "")).lower()

            if status in ("closed", "archived"):
                closed_case_hours[case_id] = closed_case_hours.get(
                    case_id, 0.0
                ) + _safe_float(entry.get("hours"))

        for case_id, hours in closed_case_hours.items():
            case = case_map.get(case_id, {})
            case_title = case.get("title", case_id)

            anomalies.append(
                BillingAnomaly(
                    anomaly_type="unusual_hours",
                    severity="medium",
                    description=(
                        f"{hours:.1f}h enregistrées sur le dossier clôturé "
                        f"'{case_title}'"
                    ),
                    case_id=case_id,
                    recommended_action=(
                        "Vérifier si le dossier doit être réouvert ou si les "
                        "prestations doivent être transférées."
                    ),
                )
            )

        return anomalies

    def _detect_stale_billing(
        self,
        entries_by_case: dict[str, list[dict]],
        invoices_by_case: dict[str, list[dict]],
        case_map: dict[str, dict],
    ) -> list[BillingAnomaly]:
        """Detect cases with active work but no recent invoice."""
        anomalies: list[BillingAnomaly] = []
        now = datetime.now()

        for case_id, entries in entries_by_case.items():
            # Check if there's recent work (within last 30 days)
            recent_work = False
            for entry in entries:
                dt = _parse_datetime(entry.get("date"))
                if dt and (now - dt).days <= DAYS_WITHOUT_INVOICE_THRESHOLD:
                    recent_work = True
                    break

            if not recent_work:
                continue

            # Check last invoice date
            case_invoices = invoices_by_case.get(case_id, [])
            if not case_invoices:
                # No invoices at all despite active work
                total_hours = sum(_safe_float(e.get("hours")) for e in entries)
                if total_hours > 5:
                    case = case_map.get(case_id, {})
                    case_title = case.get("title", case_id)
                    anomalies.append(
                        BillingAnomaly(
                            anomaly_type="unbilled_time",
                            severity="medium",
                            description=(
                                f"Aucune facture émise pour '{case_title}' "
                                f"malgré {total_hours:.1f}h de prestations"
                            ),
                            case_id=case_id,
                            recommended_action=(
                                "Évaluer la situation de facturation de ce "
                                "dossier et préparer un premier état de frais."
                            ),
                        )
                    )
                continue

            # Find most recent invoice date
            invoice_dates = []
            for inv in case_invoices:
                dt = _parse_datetime(inv.get("date"))
                if dt:
                    invoice_dates.append(dt)

            if not invoice_dates:
                continue

            latest_invoice = max(invoice_dates)
            days_since = (now - latest_invoice).days

            if days_since > DAYS_WITHOUT_INVOICE_THRESHOLD:
                # Calculate hours since last invoice
                hours_since = 0.0
                for entry in entries:
                    dt = _parse_datetime(entry.get("date"))
                    if dt and dt > latest_invoice:
                        hours_since += _safe_float(entry.get("hours"))

                if hours_since > 3:
                    case = case_map.get(case_id, {})
                    case_title = case.get("title", case_id)
                    anomalies.append(
                        BillingAnomaly(
                            anomaly_type="unbilled_time",
                            severity="low",
                            description=(
                                f"Dernière facture il y a {days_since} jours pour "
                                f"'{case_title}' avec {hours_since:.1f}h de "
                                f"nouvelles prestations"
                            ),
                            case_id=case_id,
                            recommended_action=(
                                "Préparer une facture intermédiaire pour les "
                                "prestations récentes."
                            ),
                        )
                    )

        return anomalies

    def _calculate_monthly_trend(
        self,
        time_entries: list[dict],
        invoices: list[dict],
    ) -> list[dict]:
        """Calculate monthly hours and billing amounts."""
        monthly: dict[str, dict] = {}  # "YYYY-MM" -> {hours, amount}

        # Aggregate hours by month
        for entry in time_entries:
            dt = _parse_datetime(entry.get("date"))
            if not dt:
                continue
            month_key = dt.strftime("%Y-%m")
            if month_key not in monthly:
                monthly[month_key] = {"month": month_key, "hours": 0.0, "amount": 0.0}
            monthly[month_key]["hours"] += _safe_float(entry.get("hours"))

        # Aggregate invoiced amounts by month
        for inv in invoices:
            dt = _parse_datetime(inv.get("date"))
            if not dt:
                continue
            month_key = dt.strftime("%Y-%m")
            if month_key not in monthly:
                monthly[month_key] = {"month": month_key, "hours": 0.0, "amount": 0.0}
            monthly[month_key]["amount"] += _safe_float(inv.get("amount"))

        # Round values and sort by month
        result = sorted(monthly.values(), key=lambda x: x["month"])
        for entry in result:
            entry["hours"] = round(entry["hours"], 2)
            entry["amount"] = round(entry["amount"], 2)

        return result

    def _generate_recommendations(
        self,
        total_unbilled_hours: float,
        total_unbilled_amount: float,
        anomalies: list[BillingAnomaly],
        suggestions: list[InvoiceSuggestion],
        recovery_rate: float,
    ) -> list[str]:
        """Generate actionable billing recommendations."""
        recommendations: list[str] = []

        # Unbilled work
        if total_unbilled_hours > 20:
            recommendations.append(
                f"Facturation prioritaire: {total_unbilled_hours:.0f}h non facturées "
                f"représentant environ {total_unbilled_amount:,.0f} EUR. "
                "Planifier une session de facturation dans la semaine."
            )

        # Overdue suggestions
        overdue = [s for s in suggestions if s.urgency == "overdue"]
        if overdue:
            recommendations.append(
                f"{len(overdue)} dossier(s) nécessitent une facturation urgente. "
                "Prioriser ces dossiers immédiatement."
            )

        # Recovery rate
        if 0 < recovery_rate < RECOVERY_RATE_TARGET:
            gap = RECOVERY_RATE_TARGET - recovery_rate
            recommendations.append(
                f"Le taux de recouvrement ({recovery_rate:.0%}) est {gap:.0%} "
                f"en dessous de l'objectif de {RECOVERY_RATE_TARGET:.0%}. "
                "Revoir les processus de facturation et de suivi."
            )

        # Missing rates
        missing_rate_anomalies = [
            a for a in anomalies if a.anomaly_type == "missing_rate"
        ]
        if missing_rate_anomalies:
            total_risk = sum(a.amount_at_risk for a in missing_rate_anomalies)
            recommendations.append(
                f"{len(missing_rate_anomalies)} dossier(s) avec des prestations "
                f"sans taux horaire ({total_risk:,.0f} EUR à risque). "
                "Mettre à jour les taux avant la prochaine facturation."
            )

        # Overdue invoices
        overdue_inv = [a for a in anomalies if a.anomaly_type == "overdue_invoice"]
        if overdue_inv:
            total_overdue = sum(a.amount_at_risk for a in overdue_inv)
            recommendations.append(
                f"{len(overdue_inv)} facture(s) impayée(s) totalisant "
                f"{total_overdue:,.0f} EUR. Mettre en place un suivi de "
                "relance systématique."
            )

        # Weekend work
        weekend_anomalies = [
            a
            for a in anomalies
            if a.anomaly_type == "unusual_hours"
            and ("samedi" in a.description or "dimanche" in a.description)
        ]
        if len(weekend_anomalies) > 3:
            recommendations.append(
                "Travail fréquent le week-end détecté. Vérifier la charge "
                "de travail et la facturation majorée le cas échéant."
            )

        # General: if no issues found
        if not recommendations:
            recommendations.append(
                "La facturation est à jour. Continuer le suivi mensuel régulier."
            )

        return recommendations
