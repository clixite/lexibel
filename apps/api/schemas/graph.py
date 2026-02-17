"""Pydantic schemas for Knowledge Graph endpoints."""

from typing import Optional, Literal

from pydantic import BaseModel, Field


# ── Node / Relationship schemas ──


class GraphNodeResponse(BaseModel):
    id: str
    label: str
    name: str = ""
    properties: dict = {}


class GraphRelationshipResponse(BaseModel):
    from_id: str = Field(alias="from")
    to_id: str = Field(alias="to")
    type: str
    properties: dict = {}

    model_config = {"populate_by_name": True}


class GraphContextResponse(BaseModel):
    nodes: list[GraphNodeResponse] = []
    relationships: list[GraphRelationshipResponse] = []
    paths: list[list[str]] = []
    text_summary: str = ""
    entity_count: int = 0
    relationship_count: int = 0


# ── Case subgraph ──


class CaseSubgraphResponse(BaseModel):
    case_id: str
    nodes: list[GraphNodeResponse]
    relationships: list[GraphRelationshipResponse]
    total_nodes: int
    total_relationships: int


# ── Entity connections ──


class EntityConnectionResponse(BaseModel):
    entity_id: str
    entity_name: str
    connections: list[dict]
    total: int


# ── Graph search ──


class GraphSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    case_id: Optional[str] = None
    depth: int = Field(2, ge=1, le=5)


class GraphSearchResponse(BaseModel):
    context: GraphContextResponse
    query: str


# ── Conflict detection ──


class ConflictResponse(BaseModel):
    entity_id: str
    entity_name: str
    entity_type: str
    roles: list[str]
    confidence: float
    description: str = ""


class ConflictListResponse(BaseModel):
    case_id: str
    conflicts: list[ConflictResponse]
    total: int


# ── Similar cases ──


class SimilarCaseResponse(BaseModel):
    case_id: str
    case_title: str
    similarity_score: float
    shared_entities: list[str]
    shared_legal_concepts: list[str]


class SimilarCasesResponse(BaseModel):
    source_case_id: str
    similar_cases: list[SimilarCaseResponse]
    total: int


# ── Build trigger ──


class BuildRequest(BaseModel):
    documents: list[dict] = Field(
        default_factory=list, description="List of {id, text} dicts"
    )


class BuildResponse(BaseModel):
    case_id: str
    nodes_created: int
    nodes_merged: int
    relationships_created: int
    entities_extracted: int
    errors: list[str] = []


# ── NER extraction ──


class EntityResponse(BaseModel):
    text: str
    entity_type: str
    start: int
    end: int
    confidence: float
    metadata: dict = {}


# ── Advanced Conflict Detection (2026) ──


class ConflictPathResponse(BaseModel):
    """A path showing how conflict arises through the graph."""
    nodes: list[str] = []
    relationships: list[str] = []
    description: str = ""
    hops: int = 0


class AdvancedConflictResponse(BaseModel):
    """Enhanced conflict with multi-hop analysis and risk scoring."""
    conflict_id: str
    entity_id: str
    entity_name: str
    entity_type: str
    conflict_type: Literal[
        "direct_opposition",
        "dual_representation",
        "former_client",
        "associate_conflict",
        "organizational",
        "familial",
        "business_interest",
    ]
    severity: Literal["critical", "high", "medium", "low", "info"]
    confidence: float
    risk_score: float
    hop_distance: int
    description: str
    paths: list[ConflictPathResponse] = []
    network_centrality: float = 0.0
    recommendations: list[str] = []
    related_cases: list[str] = []


class ConflictReportResponse(BaseModel):
    """Comprehensive conflict analysis report."""
    case_id: str
    total_conflicts: int
    by_severity: dict[str, int] = {}
    by_type: dict[str, int] = {}
    conflicts: list[AdvancedConflictResponse] = []
    network_analysis: dict = {}
    recommendations: list[str] = []
    report_generated_at: str


class ConflictPredictionResponse(BaseModel):
    """Prediction of conflict risk for new entity."""
    case_id: str
    entity_id: str
    risk_probability: float
    risk_level: Literal["critical", "high", "medium", "low", "minimal"]
    recommendations: list[str] = []
    analysis_timestamp: str


# ── Graph Sync ──


class SyncResultResponse(BaseModel):
    """Result of a graph sync operation."""
    success: bool
    entity_id: str
    nodes_affected: int = 0
    relationships_affected: int = 0
    error: Optional[str] = None


class NetworkStatsResponse(BaseModel):
    """Network-wide graph statistics."""
    tenant_id: str
    total_nodes: int
    total_relationships: int
    nodes_by_type: dict[str, int]
    relationships_by_type: dict[str, int]
    network_density: float
    most_connected_entities: list[dict] = []
    stats_generated_at: str
