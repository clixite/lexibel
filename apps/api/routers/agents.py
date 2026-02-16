"""Agent endpoints — due diligence, emotional radar, document assembly."""
from dataclasses import asdict
from fastapi import APIRouter, Depends, HTTPException

from apps.api.dependencies import get_current_user
from apps.api.schemas.agents import (
    AssembleDocumentRequest,
    AssembledDocumentResponse,
    DueDiligenceRequest,
    DueDiligenceResponse,
    EmotionalRadarRequest,
    EmotionalProfileResponse,
    TemplateListResponse,
    TemplateInfo,
    VLLMHealthResponse,
    LoRAAdapterResponse,
)
from apps.api.services.agents import AgentOrchestrator
from apps.api.services.vllm_service import StubVLLMService
from apps.api.services.lora_registry import LoRARegistry

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])

# Shared singletons
_orchestrator = AgentOrchestrator()
_vllm = StubVLLMService()
_lora_registry = LoRARegistry()


@router.post("/due-diligence/{case_id}", response_model=DueDiligenceResponse)
async def run_due_diligence(
    case_id: str,
    body: DueDiligenceRequest,
    user: dict = Depends(get_current_user),
):
    """Run automated due diligence analysis on a case."""
    tenant_id = user.get("tenant_id", "")
    report = _orchestrator.run_due_diligence(
        case_id=case_id,
        tenant_id=tenant_id,
        events=body.events,
    )
    return DueDiligenceResponse(**asdict(report))


@router.post("/emotional-radar/{case_id}", response_model=EmotionalProfileResponse)
async def run_emotional_radar(
    case_id: str,
    body: EmotionalRadarRequest,
    user: dict = Depends(get_current_user),
):
    """Analyze communication tone and detect escalation in a case."""
    tenant_id = user.get("tenant_id", "")
    profile = _orchestrator.run_emotional_radar(
        case_id=case_id,
        tenant_id=tenant_id,
        events=body.events,
    )
    return EmotionalProfileResponse(**asdict(profile))


@router.post("/assemble-document", response_model=AssembledDocumentResponse)
async def assemble_document(
    body: AssembleDocumentRequest,
    user: dict = Depends(get_current_user),
):
    """Assemble a legal document from a template."""
    try:
        doc = _orchestrator.assemble_document(
            template_name=body.template_name,
            case_data=body.case_data,
            variables=body.variables,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return AssembledDocumentResponse(**asdict(doc))


@router.get("/templates", response_model=TemplateListResponse)
async def list_templates(user: dict = Depends(get_current_user)):
    """List available document templates."""
    templates = _orchestrator.list_templates()
    return TemplateListResponse(
        templates=[TemplateInfo(**t) for t in templates]
    )


@router.get("/vllm/health", response_model=VLLMHealthResponse)
async def vllm_health(user: dict = Depends(get_current_user)):
    """Check vLLM service health."""
    healthy = await _vllm._check_health()
    models = await _vllm.list_models()
    return VLLMHealthResponse(
        status="healthy" if healthy else "unavailable",
        model=models[0].id if models else "",
        adapters=[a.name for a in _lora_registry.list_adapters()],
    )


@router.get("/lora/adapters", response_model=list[LoRAAdapterResponse])
async def list_lora_adapters(user: dict = Depends(get_current_user)):
    """List available LoRA adapters."""
    adapters = _lora_registry.list_adapters()
    return [
        LoRAAdapterResponse(
            name=a.name,
            path=a.lora_path,
            task_type=", ".join(a.task_types),
            language=", ".join(a.languages),
            base_model=a.base_model,
            priority=a.priority,
        )
        for a in adapters
    ]
