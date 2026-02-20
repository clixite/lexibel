"""Brain Intelligence API schemas."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Request schemas ──────────────────────────────────────────────────


class CaseAnalysisRequest(BaseModel):
    case_id: uuid.UUID
    include_strategy: bool = True
    include_completeness: bool = True


class BrainSummaryRequest(BaseModel):
    days_ahead: int = 14
    include_workload: bool = True


class ActionFeedbackRequest(BaseModel):
    action_id: uuid.UUID
    feedback: str = Field(pattern=r"^(approved|rejected|deferred)$")
    notes: str | None = None


class InsightDismissRequest(BaseModel):
    insight_id: uuid.UUID
    reason: str | None = None


class CommunicationScoreRequest(BaseModel):
    case_id: uuid.UUID
    include_sentiment: bool = True


# ── Response schemas ─────────────────────────────────────────────────


class RiskFactor(BaseModel):
    name: str
    score: int = Field(ge=0, le=100)
    weight: float = Field(ge=0, le=1)
    description: str
    severity: str  # low, medium, high, critical


class RiskAssessmentResponse(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    level: str  # low, medium, high, critical
    factors: list[RiskFactor]
    recommendations: list[str]


class CompletenessItem(BaseModel):
    element: str
    label_fr: str
    present: bool
    critical: bool


class CompletenessResponse(BaseModel):
    score: int = Field(ge=0, le=100)
    present: list[CompletenessItem]
    missing: list[CompletenessItem]
    matter_type: str


class StrategySuggestionResponse(BaseModel):
    title: str
    description: str
    priority: str  # high, medium, low
    rationale: str
    estimated_impact: str  # high, medium, low
    action_type: str  # negotiation, litigation, mediation, documentation, investigation


class CaseHealthResponse(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    status: str  # healthy, attention_needed, at_risk, critical
    components: dict[
        str, int
    ]  # completeness, activity, billing, communication, deadlines
    trend: str  # improving, stable, declining


class ActionSuggestionResponse(BaseModel):
    action_type: str  # alert, draft, suggestion, follow_up, review
    title: str
    description: str
    priority: str  # critical, urgent, normal
    confidence: float = Field(ge=0, le=1)
    trigger_source: str  # analysis, deadline, communication, document
    generated_content: str | None = None


class CaseAnalysisResponse(BaseModel):
    case_id: str
    risk_assessment: RiskAssessmentResponse
    completeness: CompletenessResponse | None = None
    health: CaseHealthResponse
    strategy_suggestions: list[StrategySuggestionResponse] = []
    suggested_actions: list[ActionSuggestionResponse] = []
    analyzed_at: datetime


class InsightResponse(BaseModel):
    id: str | None = None
    insight_type: str  # risk, opportunity, contradiction, deadline, gap, billing
    severity: str  # low, medium, high, critical
    title: str
    description: str
    suggested_actions: list[str] = []
    case_id: str | None = None
    dismissed: bool = False


class DeadlineResponse(BaseModel):
    title: str
    date: str
    days_remaining: int
    urgency: str  # critical, urgent, attention, normal
    case_id: str | None = None
    case_title: str | None = None
    legal_basis: str | None = None  # e.g. "Art. 1051 C.J."


class WorkloadWeek(BaseModel):
    week_start: str
    week_end: str
    deadline_count: int
    cases_count: int
    estimated_hours: float
    overload: bool


class BrainSummaryResponse(BaseModel):
    total_active_cases: int
    risk_distribution: dict[str, int]  # low: X, medium: Y, high: Z, critical: W
    critical_deadlines: list[DeadlineResponse]
    pending_actions: list[ActionSuggestionResponse]
    recent_insights: list[InsightResponse]
    workload_next_weeks: list[WorkloadWeek] = []
    cases_needing_attention: list[dict]  # [{case_id, title, reason, urgency}]
    stats: dict  # aggregate stats


class CommunicationHealthResponse(BaseModel):
    case_id: str
    overall_score: int = Field(ge=0, le=100)
    status: str  # healthy, needs_attention, critical
    last_client_contact: str | None = None
    days_since_last_contact: int | None = None
    response_time_avg_hours: float | None = None
    gaps: list[dict]  # [{party, days_since_contact, severity}]
    sentiment_trend: str | None = None  # improving, stable, deteriorating
    recommendations: list[str] = []


class BrainActionResponse(BaseModel):
    id: str
    case_id: str
    action_type: str
    priority: str
    status: str
    confidence_score: float
    trigger_source: str
    generated_content: str | None = None
    created_at: str


class BrainInsightListResponse(BaseModel):
    items: list[InsightResponse]
    total: int


# ── Dossier creation assist schemas ─────────────────────────────────


class DossierCreationAssistRequest(BaseModel):
    matter_type: str = Field(
        ...,
        description="Type de matiere: civil, penal, commercial, social, fiscal, family, administrative, immobilier, construction, societes",
    )
    description: str = Field(..., min_length=1, description="Description de l'affaire")
    client_name: Optional[str] = None


class DossierCreationAssistResponse(BaseModel):
    suggested_jurisdiction: Optional[str] = None
    suggested_sub_type: Optional[str] = None
    applicable_deadlines: list[dict] = Field(
        default_factory=list,
        description="Delais applicables: [{name, duration, description}]",
    )
    required_documents: list[str] = Field(default_factory=list)
    risk_points: list[str] = Field(default_factory=list)
    strategy_notes: str = ""
    estimated_complexity: str = Field(
        "moderate", description="simple, moderate, complex"
    )
    belgian_legal_references: list[str] = Field(default_factory=list)


# ── Contact creation assist schemas ──────────────────────────────────


class ContactAssistRequest(BaseModel):
    type: str = Field(..., pattern="^(natural|legal)$")
    full_name: str = Field(..., min_length=1)
    bce_number: Optional[str] = None


class ContactAssistResponse(BaseModel):
    suggested_fields: dict = Field(
        default_factory=dict, description="Champs pre-remplis suggeres"
    )
    bce_info: Optional[dict] = Field(
        None, description="Informations BCE si numero fourni"
    )
    duplicate_warning: Optional[dict] = Field(
        None, description="Alerte de doublon potentiel"
    )
    compliance_notes: list[str] = Field(
        default_factory=list, description="Notes RGPD et protection des donnees"
    )
    relationship_suggestions: list[str] = Field(
        default_factory=list, description="Suggestions de categorisation"
    )
