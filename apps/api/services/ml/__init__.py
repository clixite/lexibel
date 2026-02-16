"""ML Pipeline — orchestrates linkage ranking, email triage, and deadline extraction.

Usage:
    pipeline = MLPipeline()
    result = pipeline.process_event(event)
"""
from dataclasses import dataclass, field
from typing import Optional

from apps.api.services.ml.linkage_ranker import LinkageRanker, CaseSuggestion
from apps.api.services.ml.email_triage import EmailTriageClassifier, Classification
from apps.api.services.ml.deadline_extractor import DeadlineExtractor, Deadline


@dataclass
class MLResult:
    """Combined result from all ML services."""
    case_suggestions: list[CaseSuggestion] = field(default_factory=list)
    classification: Optional[Classification] = None
    deadlines: list[Deadline] = field(default_factory=list)


class MLPipeline:
    """Orchestrate linkage ranking, email triage, and deadline extraction."""

    def __init__(self) -> None:
        self.linker = LinkageRanker()
        self.triage = EmailTriageClassifier()
        self.deadlines = DeadlineExtractor()

    def process_event(self, event: dict) -> MLResult:
        """Run all ML services on an incoming event.

        Args:
            event: Dict with keys like subject, body, sender, type, tenant_id.
                   Optional: existing_cases (list of case dicts for linkage).

        Returns:
            MLResult with case_suggestions, classification, and deadlines.
        """
        result = MLResult()

        # Text for analysis
        text = self._extract_text(event)

        # 1. Case linkage
        existing_cases = event.get("existing_cases", [])
        if existing_cases:
            result.case_suggestions = self.linker.rank(
                text=text,
                sender=event.get("sender", ""),
                existing_cases=existing_cases,
            )

        # 2. Email triage
        result.classification = self.triage.classify(
            subject=event.get("subject", ""),
            body=event.get("body", text),
            sender=event.get("sender", ""),
        )

        # 3. Deadline extraction
        result.deadlines = self.deadlines.extract(text)

        return result

    def _extract_text(self, event: dict) -> str:
        """Extract combined text from event fields."""
        parts = []
        for key in ("subject", "body", "body_preview", "description", "content"):
            val = event.get(key)
            if val:
                parts.append(str(val))
        return " ".join(parts)


__all__ = [
    "MLPipeline",
    "MLResult",
    "LinkageRanker",
    "CaseSuggestion",
    "EmailTriageClassifier",
    "Classification",
    "DeadlineExtractor",
    "Deadline",
]
