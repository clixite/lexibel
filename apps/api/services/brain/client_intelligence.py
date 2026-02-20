"""Client Intelligence — Smart client relationship analysis.

Tracks client engagement, identifies at-risk relationships,
suggests follow-up actions, and monitors satisfaction signals.
Designed for Belgian legal practice relationship management.
"""

from dataclasses import dataclass, field
from datetime import datetime


# ── Data classes ──


@dataclass
class ClientHealth:
    """Health assessment of client relationship."""

    contact_id: str
    contact_name: str
    health_score: int  # 0-100
    status: str  # healthy, needs_attention, at_risk, critical
    last_contact_date: str | None = None
    days_since_contact: int = 0
    active_cases: int = 0
    total_billed: float = 0.0
    outstanding_amount: float = 0.0
    communication_frequency: str = "normal"  # frequent, normal, sparse, absent
    risk_factors: list[str] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)


@dataclass
class FollowUpSuggestion:
    """A suggested follow-up action for a client."""

    contact_id: str
    contact_name: str
    urgency: str  # immediate, soon, routine
    reason: str
    suggested_action: str
    case_id: str | None = None
    case_title: str | None = None


# ── Thresholds and configuration ──

# Communication thresholds (days)
COMMUNICATION_FREQUENT_DAYS = 7  # Contact within last 7 days
COMMUNICATION_NORMAL_DAYS = 14  # Contact within 14 days
COMMUNICATION_SPARSE_DAYS = 30  # Contact within 30 days
# Beyond 30 days = absent

# Health score weights
WEIGHT_COMMUNICATION = 30  # Max 30 points for communication recency
WEIGHT_ACTIVE_CASES = 20  # Max 20 points for active engagement
WEIGHT_BILLING_HEALTH = 25  # Max 25 points for billing relationship
WEIGHT_RESPONSIVENESS = 15  # Max 15 points for client responsiveness
WEIGHT_LONGEVITY = 10  # Max 10 points for relationship length

# Risk thresholds
DAYS_NO_CONTACT_WARNING = 14
DAYS_NO_CONTACT_RISK = 30
DAYS_NO_CONTACT_CRITICAL = 60
OUTSTANDING_AMOUNT_WARNING = 1000.0  # EUR
OUTSTANDING_AMOUNT_CRITICAL = 5000.0  # EUR
UNPAID_RATIO_WARNING = 0.30  # 30% of total billed is unpaid


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


def _safe_float(value: object, default: float = 0.0) -> float:
    """Safely convert a value to float."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _days_between(dt: datetime, now: datetime) -> int:
    """Calculate days between two datetimes, always non-negative."""
    delta = now - dt
    return max(int(delta.total_seconds() / 86400), 0)


class ClientIntelligence:
    """Smart client relationship analysis for Belgian law firms.

    Assesses client health, identifies at-risk relationships,
    and generates follow-up suggestions. All data is passed in —
    no database dependencies.
    """

    def assess_client_health(
        self,
        contact: dict,
        cases: list[dict],
        communications: list[dict],
        time_entries: list[dict],
    ) -> ClientHealth:
        """Assess the health of a client relationship.

        Calculates an engagement score, tracks communication recency,
        monitors the billing relationship, and identifies risk factors.

        Args:
            contact: Contact dict with keys:
                id, name, email (optional), phone (optional),
                created_at (optional), type (optional: person/organization)
            cases: List of case dicts for this contact with keys:
                id, title, status (open/closed/archived),
                created_at (optional), updated_at (optional)
            communications: List of communication dicts with keys:
                id, contact_id, date, direction (inbound/outbound),
                type (email/call/meeting/letter), subject (optional)
            time_entries: List of time entry dicts linked to contact's cases:
                id, case_id, hours, date, hourly_rate (optional),
                billed (bool, optional)

        Returns:
            ClientHealth with score, status, risk factors, and recommendations
        """
        now = datetime.now()
        contact_id = str(contact.get("id", ""))
        contact_name = str(contact.get("name", "Unknown"))

        # ── Communication analysis ──
        comm_score, last_contact_date, days_since, comm_frequency = (
            self._analyze_communications(communications, now)
        )

        # ── Case engagement analysis ──
        case_score, active_cases = self._analyze_case_engagement(cases, now)

        # ── Billing health analysis ──
        billing_score, total_billed, outstanding = self._analyze_billing(
            time_entries, cases
        )

        # ── Responsiveness analysis ──
        responsiveness_score = self._analyze_responsiveness(communications, now)

        # ── Longevity analysis ──
        longevity_score = self._analyze_longevity(contact, cases, now)

        # ── Calculate overall health score ──
        health_score = (
            comm_score
            + case_score
            + billing_score
            + responsiveness_score
            + longevity_score
        )
        health_score = max(0, min(100, health_score))

        # ── Determine status ──
        status = self._determine_status(health_score, days_since, outstanding)

        # ── Identify risk factors ──
        risk_factors = self._identify_risk_factors(
            days_since,
            active_cases,
            total_billed,
            outstanding,
            comm_frequency,
            cases,
            communications,
            now,
        )

        # ── Generate recommended actions ──
        recommended_actions = self._generate_client_actions(
            status,
            risk_factors,
            days_since,
            active_cases,
            outstanding,
            comm_frequency,
            contact_name,
        )

        return ClientHealth(
            contact_id=contact_id,
            contact_name=contact_name,
            health_score=health_score,
            status=status,
            last_contact_date=last_contact_date,
            days_since_contact=days_since,
            active_cases=active_cases,
            total_billed=round(total_billed, 2),
            outstanding_amount=round(outstanding, 2),
            communication_frequency=comm_frequency,
            risk_factors=risk_factors,
            recommended_actions=recommended_actions,
        )

    def get_follow_up_suggestions(
        self,
        contacts: list[dict],
        cases: list[dict],
        communications: list[dict],
    ) -> list[FollowUpSuggestion]:
        """Generate follow-up suggestions across all clients.

        Identifies clients needing attention and suggests specific
        actions, prioritized by urgency.

        Args:
            contacts: List of contact dicts (see assess_client_health)
            cases: List of all case dicts with contact_id field
            communications: List of all communication dicts with contact_id

        Returns:
            List of FollowUpSuggestion sorted by urgency
        """
        now = datetime.now()
        suggestions: list[FollowUpSuggestion] = []

        # Build lookup structures
        cases_by_contact = self._group_by_contact(cases)
        comms_by_contact = self._group_by_contact(communications)

        for contact in contacts:
            contact_id = str(contact.get("id", ""))
            contact_name = str(contact.get("name", "Unknown"))

            contact_cases = cases_by_contact.get(contact_id, [])
            contact_comms = comms_by_contact.get(contact_id, [])

            # Generate suggestions for this contact
            contact_suggestions = self._suggest_for_contact(
                contact_id, contact_name, contact_cases, contact_comms, now
            )
            suggestions.extend(contact_suggestions)

        # Sort by urgency: immediate > soon > routine
        urgency_order = {"immediate": 0, "soon": 1, "routine": 2}
        suggestions.sort(key=lambda s: urgency_order.get(s.urgency, 2))

        return suggestions

    # ── Private analysis methods ──

    def _analyze_communications(
        self,
        communications: list[dict],
        now: datetime,
    ) -> tuple[int, str | None, int, str]:
        """Analyze communication patterns and recency.

        Returns:
            (score, last_contact_date_str, days_since_contact, frequency)
        """
        if not communications:
            return 0, None, 999, "absent"

        # Find most recent communication
        comm_dates: list[datetime] = []
        for comm in communications:
            dt = _parse_datetime(comm.get("date"))
            if dt:
                comm_dates.append(dt)

        if not comm_dates:
            return 0, None, 999, "absent"

        latest = max(comm_dates)
        last_contact_date = latest.date().isoformat()
        days_since = _days_between(latest, now)

        # Determine frequency
        if days_since <= COMMUNICATION_FREQUENT_DAYS:
            frequency = "frequent"
        elif days_since <= COMMUNICATION_NORMAL_DAYS:
            frequency = "normal"
        elif days_since <= COMMUNICATION_SPARSE_DAYS:
            frequency = "sparse"
        else:
            frequency = "absent"

        # Calculate communication score (max WEIGHT_COMMUNICATION)
        if days_since <= COMMUNICATION_FREQUENT_DAYS:
            score = WEIGHT_COMMUNICATION
        elif days_since <= COMMUNICATION_NORMAL_DAYS:
            score = int(WEIGHT_COMMUNICATION * 0.8)
        elif days_since <= COMMUNICATION_SPARSE_DAYS:
            score = int(WEIGHT_COMMUNICATION * 0.5)
        elif days_since <= DAYS_NO_CONTACT_CRITICAL:
            score = int(WEIGHT_COMMUNICATION * 0.2)
        else:
            score = 0

        # Bonus for volume of recent communications
        recent_count = sum(1 for dt in comm_dates if _days_between(dt, now) <= 30)
        if recent_count >= 5:
            score = min(score + 5, WEIGHT_COMMUNICATION)

        return score, last_contact_date, days_since, frequency

    def _analyze_case_engagement(
        self,
        cases: list[dict],
        now: datetime,
    ) -> tuple[int, int]:
        """Analyze case engagement for a client.

        Returns:
            (score, active_case_count)
        """
        if not cases:
            return 0, 0

        active = [
            c
            for c in cases
            if str(c.get("status", "")).lower() in ("open", "active", "pending")
        ]
        active_count = len(active)

        # Score based on active cases (max WEIGHT_ACTIVE_CASES)
        if active_count >= 3:
            score = WEIGHT_ACTIVE_CASES
        elif active_count == 2:
            score = int(WEIGHT_ACTIVE_CASES * 0.8)
        elif active_count == 1:
            score = int(WEIGHT_ACTIVE_CASES * 0.6)
        else:
            # No active cases but has recent closed cases
            recently_closed = 0
            for c in cases:
                if str(c.get("status", "")).lower() in ("closed", "archived"):
                    updated = _parse_datetime(c.get("updated_at"))
                    if updated and _days_between(updated, now) <= 90:
                        recently_closed += 1
            if recently_closed > 0:
                score = int(WEIGHT_ACTIVE_CASES * 0.3)
            else:
                score = 0

        return score, active_count

    def _analyze_billing(
        self,
        time_entries: list[dict],
        cases: list[dict],
    ) -> tuple[int, float, float]:
        """Analyze billing health for a client.

        Returns:
            (score, total_billed, outstanding_amount)
        """
        total_billed = 0.0
        total_hours = 0.0

        for entry in time_entries:
            hours = _safe_float(entry.get("hours"))
            rate = _safe_float(entry.get("hourly_rate"))
            total_hours += hours
            if entry.get("billed") is True and rate > 0:
                total_billed += hours * rate

        # If no hourly rates, estimate
        if total_billed == 0 and total_hours > 0:
            billed_entries = [e for e in time_entries if e.get("billed") is True]
            total_billed = (
                sum(_safe_float(e.get("hours")) for e in billed_entries) * 150.0
            )

        # Estimate outstanding (unbilled work)
        unbilled_hours = sum(
            _safe_float(e.get("hours"))
            for e in time_entries
            if e.get("billed") is not True
        )
        # Use average rate or default
        rates = [
            _safe_float(e.get("hourly_rate"))
            for e in time_entries
            if _safe_float(e.get("hourly_rate")) > 0
        ]
        avg_rate = sum(rates) / len(rates) if rates else 150.0
        outstanding = unbilled_hours * avg_rate

        # Score based on billing health (max WEIGHT_BILLING_HEALTH)
        score = WEIGHT_BILLING_HEALTH  # Start at full

        # Deduct for high outstanding ratio
        if total_billed > 0:
            unpaid_ratio = outstanding / (total_billed + outstanding)
            if unpaid_ratio > UNPAID_RATIO_WARNING:
                score -= int(WEIGHT_BILLING_HEALTH * 0.3)
            if unpaid_ratio > 0.50:
                score -= int(WEIGHT_BILLING_HEALTH * 0.3)
        elif outstanding > 0:
            # Only outstanding, no billed — concerning
            score = int(WEIGHT_BILLING_HEALTH * 0.3)

        # Deduct for very high outstanding amounts
        if outstanding > OUTSTANDING_AMOUNT_CRITICAL:
            score -= int(WEIGHT_BILLING_HEALTH * 0.2)
        elif outstanding > OUTSTANDING_AMOUNT_WARNING:
            score -= int(WEIGHT_BILLING_HEALTH * 0.1)

        score = max(0, score)

        return score, total_billed, outstanding

    def _analyze_responsiveness(
        self,
        communications: list[dict],
        now: datetime,
    ) -> int:
        """Analyze client responsiveness based on communication patterns.

        Returns:
            Score (max WEIGHT_RESPONSIVENESS)
        """
        if not communications:
            return 0

        # Check ratio of inbound (from client) vs outbound (to client)
        inbound = [
            c
            for c in communications
            if str(c.get("direction", "")).lower() == "inbound"
        ]
        outbound = [
            c
            for c in communications
            if str(c.get("direction", "")).lower() == "outbound"
        ]

        total = len(inbound) + len(outbound)
        if total == 0:
            return int(WEIGHT_RESPONSIVENESS * 0.5)

        # Ideal ratio is roughly balanced (40-60% inbound)
        inbound_ratio = len(inbound) / total

        if 0.3 <= inbound_ratio <= 0.7:
            score = WEIGHT_RESPONSIVENESS  # Good two-way communication
        elif 0.1 <= inbound_ratio < 0.3:
            score = int(WEIGHT_RESPONSIVENESS * 0.6)  # Client less responsive
        elif inbound_ratio < 0.1:
            score = int(WEIGHT_RESPONSIVENESS * 0.2)  # Client barely responds
        else:
            # Client sends a lot — could be needy but engaged
            score = int(WEIGHT_RESPONSIVENESS * 0.8)

        # Check for recent inbound communication (last 14 days)
        recent_inbound = [
            c
            for c in inbound
            if _parse_datetime(c.get("date"))
            and _days_between(_parse_datetime(c.get("date")), now) <= 14  # type: ignore[arg-type]
        ]
        if recent_inbound:
            score = min(score + 3, WEIGHT_RESPONSIVENESS)

        return score

    def _analyze_longevity(
        self,
        contact: dict,
        cases: list[dict],
        now: datetime,
    ) -> int:
        """Analyze relationship longevity.

        Returns:
            Score (max WEIGHT_LONGEVITY)
        """
        # Try to determine relationship start
        earliest = None

        # From contact creation date
        created = _parse_datetime(contact.get("created_at"))
        if created:
            earliest = created

        # From earliest case
        for case in cases:
            case_created = _parse_datetime(case.get("created_at"))
            if case_created:
                if earliest is None or case_created < earliest:
                    earliest = case_created

        if earliest is None:
            return int(WEIGHT_LONGEVITY * 0.5)  # Unknown, give middle score

        months = _days_between(earliest, now) / 30

        if months >= 24:
            return WEIGHT_LONGEVITY  # 2+ years
        elif months >= 12:
            return int(WEIGHT_LONGEVITY * 0.8)  # 1+ year
        elif months >= 6:
            return int(WEIGHT_LONGEVITY * 0.6)  # 6+ months
        elif months >= 3:
            return int(WEIGHT_LONGEVITY * 0.4)  # 3+ months
        else:
            return int(WEIGHT_LONGEVITY * 0.2)  # New client

    def _determine_status(
        self,
        health_score: int,
        days_since_contact: int,
        outstanding: float,
    ) -> str:
        """Determine overall client relationship status."""
        # Critical: very low score or very long silence
        if health_score < 25 or days_since_contact > DAYS_NO_CONTACT_CRITICAL:
            return "critical"

        # At risk: low score, long silence, or high outstanding
        if (
            health_score < 45
            or days_since_contact > DAYS_NO_CONTACT_RISK
            or outstanding > OUTSTANDING_AMOUNT_CRITICAL
        ):
            return "at_risk"

        # Needs attention
        if (
            health_score < 65
            or days_since_contact > DAYS_NO_CONTACT_WARNING
            or outstanding > OUTSTANDING_AMOUNT_WARNING
        ):
            return "needs_attention"

        return "healthy"

    def _identify_risk_factors(
        self,
        days_since: int,
        active_cases: int,
        total_billed: float,
        outstanding: float,
        comm_frequency: str,
        cases: list[dict],
        communications: list[dict],
        now: datetime,
    ) -> list[str]:
        """Identify specific risk factors for a client relationship."""
        risks: list[str] = []

        # Communication risks
        if days_since > DAYS_NO_CONTACT_CRITICAL:
            risks.append(
                f"Aucun contact depuis {days_since} jours — relation en danger"
            )
        elif days_since > DAYS_NO_CONTACT_RISK:
            risks.append(f"Aucun contact depuis {days_since} jours — suivi nécessaire")
        elif days_since > DAYS_NO_CONTACT_WARNING:
            risks.append(f"Dernier contact il y a {days_since} jours")

        # No active cases
        if active_cases == 0:
            # Check if there were recent cases
            has_recent_case = False
            for case in cases:
                updated = _parse_datetime(case.get("updated_at"))
                if updated and _days_between(updated, now) <= 180:
                    has_recent_case = True
                    break
            if has_recent_case:
                risks.append("Aucun dossier actif — client potentiellement inactif")
            else:
                risks.append(
                    "Aucun dossier actif depuis plus de 6 mois — relation dormante"
                )

        # Billing risks
        if outstanding > OUTSTANDING_AMOUNT_CRITICAL:
            risks.append(f"Montant impayé élevé: {outstanding:,.2f} EUR")
        elif outstanding > OUTSTANDING_AMOUNT_WARNING:
            risks.append(f"Montant impayé en attente: {outstanding:,.2f} EUR")

        if total_billed > 0:
            unpaid_ratio = outstanding / (total_billed + outstanding)
            if unpaid_ratio > UNPAID_RATIO_WARNING:
                risks.append(
                    f"Taux d'impayé de {unpaid_ratio:.0%} — risque de recouvrement"
                )

        # Communication pattern risks
        if comm_frequency == "absent":
            risks.append("Communication absente — le client ne répond plus")
        elif comm_frequency == "sparse":
            risks.append("Communication rare — engagement faible")

        # Check for one-way communication (only outbound)
        if communications:
            inbound = [
                c
                for c in communications
                if str(c.get("direction", "")).lower() == "inbound"
            ]
            outbound = [
                c
                for c in communications
                if str(c.get("direction", "")).lower() == "outbound"
            ]
            if outbound and not inbound:
                risks.append("Communication unilatérale — le client n'a jamais répondu")
            elif len(outbound) > 3 * max(len(inbound), 1):
                risks.append(
                    "Déséquilibre de communication — peu de réponses du client"
                )

        return risks

    def _generate_client_actions(
        self,
        status: str,
        risk_factors: list[str],
        days_since: int,
        active_cases: int,
        outstanding: float,
        comm_frequency: str,
        contact_name: str,
    ) -> list[str]:
        """Generate recommended actions for a client relationship."""
        actions: list[str] = []

        # Status-based actions
        if status == "critical":
            actions.append(
                f"URGENT: Planifier un appel avec {contact_name} cette semaine"
            )
            if outstanding > OUTSTANDING_AMOUNT_WARNING:
                actions.append("Évaluer la situation des impayés avant tout contact")

        elif status == "at_risk":
            actions.append(
                f"Planifier une prise de contact avec {contact_name} "
                "dans les 7 prochains jours"
            )

        elif status == "needs_attention":
            actions.append(f"Envoyer un message de suivi à {contact_name}")

        # Communication actions
        if comm_frequency == "absent" and days_since > DAYS_NO_CONTACT_RISK:
            actions.append(
                "Envoyer un courrier/email de courtoisie pour reprendre contact"
            )

        # Case-related actions
        if active_cases == 0:
            actions.append(
                "Proposer un rendez-vous de bilan ou un service complémentaire"
            )

        # Billing actions
        if outstanding > OUTSTANDING_AMOUNT_CRITICAL:
            actions.append(
                f"Résoudre les impayés ({outstanding:,.0f} EUR) avant "
                "nouvelle prestation"
            )
        elif outstanding > OUTSTANDING_AMOUNT_WARNING:
            actions.append(
                "Envoyer un rappel courtois concernant les factures en attente"
            )

        # General maintenance
        if status == "healthy" and not actions:
            actions.append("Relation saine — maintenir le rythme de contact actuel")

        return actions

    def _suggest_for_contact(
        self,
        contact_id: str,
        contact_name: str,
        cases: list[dict],
        communications: list[dict],
        now: datetime,
    ) -> list[FollowUpSuggestion]:
        """Generate follow-up suggestions for a specific contact."""
        suggestions: list[FollowUpSuggestion] = []

        # 1. Check communication recency
        latest_comm = None
        for comm in communications:
            dt = _parse_datetime(comm.get("date"))
            if dt and (latest_comm is None or dt > latest_comm):
                latest_comm = dt

        days_since = _days_between(latest_comm, now) if latest_comm else 999

        # No contact in critical period
        if days_since > DAYS_NO_CONTACT_CRITICAL:
            suggestions.append(
                FollowUpSuggestion(
                    contact_id=contact_id,
                    contact_name=contact_name,
                    urgency="immediate",
                    reason=(
                        f"Aucun contact depuis {days_since} jours — relation en danger"
                    ),
                    suggested_action=(
                        "Appeler le client ou envoyer un courrier personnel "
                        "pour reprendre contact"
                    ),
                )
            )
        elif days_since > DAYS_NO_CONTACT_RISK:
            suggestions.append(
                FollowUpSuggestion(
                    contact_id=contact_id,
                    contact_name=contact_name,
                    urgency="soon",
                    reason=f"Dernier contact il y a {days_since} jours",
                    suggested_action=(
                        "Envoyer un email de suivi ou proposer un point téléphonique"
                    ),
                )
            )
        elif days_since > DAYS_NO_CONTACT_WARNING:
            suggestions.append(
                FollowUpSuggestion(
                    contact_id=contact_id,
                    contact_name=contact_name,
                    urgency="routine",
                    reason=f"Dernier contact il y a {days_since} jours",
                    suggested_action="Envoyer un message de suivi courtois",
                )
            )

        # 2. Check for cases needing updates
        active_cases = [
            c
            for c in cases
            if str(c.get("status", "")).lower() in ("open", "active", "pending")
        ]

        for case in active_cases:
            case_updated = _parse_datetime(case.get("updated_at"))
            if case_updated:
                days_since_update = _days_between(case_updated, now)
                case_id = str(case.get("id", ""))
                case_title = str(case.get("title", ""))

                if days_since_update > 21:
                    suggestions.append(
                        FollowUpSuggestion(
                            contact_id=contact_id,
                            contact_name=contact_name,
                            urgency="soon" if days_since_update > 30 else "routine",
                            reason=(
                                f"Dossier '{case_title}' sans mise à jour "
                                f"depuis {days_since_update} jours"
                            ),
                            suggested_action=(
                                "Envoyer un état d'avancement au client pour ce dossier"
                            ),
                            case_id=case_id,
                            case_title=case_title,
                        )
                    )

        # 3. Check for unanswered outbound communications
        recent_outbound = [
            c
            for c in communications
            if str(c.get("direction", "")).lower() == "outbound"
            and _parse_datetime(c.get("date"))
            and _days_between(
                _parse_datetime(c.get("date")),
                now,  # type: ignore[arg-type]
            )
            <= 14
        ]
        recent_inbound = [
            c
            for c in communications
            if str(c.get("direction", "")).lower() == "inbound"
            and _parse_datetime(c.get("date"))
            and _days_between(
                _parse_datetime(c.get("date")),
                now,  # type: ignore[arg-type]
            )
            <= 14
        ]

        if len(recent_outbound) >= 2 and len(recent_inbound) == 0:
            suggestions.append(
                FollowUpSuggestion(
                    contact_id=contact_id,
                    contact_name=contact_name,
                    urgency="soon",
                    reason=(
                        f"{len(recent_outbound)} messages envoyés sans réponse "
                        "dans les 14 derniers jours"
                    ),
                    suggested_action=(
                        "Relancer par téléphone — le client ne répond peut-être "
                        "pas aux emails"
                    ),
                )
            )

        # 4. Check for completed cases without follow-up
        recently_closed = [
            c
            for c in cases
            if str(c.get("status", "")).lower() in ("closed", "archived")
            and _parse_datetime(c.get("updated_at"))
            and _days_between(
                _parse_datetime(c.get("updated_at")),
                now,  # type: ignore[arg-type]
            )
            <= 30
        ]

        if recently_closed and not active_cases:
            case = recently_closed[0]
            suggestions.append(
                FollowUpSuggestion(
                    contact_id=contact_id,
                    contact_name=contact_name,
                    urgency="routine",
                    reason=(
                        f"Dossier '{case.get('title', '')}' récemment clôturé — "
                        "aucun dossier actif restant"
                    ),
                    suggested_action=(
                        "Envoyer un courrier de satisfaction et proposer un "
                        "rendez-vous de bilan"
                    ),
                    case_id=str(case.get("id", "")),
                    case_title=str(case.get("title", "")),
                )
            )

        return suggestions

    def _group_by_contact(self, items: list[dict]) -> dict[str, list[dict]]:
        """Group items by contact_id."""
        groups: dict[str, list[dict]] = {}
        for item in items:
            contact_id = str(item.get("contact_id", ""))
            if not contact_id:
                continue
            groups.setdefault(contact_id, []).append(item)
        return groups
