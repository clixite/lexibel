"""Pydantic schemas for Legal RAG endpoints."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ── Request Schemas ──


class LegalSearchRequest(BaseModel):
    """Legal search request."""

    query: str = Field(
        ..., min_length=1, max_length=2000, description="Natural language search query"
    )
    jurisdiction: Optional[str] = Field(
        None,
        description="Filter by jurisdiction: federal, wallonie, flandre, bruxelles, eu",
    )
    document_type: Optional[str] = Field(
        None, description="Filter by document type: code_civil, jurisprudence, etc."
    )
    date_from: Optional[datetime] = Field(
        None, description="Filter documents published after this date"
    )
    date_to: Optional[datetime] = Field(
        None, description="Filter documents published before this date"
    )
    limit: int = Field(10, ge=1, le=50, description="Maximum results to return")
    enable_reranking: bool = Field(True, description="Enable cross-encoder re-ranking")
    enable_multilingual: bool = Field(
        True, description="Enable FR/NL translation search"
    )


class LegalChatRequest(BaseModel):
    """Legal AI chat request."""

    message: str = Field(..., min_length=1, max_length=5000)
    case_id: Optional[str] = None
    conversation_id: Optional[str] = None
    max_tokens: int = Field(2000, ge=100, le=8000)


class ExplainArticleRequest(BaseModel):
    """Request to explain legal article in simple terms."""

    article_text: str = Field(..., min_length=1, max_length=5000)
    simplification_level: str = Field("medium", pattern="^(basic|medium|detailed)$")


class PredictJurisprudenceRequest(BaseModel):
    """Request to predict jurisprudence outcome."""

    case_facts: str = Field(..., min_length=10, max_length=10000)
    relevant_articles: list[str] = Field(default_factory=list)


class DetectConflictsRequest(BaseModel):
    """Request to detect conflicts between legal articles."""

    article1: str = Field(..., min_length=1)
    article2: str = Field(..., min_length=1)


class LegalTimelineRequest(BaseModel):
    """Request for law modification timeline."""

    law_reference: str = Field(..., min_length=1, max_length=200)


# ── Response Schemas ──


class LegalEntityResponse(BaseModel):
    """A detected legal entity."""

    entity_type: str
    text: str
    normalized: str
    confidence: float


class LegalSearchResultItem(BaseModel):
    """A single legal search result."""

    chunk_text: str
    score: float
    source: str
    document_type: str
    jurisdiction: str
    article_number: Optional[str] = None
    date_published: Optional[datetime] = None
    url: Optional[str] = None
    page_number: Optional[int] = None
    highlighted_passages: list[str] = []
    related_articles: list[str] = []
    entities: list[LegalEntityResponse] = []


class LegalSearchResponse(BaseModel):
    """Legal search response."""

    query: str
    expanded_query: Optional[str] = None
    results: list[LegalSearchResultItem]
    total: int
    search_time_ms: float
    suggested_queries: list[str] = []
    detected_entities: list[LegalEntityResponse] = []


class LegalChatMessage(BaseModel):
    """A chat message in conversation."""

    role: str  # user, assistant
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    sources: list[LegalSearchResultItem] = []


class LegalChatResponse(BaseModel):
    """Legal AI chat response."""

    message: LegalChatMessage
    conversation_id: str
    related_documents: list[LegalSearchResultItem] = []
    suggested_followups: list[str] = []


class ExplainArticleResponse(BaseModel):
    """Article explanation response."""

    original_text: str
    simplified_explanation: str
    key_points: list[str] = []
    related_articles: list[str] = []


class JurisprudencePrediction(BaseModel):
    """Jurisprudence prediction result."""

    predicted_outcome: str
    confidence: float
    similar_cases: list[dict] = []
    reasoning: str = ""


class ConflictDetectionResponse(BaseModel):
    """Legal conflict detection response."""

    has_conflict: bool
    explanation: str
    severity: str = "none"  # none, minor, major, critical
    recommendations: list[str] = []


class LegalTimelineEvent(BaseModel):
    """A single event in legal timeline."""

    date: datetime
    change: str
    source: str
    type: str = "modification"  # creation, modification, abrogation


class LegalTimelineResponse(BaseModel):
    """Legal timeline response."""

    law_reference: str
    events: list[LegalTimelineEvent]
    current_version: str = ""
