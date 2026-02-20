"""Communication Intelligence — Email and call analysis with urgency scoring.

Analyzes communication patterns, scores urgency, detects sentiment shifts,
and identifies cases needing attention based on communication history.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class PartyContact:
    """Communication status for a single party."""

    contact_id: str
    contact_name: str
    role: str  # client, adverse, witness, third_party
    last_contact_date: date | None
    days_since_contact: int | None
    total_emails: int
    total_calls: int
    avg_response_hours: float | None
    status: str  # active, warning, critical, no_contact


@dataclass
class CommunicationGap:
    """Identified communication gap."""

    contact_name: str
    role: str
    days_since_contact: int
    severity: str  # low, medium, high, critical
    recommendation: str


@dataclass
class CommunicationHealth:
    """Overall communication health assessment for a case."""

    case_id: str
    overall_score: float  # 0-100
    status: str  # healthy, warning, critical
    parties: list[PartyContact] = field(default_factory=list)
    gaps: list[CommunicationGap] = field(default_factory=list)
    total_emails: int = 0
    total_calls: int = 0
    avg_response_hours: float | None = None
    summary: str = ""


@dataclass
class UrgencyIndicator:
    """A single urgency indicator found in a communication."""

    keyword: str
    category: str  # critical, urgent, normal
    context: str  # Surrounding text snippet


@dataclass
class UrgencyScore:
    """Urgency assessment for a single communication."""

    score: float  # 0-100
    category: str  # low, medium, high, critical
    indicators: list[UrgencyIndicator] = field(default_factory=list)
    explanation: str = ""


@dataclass
class SentimentMoment:
    """A point in time with a sentiment reading."""

    date: date
    sentiment: str  # positive, neutral, negative, hostile
    score: float  # -1.0 (hostile) to 1.0 (positive)
    excerpt: str = ""


@dataclass
class SentimentTrend:
    """Sentiment trend analysis over time."""

    trend: str  # improving, stable, deteriorating
    alert_level: str  # none, low, medium, high
    current_sentiment: str  # positive, neutral, negative, hostile
    moments: list[SentimentMoment] = field(default_factory=list)
    key_moments: list[SentimentMoment] = field(default_factory=list)
    summary: str = ""


# ---------------------------------------------------------------------------
# Urgency keyword definitions — French legal terminology
# ---------------------------------------------------------------------------

URGENCY_KEYWORDS: dict[str, list[str]] = {
    "critical": [
        "saisie",
        "saisie-arrêt",
        "saisie conservatoire",
        "expulsion",
        "détention",
        "mandat d'arrêt",
        "mandat de perquisition",
        "garde à vue",
        "privation de liberté",
        "mesure d'urgence",
        "extrême urgence",
        "référé",
        "unilatéral",
        "ordonnance sur requête",
    ],
    "urgent": [
        "mise en demeure",
        "délai",
        "urgence",
        "dernier délai",
        "injonction",
        "sommation",
        "astreinte",
        "exécution provisoire",
        "date limite",
        "impératif",
        "sous peine de",
        "forclusion",
        "péremption",
        "prescription",
        "imminent",
        "sans délai",
    ],
    "attention": [
        "rappel",
        "relance",
        "en attente",
        "réponse attendue",
        "suite à donner",
        "à votre attention",
        "prière de",
        "nous vous prions",
        "veuillez",
        "dans les meilleurs délais",
    ],
}

# Sentiment keywords — French
SENTIMENT_KEYWORDS: dict[str, list[str]] = {
    "positive": [
        "accord",
        "accepté",
        "favorable",
        "satisfait",
        "remercie",
        "remercions",
        "excellent",
        "bonne nouvelle",
        "résolu",
        "arrangement",
        "conciliation",
        "entente",
        "compromis",
    ],
    "neutral": [
        "information",
        "demande",
        "suite à",
        "concernant",
        "référence",
        "objet",
        "pièce jointe",
        "ci-joint",
        "veuillez trouver",
    ],
    "negative": [
        "refus",
        "refusé",
        "désaccord",
        "contestation",
        "insatisfait",
        "plainte",
        "réclamation",
        "problème",
        "difficulté",
        "retard",
        "manquement",
        "défaut",
    ],
    "hostile": [
        "menace",
        "menaçant",
        "agression",
        "intimidation",
        "harcèlement",
        "injure",
        "diffamation",
        "calomnie",
        "mise en cause",
        "poursuites",
        "dommages-intérêts",
        "responsabilité",
    ],
}

# Communication gap thresholds (days)
GAP_THRESHOLDS = {
    "client": {"warning": 7, "critical": 14},
    "adverse": {"warning": 14, "critical": 30},
    "witness": {"warning": 21, "critical": 45},
    "third_party": {"warning": 14, "critical": 30},
}


# ---------------------------------------------------------------------------
# CommunicationScorer
# ---------------------------------------------------------------------------


class CommunicationScorer:
    """Communication intelligence engine for legal practice.

    Analyzes email and call patterns, scores urgency of incoming
    communications, detects sentiment shifts in correspondence,
    and identifies cases that need attention due to communication gaps.
    """

    # ------------------------------------------------------------------
    # Communication Health
    # ------------------------------------------------------------------

    def score_communication_health(
        self,
        case_id: str,
        emails: list[dict[str, Any]],
        calls: list[dict[str, Any]],
        contacts: list[dict[str, Any]],
    ) -> CommunicationHealth:
        """Score the overall communication health of a case.

        Evaluates communication frequency, response times, and gaps
        for each party involved in the case.

        Args:
            case_id: UUID of the case.
            emails: List of email dicts with from_address, received_at, etc.
            calls: List of call dicts with caller_number, started_at, etc.
            contacts: List of contact dicts with role, email, phone, etc.

        Returns:
            CommunicationHealth with per-party breakdown and gap analysis.
        """
        today = date.today()
        parties: list[PartyContact] = []
        gaps: list[CommunicationGap] = []

        total_emails = len(emails)
        total_calls = len(calls)

        # Build per-contact communication profiles
        for contact in contacts:
            contact_id = str(contact.get("contact_id", contact.get("id", "")))
            contact_name = contact.get("full_name", contact.get("name", "Inconnu"))
            role = contact.get("role", "third_party")
            contact_email = (contact.get("email") or "").lower()
            contact_phone = contact.get("phone_e164", "")

            # Find emails to/from this contact
            contact_emails = self._filter_emails_for_contact(emails, contact_email)
            contact_calls = self._filter_calls_for_contact(calls, contact_phone)

            # Last contact date
            last_date = self._find_last_contact_date(contact_emails, contact_calls)
            days_since = (today - last_date).days if last_date else None

            # Average response time
            avg_response = self._calculate_avg_response_hours(contact_emails)

            # Status
            status = self._contact_status(role, days_since)

            party = PartyContact(
                contact_id=contact_id,
                contact_name=contact_name,
                role=role,
                last_contact_date=last_date,
                days_since_contact=days_since,
                total_emails=len(contact_emails),
                total_calls=len(contact_calls),
                avg_response_hours=avg_response,
                status=status,
            )
            parties.append(party)

            # Identify gaps
            if status in ("warning", "critical"):
                gap = self._build_gap(contact_name, role, days_since, status)
                if gap is not None:
                    gaps.append(gap)

        # Overall health score
        overall_score = self._calculate_overall_health(
            parties, total_emails, total_calls
        )
        health_status = self._health_status(overall_score)

        # Global average response time
        all_response_hours: list[float] = [
            p.avg_response_hours for p in parties if p.avg_response_hours is not None
        ]
        avg_response_global = (
            sum(all_response_hours) / len(all_response_hours)
            if all_response_hours
            else None
        )

        summary = self._build_health_summary(
            overall_score, health_status, parties, gaps
        )

        return CommunicationHealth(
            case_id=case_id,
            overall_score=round(overall_score, 1),
            status=health_status,
            parties=parties,
            gaps=gaps,
            total_emails=total_emails,
            total_calls=total_calls,
            avg_response_hours=(
                round(avg_response_global, 1)
                if avg_response_global is not None
                else None
            ),
            summary=summary,
        )

    # ------------------------------------------------------------------
    # Urgency Analysis
    # ------------------------------------------------------------------

    def analyze_urgency(
        self,
        subject: str | None,
        body: str | None,
        sender: str | None,
        case_context: dict[str, Any] | None = None,
    ) -> UrgencyScore:
        """Score the urgency of a single communication.

        Analyzes French legal keywords in subject and body to determine
        urgency level. Also considers case context (e.g., approaching deadlines).

        Args:
            subject: Email subject line.
            body: Email or message body text.
            sender: Sender email address or name.
            case_context: Optional case metadata for context-aware scoring.

        Returns:
            UrgencyScore with score, category, and indicator details.
        """
        text_combined = " ".join(filter(None, [subject or "", body or ""])).lower()

        if not text_combined.strip():
            return UrgencyScore(
                score=0.0,
                category="low",
                indicators=[],
                explanation="Aucun contenu à analyser",
            )

        indicators: list[UrgencyIndicator] = []
        category_scores: dict[str, float] = {
            "critical": 0.0,
            "urgent": 0.0,
            "attention": 0.0,
        }

        for urgency_cat, keywords in URGENCY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_combined:
                    # Find context snippet
                    idx = text_combined.find(keyword)
                    start = max(0, idx - 40)
                    end = min(len(text_combined), idx + len(keyword) + 40)
                    context_snippet = text_combined[start:end].strip()

                    indicators.append(
                        UrgencyIndicator(
                            keyword=keyword,
                            category=urgency_cat,
                            context=f"...{context_snippet}...",
                        )
                    )

                    if urgency_cat == "critical":
                        category_scores["critical"] += 30.0
                    elif urgency_cat == "urgent":
                        category_scores["urgent"] += 20.0
                    else:
                        category_scores["attention"] += 10.0

        # Context-based adjustments
        if case_context:
            # Boost urgency if case has approaching deadlines
            days_to_deadline = case_context.get("days_to_next_deadline")
            if days_to_deadline is not None and days_to_deadline <= 7:
                category_scores["urgent"] += 15.0

            # Boost if case is at risk
            risk_level = case_context.get("risk_level", "")
            if risk_level in ("high", "critical"):
                category_scores["urgent"] += 10.0

        # Compute final score
        raw_score = (
            category_scores["critical"] * 1.0
            + category_scores["urgent"] * 0.7
            + category_scores["attention"] * 0.3
        )
        final_score = min(100.0, raw_score)

        # Determine category
        if final_score >= 75 or category_scores["critical"] > 0:
            category = "critical"
        elif final_score >= 50:
            category = "high"
        elif final_score >= 25:
            category = "medium"
        else:
            category = "low"

        explanation = self._build_urgency_explanation(category, indicators, final_score)

        return UrgencyScore(
            score=round(final_score, 1),
            category=category,
            indicators=indicators,
            explanation=explanation,
        )

    # ------------------------------------------------------------------
    # Sentiment Trend Detection
    # ------------------------------------------------------------------

    def detect_sentiment_shift(
        self,
        messages_chronological: list[dict[str, Any]],
    ) -> SentimentTrend:
        """Detect sentiment shifts in chronologically ordered messages.

        Analyzes the tone of messages over time to detect escalation patterns
        (e.g., cooperative -> tense -> hostile).

        Args:
            messages_chronological: List of message dicts with 'date',
                'subject', 'body_text' keys, ordered oldest to newest.

        Returns:
            SentimentTrend with trend direction, alert level, and key moments.
        """
        if not messages_chronological:
            return SentimentTrend(
                trend="stable",
                alert_level="none",
                current_sentiment="neutral",
                moments=[],
                key_moments=[],
                summary="Aucun message à analyser.",
            )

        moments: list[SentimentMoment] = []

        for msg in messages_chronological:
            msg_date = self._parse_date(msg.get("date") or msg.get("received_at"))
            if msg_date is None:
                continue

            text_combined = " ".join(
                filter(None, [msg.get("subject", ""), msg.get("body_text", "")])
            ).lower()

            sentiment, score = self._analyze_message_sentiment(text_combined)
            excerpt = text_combined[:120] if text_combined else ""

            moments.append(
                SentimentMoment(
                    date=msg_date,
                    sentiment=sentiment,
                    score=score,
                    excerpt=excerpt,
                )
            )

        if not moments:
            return SentimentTrend(
                trend="stable",
                alert_level="none",
                current_sentiment="neutral",
                moments=[],
                key_moments=[],
                summary="Aucun message analysable.",
            )

        # Determine trend
        trend = self._compute_trend(moments)
        current_sentiment = moments[-1].sentiment

        # Identify key moments (significant shifts)
        key_moments = self._find_key_moments(moments)

        # Determine alert level
        alert_level = self._determine_alert_level(trend, current_sentiment)

        summary = self._build_sentiment_summary(
            trend, current_sentiment, alert_level, len(moments), key_moments
        )

        return SentimentTrend(
            trend=trend,
            alert_level=alert_level,
            current_sentiment=current_sentiment,
            moments=moments,
            key_moments=key_moments,
            summary=summary,
        )

    # ------------------------------------------------------------------
    # Private Helpers — Communication Health
    # ------------------------------------------------------------------

    @staticmethod
    def _filter_emails_for_contact(
        emails: list[dict[str, Any]], contact_email: str
    ) -> list[dict[str, Any]]:
        """Filter emails that involve a specific contact email."""
        if not contact_email:
            return []

        result = []
        for email in emails:
            from_addr = (email.get("from_address") or "").lower()
            to_addrs = [
                (a if isinstance(a, str) else a.get("email", "")).lower()
                for a in (email.get("to_addresses") or [])
            ]

            if contact_email == from_addr or contact_email in to_addrs:
                result.append(email)

        return result

    @staticmethod
    def _filter_calls_for_contact(
        calls: list[dict[str, Any]], contact_phone: str
    ) -> list[dict[str, Any]]:
        """Filter calls that involve a specific contact phone number."""
        if not contact_phone:
            return []

        result = []
        for call in calls:
            caller = call.get("caller_number") or ""
            callee = call.get("callee_number") or ""
            if contact_phone in (caller, callee):
                result.append(call)

        return result

    @staticmethod
    def _find_last_contact_date(
        emails: list[dict[str, Any]],
        calls: list[dict[str, Any]],
    ) -> date | None:
        """Find the most recent contact date from emails and calls."""
        latest: date | None = None

        for email in emails:
            received = email.get("received_at")
            if received is None:
                continue
            if isinstance(received, str):
                try:
                    email_date = datetime.fromisoformat(received).date()
                except (ValueError, TypeError):
                    continue
            elif isinstance(received, datetime):
                email_date = received.date()
            elif isinstance(received, date):
                email_date = received
            else:
                continue
            if latest is None or email_date > latest:
                latest = email_date

        for call in calls:
            started = call.get("started_at")
            if started is None:
                continue
            if isinstance(started, str):
                try:
                    call_date = datetime.fromisoformat(started).date()
                except (ValueError, TypeError):
                    continue
            elif isinstance(started, datetime):
                call_date = started.date()
            elif isinstance(started, date):
                call_date = started
            else:
                continue
            if latest is None or call_date > latest:
                latest = call_date

        return latest

    @staticmethod
    def _calculate_avg_response_hours(
        emails: list[dict[str, Any]],
    ) -> float | None:
        """Calculate average response time in hours from email pairs.

        Looks at consecutive email pairs where the direction alternates
        (incoming -> outgoing or vice versa) and computes the average
        time between them.
        """
        if len(emails) < 2:
            return None

        # Sort by received_at
        sorted_emails = sorted(
            emails,
            key=lambda e: e.get("received_at") or "",
        )

        response_times: list[float] = []

        for i in range(1, len(sorted_emails)):
            prev = sorted_emails[i - 1]
            curr = sorted_emails[i]

            prev_time = prev.get("received_at")
            curr_time = curr.get("received_at")
            if prev_time is None or curr_time is None:
                continue

            if isinstance(prev_time, str):
                try:
                    prev_time = datetime.fromisoformat(prev_time)
                except (ValueError, TypeError):
                    continue
            if isinstance(curr_time, str):
                try:
                    curr_time = datetime.fromisoformat(curr_time)
                except (ValueError, TypeError):
                    continue

            if not isinstance(prev_time, datetime) or not isinstance(
                curr_time, datetime
            ):
                continue

            diff_hours = (curr_time - prev_time).total_seconds() / 3600
            if 0 < diff_hours < 720:  # Ignore gaps > 30 days
                response_times.append(diff_hours)

        if not response_times:
            return None

        return sum(response_times) / len(response_times)

    @staticmethod
    def _contact_status(role: str, days_since: int | None) -> str:
        """Determine contact status based on days since last communication."""
        if days_since is None:
            return "no_contact"

        thresholds = GAP_THRESHOLDS.get(role, GAP_THRESHOLDS["third_party"])

        if days_since >= thresholds["critical"]:
            return "critical"
        if days_since >= thresholds["warning"]:
            return "warning"
        return "active"

    @staticmethod
    def _build_gap(
        contact_name: str,
        role: str,
        days_since: int | None,
        status: str,
    ) -> CommunicationGap | None:
        """Build a communication gap report."""
        if days_since is None:
            return CommunicationGap(
                contact_name=contact_name,
                role=role,
                days_since_contact=999,
                severity="critical",
                recommendation=(
                    f"Aucun contact enregistré avec {contact_name} ({role}). "
                    f"Établissez le contact immédiatement."
                ),
            )

        role_labels = {
            "client": "le client",
            "adverse": "la partie adverse",
            "witness": "le témoin",
            "third_party": "le tiers",
        }
        role_label = role_labels.get(role, role)

        if status == "critical":
            return CommunicationGap(
                contact_name=contact_name,
                role=role,
                days_since_contact=days_since,
                severity="critical",
                recommendation=(
                    f"Aucun contact avec {role_label} ({contact_name}) depuis "
                    f"{days_since} jours. Action urgente requise."
                ),
            )

        if status == "warning":
            return CommunicationGap(
                contact_name=contact_name,
                role=role,
                days_since_contact=days_since,
                severity="medium",
                recommendation=(
                    f"Pas de contact avec {role_label} ({contact_name}) depuis "
                    f"{days_since} jours. Un suivi est recommandé."
                ),
            )

        return None

    @staticmethod
    def _calculate_overall_health(
        parties: list[PartyContact],
        total_emails: int,
        total_calls: int,
    ) -> float:
        """Calculate overall communication health score."""
        if not parties:
            return 30.0  # No contacts = poor health

        # Per-party scores
        party_scores: list[float] = []
        client_score: float | None = None

        for party in parties:
            if party.status == "active":
                pscore = 90.0
            elif party.status == "warning":
                pscore = 50.0
            elif party.status == "critical":
                pscore = 15.0
            else:  # no_contact
                pscore = 5.0

            # Adjust by communication volume
            comm_count = party.total_emails + party.total_calls
            if comm_count > 10:
                pscore = min(100.0, pscore + 5.0)
            elif comm_count == 0:
                pscore = max(0.0, pscore - 10.0)

            party_scores.append(pscore)

            if party.role == "client":
                client_score = pscore

        # Weighted: client has double weight
        if client_score is not None:
            total_weight = len(party_scores) + 1  # Extra weight for client
            weighted_sum = sum(party_scores) + client_score  # Client counted twice
            overall = weighted_sum / total_weight
        else:
            overall = sum(party_scores) / len(party_scores) if party_scores else 30.0

        # Communication volume bonus
        total_comms = total_emails + total_calls
        if total_comms > 20:
            overall = min(100.0, overall + 5.0)
        elif total_comms == 0:
            overall = max(0.0, overall - 15.0)

        return min(100.0, max(0.0, overall))

    @staticmethod
    def _health_status(score: float) -> str:
        """Convert health score to status label."""
        if score >= 60:
            return "healthy"
        if score >= 35:
            return "warning"
        return "critical"

    @staticmethod
    def _build_health_summary(
        score: float,
        status: str,
        parties: list[PartyContact],
        gaps: list[CommunicationGap],
    ) -> str:
        """Build communication health summary in French."""
        status_labels = {
            "healthy": "Communication en bonne santé",
            "warning": "Communication nécessitant attention",
            "critical": "Communication en état critique",
        }
        label = status_labels.get(status, "État inconnu")
        summary = f"{label} (score : {score:.0f}/100)."

        critical_gaps = [g for g in gaps if g.severity == "critical"]
        if critical_gaps:
            names = ", ".join(g.contact_name for g in critical_gaps)
            summary += f" Contact perdu avec : {names}."

        active_count = sum(1 for p in parties if p.status == "active")
        total = len(parties)
        if total > 0:
            summary += f" {active_count}/{total} partie(s) en contact actif."

        return summary

    # ------------------------------------------------------------------
    # Private Helpers — Urgency
    # ------------------------------------------------------------------

    @staticmethod
    def _build_urgency_explanation(
        category: str,
        indicators: list[UrgencyIndicator],
        score: float,
    ) -> str:
        """Build urgency explanation in French."""
        if not indicators:
            return "Aucun indicateur d'urgence détecté."

        category_labels = {
            "critical": "Urgence critique détectée",
            "high": "Urgence élevée détectée",
            "medium": "Urgence modérée",
            "low": "Faible urgence",
        }
        label = category_labels.get(category, "Urgence inconnue")

        critical_kw = [i.keyword for i in indicators if i.category == "critical"]
        urgent_kw = [i.keyword for i in indicators if i.category == "urgent"]

        parts = [label]
        if critical_kw:
            parts.append(f"termes critiques : {', '.join(critical_kw[:3])}")
        if urgent_kw:
            parts.append(f"termes urgents : {', '.join(urgent_kw[:3])}")

        return " — ".join(parts) + f" (score : {score:.0f}/100)."

    # ------------------------------------------------------------------
    # Private Helpers — Sentiment
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
                # Handle both date and datetime strings
                if "T" in value or " " in value:
                    return datetime.fromisoformat(value).date()
                return date.fromisoformat(value)
            except (ValueError, TypeError):
                return None
        return None

    @staticmethod
    def _analyze_message_sentiment(text: str) -> tuple[str, float]:
        """Analyze sentiment of a single message text.

        Returns (sentiment_label, sentiment_score) where score is
        -1.0 (hostile) to 1.0 (positive).
        """
        if not text:
            return "neutral", 0.0

        scores: dict[str, float] = {
            "positive": 0.0,
            "neutral": 0.0,
            "negative": 0.0,
            "hostile": 0.0,
        }

        for sentiment_cat, keywords in SENTIMENT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    scores[sentiment_cat] += 1.0

        # Determine dominant sentiment
        max_cat = max(scores, key=lambda k: scores[k])
        max_score = scores[max_cat]

        if max_score == 0:
            return "neutral", 0.0

        # Compute a numeric score from -1.0 to 1.0
        numeric = (
            scores["positive"] * 1.0
            + scores["neutral"] * 0.0
            + scores["negative"] * -0.5
            + scores["hostile"] * -1.0
        )
        total_hits = sum(scores.values())
        if total_hits > 0:
            numeric = numeric / total_hits
        numeric = max(-1.0, min(1.0, numeric))

        return max_cat, round(numeric, 2)

    @staticmethod
    def _compute_trend(moments: list[SentimentMoment]) -> str:
        """Compute overall sentiment trend from chronological moments.

        Uses a simple linear regression on scores to determine direction.
        """
        if len(moments) < 2:
            return "stable"

        # Compare average of first half vs second half
        mid = len(moments) // 2
        first_half = moments[:mid] if mid > 0 else moments[:1]
        second_half = moments[mid:]

        avg_first = sum(m.score for m in first_half) / len(first_half)
        avg_second = sum(m.score for m in second_half) / len(second_half)

        diff = avg_second - avg_first

        if diff > 0.15:
            return "improving"
        if diff < -0.15:
            return "deteriorating"
        return "stable"

    @staticmethod
    def _find_key_moments(moments: list[SentimentMoment]) -> list[SentimentMoment]:
        """Find key moments where sentiment shifted significantly."""
        if len(moments) < 2:
            return []

        key_moments: list[SentimentMoment] = []

        for i in range(1, len(moments)):
            score_diff = abs(moments[i].score - moments[i - 1].score)
            if score_diff >= 0.4:
                key_moments.append(moments[i])

        return key_moments[:5]  # Limit to 5 most significant shifts

    @staticmethod
    def _determine_alert_level(trend: str, current_sentiment: str) -> str:
        """Determine alert level based on trend and current sentiment."""
        if current_sentiment == "hostile":
            return "high"
        if trend == "deteriorating" and current_sentiment == "negative":
            return "high"
        if trend == "deteriorating":
            return "medium"
        if current_sentiment == "negative":
            return "low"
        return "none"

    @staticmethod
    def _build_sentiment_summary(
        trend: str,
        current_sentiment: str,
        alert_level: str,
        message_count: int,
        key_moments: list[SentimentMoment],
    ) -> str:
        """Build sentiment trend summary in French."""
        trend_labels = {
            "improving": "en amélioration",
            "stable": "stable",
            "deteriorating": "en dégradation",
        }
        sentiment_labels = {
            "positive": "positif",
            "neutral": "neutre",
            "negative": "négatif",
            "hostile": "hostile",
        }

        trend_label = trend_labels.get(trend, "inconnu")
        sentiment_label = sentiment_labels.get(current_sentiment, "inconnu")

        summary = (
            f"Analyse de {message_count} message(s). "
            f"Tendance : {trend_label}. "
            f"Sentiment actuel : {sentiment_label}."
        )

        if key_moments:
            summary += (
                f" {len(key_moments)} moment(s) de changement significatif détecté(s)."
            )

        if alert_level in ("medium", "high"):
            summary += " Vigilance recommandée."

        return summary
