"""EmailTriageClassifier — classify incoming emails by urgency.

Categories:
- URGENT: contains deadline-related terms, tribunal notices, mise en demeure
- NORMAL: standard professional correspondence
- INFO_ONLY: newsletters, notifications, FYI emails
- SPAM: unsolicited, marketing, phishing indicators

Rule-based + keyword scoring with confidence.
Upgrade path to fine-tuned classifier model.
"""
import re
from dataclasses import dataclass, field


@dataclass
class Classification:
    """Email classification result."""
    category: str  # URGENT, NORMAL, INFO_ONLY, SPAM
    confidence: float  # 0.0 to 1.0
    reasons: list[str] = field(default_factory=list)
    suggested_priority: int = 3  # 1=highest, 5=lowest


# ── Keyword patterns by category ──

URGENT_PATTERNS = [
    # Deadlines
    (re.compile(r"\b(délai|deadline|échéance|date\s*limite)\b", re.I), "deadline_keyword"),
    (re.compile(r"\b(urgent|urgence|immédiat|impératif)\b", re.I), "urgency_keyword"),
    # Court/tribunal
    (re.compile(r"\b(tribunal|cour|audience|plaidoirie|comparution)\b", re.I), "court_keyword"),
    (re.compile(r"\b(citation|assignation|signification|exploit)\b", re.I), "legal_process"),
    (re.compile(r"\b(mise\s+en\s+demeure|sommation|injonction)\b", re.I), "formal_notice"),
    # Appeals and deadlines
    (re.compile(r"\b(appel|opposition|cassation|pourvoi)\b", re.I), "appeal_keyword"),
    (re.compile(r"\b(dernier\s+jour|expire|péremption|forclusion)\b", re.I), "expiry_keyword"),
    # Orders/judgments
    (re.compile(r"\b(jugement|arrêt|ordonnance|décision)\b", re.I), "judgment_keyword"),
    (re.compile(r"\b(notifi|signifi)\w*\b", re.I), "notification_keyword"),
]

SPAM_PATTERNS = [
    (re.compile(r"\b(unsubscribe|se\s+désabonner|uitschrijven)\b", re.I), "unsubscribe_link"),
    (re.compile(r"\b(newsletter|bulletin|infolettre)\b", re.I), "newsletter"),
    (re.compile(r"\b(promo|discount|offre\s+spéciale|soldes)\b", re.I), "promotion"),
    (re.compile(r"\b(win|gagner|congratulations|félicitations)\b", re.I), "lottery_scam"),
    (re.compile(r"\b(click\s+here|cliquez\s+ici)\b", re.I), "click_bait"),
    (re.compile(r"\b(viagra|crypto|bitcoin|invest)\b", re.I), "spam_keyword"),
    (re.compile(r"\bnoreply@\b", re.I), "noreply_sender"),
]

INFO_PATTERNS = [
    (re.compile(r"\b(FYI|pour\s+info|ter\s+info|à\s+titre\s+d.information)\b", re.I), "fyi_keyword"),
    (re.compile(r"\b(veuillez\s+noter|please\s+note|nota\s+bene)\b", re.I), "note_keyword"),
    (re.compile(r"\b(rappel|reminder|herinnering)\b", re.I), "reminder"),
    (re.compile(r"\b(mise\s+à\s+jour|update|actualisering)\b", re.I), "update"),
    (re.compile(r"\b(compte.rendu|rapport|verslag)\b", re.I), "report"),
]

# Known professional senders (Belgian legal ecosystem)
PROFESSIONAL_SENDERS = [
    re.compile(r"@just\.fgov\.be$", re.I),          # Belgian justice
    re.compile(r"@juridat\.be$", re.I),              # Juridat
    re.compile(r"@avocats\.be$", re.I),              # OBFG
    re.compile(r"@balieantwerpen\.be$", re.I),       # OVB
    re.compile(r"@dpa\.fgov\.be$", re.I),            # DPA
    re.compile(r"@notaire\.be$", re.I),              # Notaries
    re.compile(r"@huissier\.be$", re.I),             # Bailiffs
]


class EmailTriageClassifier:
    """Classify incoming emails by urgency and category."""

    def classify(
        self,
        subject: str,
        body: str,
        sender: str = "",
    ) -> Classification:
        """Classify an email.

        Args:
            subject: Email subject line
            body: Email body text
            sender: Sender email address

        Returns:
            Classification with category, confidence, and reasons
        """
        text = f"{subject} {body}"
        scores: dict[str, float] = {
            "URGENT": 0.0,
            "NORMAL": 0.2,  # default baseline
            "INFO_ONLY": 0.0,
            "SPAM": 0.0,
        }
        reasons: list[str] = []

        # Check urgent patterns
        for pattern, reason in URGENT_PATTERNS:
            matches = pattern.findall(text)
            if matches:
                scores["URGENT"] += 0.15 * min(len(matches), 3)
                reasons.append(f"urgent:{reason}({len(matches)})")

        # Check spam patterns
        for pattern, reason in SPAM_PATTERNS:
            matches = pattern.findall(text)
            if matches:
                scores["SPAM"] += 0.2 * min(len(matches), 3)
                reasons.append(f"spam:{reason}({len(matches)})")

        # Check info patterns
        for pattern, reason in INFO_PATTERNS:
            matches = pattern.findall(text)
            if matches:
                scores["INFO_ONLY"] += 0.15 * min(len(matches), 3)
                reasons.append(f"info:{reason}({len(matches)})")

        # Professional sender boost for urgent
        if sender:
            for pattern in PROFESSIONAL_SENDERS:
                if pattern.search(sender):
                    scores["URGENT"] += 0.1
                    scores["NORMAL"] += 0.1
                    reasons.append(f"professional_sender={sender}")
                    break

        # Subject line urgency indicators
        if subject:
            subj_upper = subject.upper()
            if subj_upper.startswith("URGENT") or "[URGENT]" in subj_upper:
                scores["URGENT"] += 0.3
                reasons.append("subject_urgent_prefix")
            if "RE:" in subj_upper or "FW:" in subj_upper:
                scores["NORMAL"] += 0.1
                reasons.append("reply_or_forward")

        # Pick highest category
        best_category = max(scores, key=lambda k: scores[k])
        best_score = scores[best_category]

        # Normalize confidence to 0-1
        total = sum(scores.values())
        confidence = best_score / total if total > 0 else 0.0

        # Priority mapping
        priority_map = {"URGENT": 1, "NORMAL": 3, "INFO_ONLY": 4, "SPAM": 5}

        return Classification(
            category=best_category,
            confidence=min(confidence, 1.0),
            reasons=reasons,
            suggested_priority=priority_map.get(best_category, 3),
        )
