"""EmotionalRadar — analyze communication tone in case timeline.

Scores each event: COOPERATIVE, NEUTRAL, TENSE, HOSTILE, THREATENING.
Detects escalation patterns over time. Flags conversations approaching
legal thresholds (harassment, threats).
"""

import re
from dataclasses import dataclass, field


@dataclass
class EventTone:
    """Tone analysis for a single event."""

    event_id: str
    event_type: str  # email, call, note
    date: str
    tone: str  # COOPERATIVE, NEUTRAL, TENSE, HOSTILE, THREATENING
    score: float  # -1.0 (hostile) to +1.0 (cooperative)
    keywords_found: list[str] = field(default_factory=list)
    flagged: bool = False
    flag_reason: str = ""


@dataclass
class EmotionalProfile:
    """Emotional profile for a case's communications."""

    case_id: str
    overall_tone: str  # COOPERATIVE, NEUTRAL, TENSE, HOSTILE, THREATENING
    overall_score: float
    trend: str  # IMPROVING, STABLE, DETERIORATING
    escalation_risk: str  # LOW, MEDIUM, HIGH, CRITICAL
    events_analyzed: int = 0
    flagged_events: list[EventTone] = field(default_factory=list)
    all_events: list[EventTone] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


# ── Tone patterns ──

COOPERATIVE_PATTERNS = [
    (re.compile(r"\b(merci|dank|thank|cordialement|bien\s+à\s+vous)\b", re.I), 0.3),
    (re.compile(r"\b(accord|akkoord|agree|d.accord|accepte)\b", re.I), 0.4),
    (
        re.compile(r"\b(proposition|voorstel|propose|collaborer|samenwerken)\b", re.I),
        0.3,
    ),
    (re.compile(r"\b(résoudre|oplossen|solution|compromis)\b", re.I), 0.4),
    (re.compile(r"\b(volontiers|graag|heureux|enchanté)\b", re.I), 0.2),
]

TENSE_PATTERNS = [
    (re.compile(r"\b(désaccord|onenigheid|disagree|conteste|betwist)\b", re.I), -0.3),
    (re.compile(r"\b(déçu|teleurgesteld|disappoint|insatisfait)\b", re.I), -0.3),
    (re.compile(r"\b(retard|vertraging|delay|urgence)\b", re.I), -0.2),
    (re.compile(r"\b(inacceptable|onaanvaardbaar|unacceptable)\b", re.I), -0.4),
    (re.compile(r"\b(exige|eist|demand|sommation|injonction)\b", re.I), -0.3),
]

HOSTILE_PATTERNS = [
    (re.compile(r"\b(mise\s+en\s+demeure|ingebrekestelling)\b", re.I), -0.5),
    (re.compile(r"\b(assignation|dagvaarding|citation|tribunal)\b", re.I), -0.4),
    (re.compile(r"\b(incompétent|onbekwaam|négligent|nalatig)\b", re.I), -0.5),
    (re.compile(r"\b(faute\s+grave|zware\s+fout|grave\s+erreur)\b", re.I), -0.6),
    (re.compile(r"\b(responsable|aansprakelijk|liable|dommages)\b", re.I), -0.3),
]

THREATENING_PATTERNS = [
    (re.compile(r"\b(menace|dreig|threaten|plainte\s+pénale)\b", re.I), -0.8),
    (re.compile(r"\b(poursuites?|vervolging|prosecution)\b", re.I), -0.7),
    (re.compile(r"\b(harcèlement|pesterij|harassment)\b", re.I), -0.9),
    (re.compile(r"\b(violence|geweld|intimidation)\b", re.I), -0.9),
    (re.compile(r"\b(détruire|vernietigen|destroy|tuer)\b", re.I), -1.0),
]

# Legal threshold patterns
LEGAL_THRESHOLD_PATTERNS = [
    (
        re.compile(r"\b(menace|dreig|threaten)\b", re.I),
        "Potential threat detected (Art. 327-331 Code pénal)",
    ),
    (
        re.compile(r"\b(harcèlement|pesterij|stalking)\b", re.I),
        "Potential harassment (Art. 442bis Code pénal)",
    ),
    (
        re.compile(r"\b(calomnie|laster|defamation|diffamation)\b", re.I),
        "Potential defamation (Art. 443 Code pénal)",
    ),
    (
        re.compile(r"\b(violence|geweld|agress)\b", re.I),
        "Violence/aggression indicator",
    ),
]


class EmotionalRadar:
    """Analyze communication tone and detect escalation."""

    def analyze(
        self,
        case_id: str,
        tenant_id: str,
        events: list[dict],
    ) -> EmotionalProfile:
        """Analyze all events in a case timeline.

        Args:
            case_id: Case ID
            tenant_id: Tenant UUID
            events: List of event dicts with keys: id, type, date, content/body

        Returns:
            EmotionalProfile with tone analysis
        """
        analyzed: list[EventTone] = []

        for event in events:
            text = (
                event.get("content")
                or event.get("body")
                or event.get("description")
                or ""
            )
            if not text.strip():
                continue

            tone_result = self._analyze_event(
                event_id=event.get("id", ""),
                event_type=event.get("type", "unknown"),
                date=event.get("date", event.get("created_at", "")),
                text=text,
            )
            analyzed.append(tone_result)

        if not analyzed:
            return EmotionalProfile(
                case_id=case_id,
                overall_tone="NEUTRAL",
                overall_score=0.0,
                trend="STABLE",
                escalation_risk="LOW",
            )

        # Compute overall metrics
        avg_score = sum(e.score for e in analyzed) / len(analyzed)
        overall_tone = self._score_to_tone(avg_score)
        trend = self._compute_trend(analyzed)
        flagged = [e for e in analyzed if e.flagged]
        escalation_risk = self._compute_escalation_risk(analyzed, flagged)

        profile = EmotionalProfile(
            case_id=case_id,
            overall_tone=overall_tone,
            overall_score=round(avg_score, 2),
            trend=trend,
            escalation_risk=escalation_risk,
            events_analyzed=len(analyzed),
            flagged_events=flagged,
            all_events=analyzed,
            recommendations=self._generate_recommendations(
                overall_tone, trend, escalation_risk, flagged
            ),
        )

        return profile

    def _analyze_event(
        self,
        event_id: str,
        event_type: str,
        date: str,
        text: str,
    ) -> EventTone:
        """Analyze tone of a single event."""
        score = 0.0
        keywords: list[str] = []

        # Score cooperative patterns
        for pattern, weight in COOPERATIVE_PATTERNS:
            matches = pattern.findall(text)
            if matches:
                score += weight * min(len(matches), 2)
                keywords.extend(matches[:2])

        # Score tense patterns
        for pattern, weight in TENSE_PATTERNS:
            matches = pattern.findall(text)
            if matches:
                score += weight * min(len(matches), 2)
                keywords.extend(matches[:2])

        # Score hostile patterns
        for pattern, weight in HOSTILE_PATTERNS:
            matches = pattern.findall(text)
            if matches:
                score += weight * min(len(matches), 2)
                keywords.extend(matches[:2])

        # Score threatening patterns
        for pattern, weight in THREATENING_PATTERNS:
            matches = pattern.findall(text)
            if matches:
                score += weight * min(len(matches), 2)
                keywords.extend(matches[:2])

        # Clamp score
        score = max(-1.0, min(1.0, score))
        tone = self._score_to_tone(score)

        # Check legal thresholds
        flagged = False
        flag_reason = ""
        for pattern, reason in LEGAL_THRESHOLD_PATTERNS:
            if pattern.search(text):
                flagged = True
                flag_reason = reason
                break

        return EventTone(
            event_id=event_id,
            event_type=event_type,
            date=date,
            tone=tone,
            score=round(score, 2),
            keywords_found=keywords,
            flagged=flagged,
            flag_reason=flag_reason,
        )

    @staticmethod
    def _score_to_tone(score: float) -> str:
        """Convert numeric score to tone category."""
        if score >= 0.3:
            return "COOPERATIVE"
        elif score >= 0.0:
            return "NEUTRAL"
        elif score >= -0.3:
            return "TENSE"
        elif score >= -0.6:
            return "HOSTILE"
        else:
            return "THREATENING"

    @staticmethod
    def _compute_trend(events: list[EventTone]) -> str:
        """Compute tone trend over time."""
        if len(events) < 2:
            return "STABLE"

        # Compare first half vs second half
        mid = len(events) // 2
        first_half = sum(e.score for e in events[:mid]) / max(mid, 1)
        second_half = sum(e.score for e in events[mid:]) / max(len(events) - mid, 1)

        diff = second_half - first_half
        if diff > 0.15:
            return "IMPROVING"
        elif diff < -0.15:
            return "DETERIORATING"
        return "STABLE"

    @staticmethod
    def _compute_escalation_risk(
        events: list[EventTone], flagged: list[EventTone]
    ) -> str:
        """Compute escalation risk level."""
        if len(flagged) >= 3:
            return "CRITICAL"
        if len(flagged) >= 1:
            return "HIGH"

        hostile_count = sum(1 for e in events if e.tone in ("HOSTILE", "THREATENING"))
        if hostile_count >= 3:
            return "HIGH"
        if hostile_count >= 1:
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def _generate_recommendations(
        tone: str, trend: str, risk: str, flagged: list[EventTone]
    ) -> list[str]:
        """Generate recommendations based on emotional analysis."""
        recs = []

        if risk in ("HIGH", "CRITICAL"):
            recs.append(
                "Escalation detected. Consider involving a mediator or senior partner."
            )

        if flagged:
            recs.append(
                f"{len(flagged)} communication(s) flagged for potential legal threshold violations."
            )
            for f in flagged[:3]:
                recs.append(f"  - {f.flag_reason} (event: {f.event_id})")

        if trend == "DETERIORATING":
            recs.append(
                "Tone is deteriorating over time. Proactive outreach recommended."
            )

        if tone == "THREATENING":
            recs.append(
                "URGENT: Threatening communications detected. Consider protective measures and document all interactions."
            )

        if not recs:
            recs.append(
                "Communication tone within normal parameters. No action required."
            )

        return recs
