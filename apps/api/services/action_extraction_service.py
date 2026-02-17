"""Action Extraction Service — AI-powered extraction from transcripts.

Analyzes transcripts to extract:
- Action items / TODOs
- Deadlines and dates
- Decisions made
- Contact references
- Case references
- Key topics and sentiment
"""

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from apps.api.services.llm_gateway import ContextChunk, LLMGateway, LLMResponse


@dataclass
class ActionItem:
    """An action item extracted from transcript."""

    action_id: str
    text: str
    assignee: Optional[str] = None  # Name mentioned or detected
    deadline: Optional[datetime] = None
    priority: str = "medium"  # low, medium, high, urgent
    status: str = "pending"  # pending, in_progress, completed
    confidence: float = 0.0
    source_segment_start: Optional[float] = None  # timestamp in transcript
    source_segment_end: Optional[float] = None


@dataclass
class ExtractedDecision:
    """A decision made during the conversation."""

    decision_id: str
    text: str
    decided_by: Optional[str] = None
    timestamp: Optional[float] = None
    confidence: float = 0.0


@dataclass
class ExtractedReference:
    """A reference to a case, contact, or document."""

    ref_id: str
    ref_type: str  # "case", "contact", "document", "law"
    text: str  # The referenced entity
    context: str  # Surrounding context
    confidence: float = 0.0
    timestamp: Optional[float] = None


@dataclass
class TranscriptInsights:
    """Complete insights extracted from transcript."""

    transcript_id: str
    summary: str  # 3-sentence executive summary
    action_items: list[ActionItem] = field(default_factory=list)
    decisions: list[ExtractedDecision] = field(default_factory=list)
    references: list[ExtractedReference] = field(default_factory=list)
    key_topics: list[str] = field(default_factory=list)
    sentiment_score: float = 0.0  # -1 (negative) to 1 (positive)
    urgency_level: str = "normal"  # low, normal, high, critical
    suggested_next_actions: list[str] = field(default_factory=list)
    extracted_dates: list[dict] = field(default_factory=list)


# ── System prompts for extraction ──

SYSTEM_PROMPT_EXTRACT_ACTIONS = """Tu es un assistant juridique belge expert en analyse de transcriptions.

Analyse la transcription fournie et extrais les actions à effectuer.

Pour chaque action:
1. Identifie QUI doit faire QUOI
2. Détecte les délais mentionnés
3. Évalue la priorité (urgent, high, medium, low)
4. Note le moment exact dans la transcription

Format de réponse (JSON):
{
  "actions": [
    {
      "text": "Envoyer la requête au tribunal",
      "assignee": "Maître Dupont",
      "deadline": "2026-03-15",
      "priority": "high",
      "timestamp": 45.2
    }
  ]
}

RÈGLES:
- Sois précis et actionnable
- Capture TOUTES les tâches mentionnées
- Identifie les assignations même implicites
"""

SYSTEM_PROMPT_EXTRACT_DECISIONS = """Tu es un assistant juridique belge expert en analyse de décisions.

Extrais les décisions prises pendant la conversation.

Une décision est:
- Un choix définitif sur une action à entreprendre
- Une conclusion sur une stratégie
- Un accord entre les parties

Format JSON:
{
  "decisions": [
    {
      "text": "Nous acceptons la proposition de médiation",
      "decided_by": "Le client",
      "timestamp": 120.5
    }
  ]
}
"""

SYSTEM_PROMPT_EXTRACT_REFERENCES = """Tu es un assistant juridique belge expert en détection de références.

Détecte les références à:
- Dossiers (ex: "dossier Dupont", "affaire 2024/123")
- Contacts (noms de personnes)
- Documents (ex: "contrat du 15 janvier", "pièce 5")
- Articles de loi (ex: "article 1382 Code civil")

Format JSON:
{
  "references": [
    {
      "type": "case",
      "text": "dossier Dupont",
      "context": "Concernant le dossier Dupont, nous devons...",
      "timestamp": 30.0
    }
  ]
}
"""

SYSTEM_PROMPT_SUMMARIZE = """Tu es un assistant juridique belge expert en synthèse.

Résume cette transcription en exactement 3 phrases:
1. Sujet principal de la conversation
2. Points clés discutés
3. Prochaines étapes

Sois concis, précis et professionnel.
"""

SYSTEM_PROMPT_ANALYZE_SENTIMENT = """Analyse le sentiment général de cette conversation.

Retourne un score de -1 (très négatif) à +1 (très positif).
Considère:
- Ton général de la conversation
- Émotions exprimées
- Niveau de conflit ou d'accord
- Optimisme vs pessimisme

Format JSON:
{
  "sentiment": 0.3,
  "explanation": "Conversation constructive avec quelques inquiétudes"
}
"""


# ── Action Extraction Service ──


class ActionExtractionService:
    """Service to extract actionable insights from transcripts using AI."""

    def __init__(self, llm_gateway: Optional[LLMGateway] = None) -> None:
        self.llm = llm_gateway or LLMGateway()

    async def extract_insights(
        self,
        transcript_text: str,
        transcript_id: str,
        tenant_id: str,
        segments: Optional[list] = None,
    ) -> TranscriptInsights:
        """Extract complete insights from transcript.

        Args:
            transcript_text: Full transcript text
            transcript_id: Unique identifier for the transcript
            tenant_id: Tenant ID for rate limiting
            segments: Optional speaker segments with timestamps

        Returns:
            TranscriptInsights with all extracted data
        """
        # Create context chunk from transcript
        context = [
            ContextChunk(
                content=transcript_text,
                document_id=transcript_id,
            )
        ]

        # Extract in parallel
        actions_task = self._extract_actions(context, tenant_id, segments)
        decisions_task = self._extract_decisions(context, tenant_id, segments)
        references_task = self._extract_references(context, tenant_id, segments)
        summary_task = self._generate_summary(context, tenant_id)
        sentiment_task = self._analyze_sentiment(context, tenant_id)

        # Wait for all
        actions = await actions_task
        decisions = await decisions_task
        references = await references_task
        summary = await summary_task
        sentiment_result = await sentiment_task

        # Extract key topics (simple keyword extraction)
        key_topics = self._extract_topics(transcript_text)

        # Determine urgency based on actions and sentiment
        urgency = self._determine_urgency(actions, sentiment_result)

        # Suggest next actions
        next_actions = self._suggest_next_actions(actions, decisions)

        # Extract dates
        extracted_dates = self._extract_dates(transcript_text)

        return TranscriptInsights(
            transcript_id=transcript_id,
            summary=summary,
            action_items=actions,
            decisions=decisions,
            references=references,
            key_topics=key_topics,
            sentiment_score=sentiment_result.get("sentiment", 0.0),
            urgency_level=urgency,
            suggested_next_actions=next_actions,
            extracted_dates=extracted_dates,
        )

    async def _extract_actions(
        self,
        context: list[ContextChunk],
        tenant_id: str,
        segments: Optional[list] = None,
    ) -> list[ActionItem]:
        """Extract action items using AI."""
        response = await self.llm.generate(
            prompt="Extrais toutes les actions à effectuer de cette transcription.",
            context_chunks=context,
            system_prompt=SYSTEM_PROMPT_EXTRACT_ACTIONS,
            tenant_id=tenant_id,
            max_tokens=1500,
        )

        # Parse JSON response
        actions = self._parse_actions_response(response.text)
        return actions

    async def _extract_decisions(
        self,
        context: list[ContextChunk],
        tenant_id: str,
        segments: Optional[list] = None,
    ) -> list[ExtractedDecision]:
        """Extract decisions using AI."""
        response = await self.llm.generate(
            prompt="Extrais toutes les décisions prises dans cette conversation.",
            context_chunks=context,
            system_prompt=SYSTEM_PROMPT_EXTRACT_DECISIONS,
            tenant_id=tenant_id,
            max_tokens=1000,
        )

        return self._parse_decisions_response(response.text)

    async def _extract_references(
        self,
        context: list[ContextChunk],
        tenant_id: str,
        segments: Optional[list] = None,
    ) -> list[ExtractedReference]:
        """Extract references to cases, contacts, documents, etc."""
        response = await self.llm.generate(
            prompt="Détecte toutes les références à des dossiers, contacts, documents et lois.",
            context_chunks=context,
            system_prompt=SYSTEM_PROMPT_EXTRACT_REFERENCES,
            tenant_id=tenant_id,
            max_tokens=1000,
        )

        return self._parse_references_response(response.text)

    async def _generate_summary(
        self, context: list[ContextChunk], tenant_id: str
    ) -> str:
        """Generate 3-sentence summary."""
        response = await self.llm.generate(
            prompt="Résume cette transcription en 3 phrases.",
            context_chunks=context,
            system_prompt=SYSTEM_PROMPT_SUMMARIZE,
            tenant_id=tenant_id,
            max_tokens=300,
        )

        return response.text.strip()

    async def _analyze_sentiment(
        self, context: list[ContextChunk], tenant_id: str
    ) -> dict:
        """Analyze sentiment of the conversation."""
        response = await self.llm.generate(
            prompt="Analyse le sentiment général de cette conversation.",
            context_chunks=context,
            system_prompt=SYSTEM_PROMPT_ANALYZE_SENTIMENT,
            tenant_id=tenant_id,
            max_tokens=200,
        )

        return self._parse_sentiment_response(response.text)

    def _parse_actions_response(self, response_text: str) -> list[ActionItem]:
        """Parse LLM response to extract actions."""
        import json

        actions = []
        try:
            # Try to extract JSON from response
            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                for action_data in data.get("actions", []):
                    # Parse deadline if present
                    deadline = None
                    if action_data.get("deadline"):
                        try:
                            deadline = datetime.fromisoformat(action_data["deadline"])
                        except (ValueError, TypeError):
                            pass

                    actions.append(
                        ActionItem(
                            action_id=str(uuid.uuid4()),
                            text=action_data.get("text", ""),
                            assignee=action_data.get("assignee"),
                            deadline=deadline,
                            priority=action_data.get("priority", "medium"),
                            confidence=0.85,
                            source_segment_start=action_data.get("timestamp"),
                        )
                    )
        except json.JSONDecodeError:
            # Fallback: extract from text
            pass

        return actions

    def _parse_decisions_response(self, response_text: str) -> list[ExtractedDecision]:
        """Parse LLM response to extract decisions."""
        import json

        decisions = []
        try:
            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                for dec in data.get("decisions", []):
                    decisions.append(
                        ExtractedDecision(
                            decision_id=str(uuid.uuid4()),
                            text=dec.get("text", ""),
                            decided_by=dec.get("decided_by"),
                            timestamp=dec.get("timestamp"),
                            confidence=0.8,
                        )
                    )
        except json.JSONDecodeError:
            pass

        return decisions

    def _parse_references_response(self, response_text: str) -> list[ExtractedReference]:
        """Parse LLM response to extract references."""
        import json

        references = []
        try:
            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                for ref in data.get("references", []):
                    references.append(
                        ExtractedReference(
                            ref_id=str(uuid.uuid4()),
                            ref_type=ref.get("type", "unknown"),
                            text=ref.get("text", ""),
                            context=ref.get("context", ""),
                            timestamp=ref.get("timestamp"),
                            confidence=0.75,
                        )
                    )
        except json.JSONDecodeError:
            pass

        return references

    def _parse_sentiment_response(self, response_text: str) -> dict:
        """Parse sentiment analysis response."""
        import json

        try:
            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

        return {"sentiment": 0.0, "explanation": "Could not analyze sentiment"}

    def _extract_topics(self, text: str, max_topics: int = 5) -> list[str]:
        """Extract key topics using simple keyword extraction.

        In production, use TF-IDF or a topic modeling approach.
        """
        # Common legal French keywords
        keywords = [
            "contrat",
            "tribunal",
            "procédure",
            "délai",
            "audience",
            "jugement",
            "médiation",
            "négociation",
            "dossier",
            "requête",
            "conclusions",
            "preuve",
            "témoignage",
            "expertise",
        ]

        found_topics = []
        text_lower = text.lower()
        for keyword in keywords:
            if keyword in text_lower:
                found_topics.append(keyword)
                if len(found_topics) >= max_topics:
                    break

        return found_topics

    def _determine_urgency(
        self, actions: list[ActionItem], sentiment: dict
    ) -> str:
        """Determine urgency level based on actions and sentiment."""
        # Check for urgent/high priority actions
        urgent_count = sum(
            1 for a in actions if a.priority in ["urgent", "high"]
        )

        if urgent_count > 2:
            return "critical"
        elif urgent_count > 0:
            return "high"
        elif sentiment.get("sentiment", 0) < -0.5:
            return "high"  # Negative sentiment = potential issue
        else:
            return "normal"

    def _suggest_next_actions(
        self, actions: list[ActionItem], decisions: list[ExtractedDecision]
    ) -> list[str]:
        """Suggest next steps based on extracted data."""
        suggestions = []

        # Sort actions by priority and deadline
        sorted_actions = sorted(
            actions,
            key=lambda a: (
                {"urgent": 0, "high": 1, "medium": 2, "low": 3}.get(a.priority, 99),
                a.deadline or datetime.max,
            ),
        )

        # Suggest top 3 actions
        for action in sorted_actions[:3]:
            suggestions.append(f"• {action.text}")

        # Add decision-based suggestions
        if decisions:
            suggestions.append(
                f"• Documenter les {len(decisions)} décisions prises"
            )

        return suggestions

    def _extract_dates(self, text: str) -> list[dict]:
        """Extract dates mentioned in transcript."""
        # Match various date formats
        patterns = [
            r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}",  # DD/MM/YYYY or DD-MM-YYYY
            r"\d{4}[/-]\d{1,2}[/-]\d{1,2}",  # YYYY-MM-DD
            r"\d{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+\d{4}",
        ]

        extracted = []
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                extracted.append(
                    {"date_text": match.group(0), "position": match.start()}
                )

        return extracted[:10]  # Limit to first 10 dates
