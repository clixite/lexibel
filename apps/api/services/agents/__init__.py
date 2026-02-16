"""Agent Orchestrator — route agent requests, manage execution, collect results."""
from dataclasses import dataclass, field
from typing import Optional

from apps.api.services.agents.due_diligence_agent import DueDiligenceAgent, DueDiligenceReport
from apps.api.services.agents.emotional_radar import EmotionalRadar, EmotionalProfile
from apps.api.services.agents.document_assembler import DocumentAssembler, AssembledDocument


@dataclass
class AgentResult:
    """Combined result from an agent execution."""
    agent_name: str
    status: str = "completed"  # completed, failed, partial
    error: Optional[str] = None
    data: Optional[dict] = None


class AgentOrchestrator:
    """Route agent requests and manage execution."""

    def __init__(self) -> None:
        self.due_diligence = DueDiligenceAgent()
        self.emotional_radar = EmotionalRadar()
        self.document_assembler = DocumentAssembler()

    def run_due_diligence(self, case_id: str, tenant_id: str, events: list[dict] | None = None) -> DueDiligenceReport:
        """Run due diligence analysis on a case."""
        return self.due_diligence.analyze(case_id, tenant_id, events=events or [])

    def run_emotional_radar(self, case_id: str, tenant_id: str, events: list[dict] | None = None) -> EmotionalProfile:
        """Run emotional radar on case communications."""
        return self.emotional_radar.analyze(case_id, tenant_id, events=events or [])

    def assemble_document(
        self,
        template_name: str,
        case_data: dict,
        variables: dict | None = None,
    ) -> AssembledDocument:
        """Assemble a legal document from a template."""
        return self.document_assembler.assemble(template_name, case_data, variables or {})

    def list_templates(self) -> list[dict]:
        """List available document templates."""
        return self.document_assembler.list_templates()


__all__ = [
    "AgentOrchestrator",
    "AgentResult",
    "DueDiligenceAgent",
    "DueDiligenceReport",
    "EmotionalRadar",
    "EmotionalProfile",
    "DocumentAssembler",
    "AssembledDocument",
]
