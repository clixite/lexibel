"""Pydantic schemas for Knowledge Graph endpoints."""
from typing import Optional

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
    documents: list[dict] = Field(default_factory=list, description="List of {id, text} dicts")


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
