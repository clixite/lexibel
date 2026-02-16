"""Pydantic schemas for AI agents endpoints."""
from pydantic import BaseModel, Field
from typing import Optional


# ── Due Diligence ──


class EntityRiskResponse(BaseModel):
    entity_name: str
    entity_type: str
    risk_level: str
    risk_score: float
    flags: list[str] = []
    sanctions_hit: bool = False
    bce_status: str = ""
    sources: list[str] = []


class DueDiligenceResponse(BaseModel):
    case_id: str
    generated_at: str = ""
    entities: list[EntityRiskResponse] = []
    risk_flags: list[str] = []
    sanctions_hits: int = 0
    overall_risk: str = "LOW"
    recommendations: list[str] = []
    sources: list[str] = []
    total_entities_checked: int = 0


class DueDiligenceRequest(BaseModel):
    events: list[dict] = Field(default_factory=list)
    documents_text: str = ""


# ── Emotional Radar ──


class EventToneResponse(BaseModel):
    event_id: str
    event_type: str
    date: str
    tone: str
    score: float
    keywords_found: list[str] = []
    flagged: bool = False
    flag_reason: str = ""


class EmotionalProfileResponse(BaseModel):
    case_id: str
    overall_tone: str
    overall_score: float
    trend: str
    escalation_risk: str
    events_analyzed: int = 0
    flagged_events: list[EventToneResponse] = []
    all_events: list[EventToneResponse] = []
    recommendations: list[str] = []


class EmotionalRadarRequest(BaseModel):
    events: list[dict] = Field(default_factory=list)


# ── Document Assembly ──


class AssembleDocumentRequest(BaseModel):
    template_name: str
    case_id: str = ""
    case_data: dict = Field(default_factory=dict)
    variables: dict = Field(default_factory=dict)


class AssembledDocumentResponse(BaseModel):
    template_name: str
    content: str
    format: str = "text"
    metadata: dict = {}
    variables_used: list[str] = []
    missing_variables: list[str] = []


class TemplateInfo(BaseModel):
    id: str
    name: str
    description: str = ""
    category: str = ""
    required_variables: list[str] = []
    optional_variables: list[str] = []


class TemplateListResponse(BaseModel):
    templates: list[TemplateInfo] = []


# ── vLLM ──


class VLLMHealthResponse(BaseModel):
    status: str
    model: str = ""
    adapters: list[str] = []


class LoRAAdapterResponse(BaseModel):
    name: str
    path: str
    task_type: str
    language: str = ""
    base_model: str = ""
    priority: int = 0
    enabled: bool = True
