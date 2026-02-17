"""Pydantic schemas for SENTINEL conflict detection API."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ── Type Aliases ──

ConflictType = Literal[
    "direct_opposition",
    "dual_representation",
    "former_client",
    "associate_conflict",
    "organizational",
    "familial",
    "business_interest",
    "financial_interest",
]


# ── Entity Reference ──


class EntityRef(BaseModel):
    """Reference to an entity involved in a conflict."""

    id: uuid.UUID = Field(..., description="Unique identifier of the entity")
    name: str = Field(..., description="Display name of the entity")
    type: Literal["Person", "Company"] = Field(
        ..., description="Type of entity (Person or Company)"
    )


# ── Conflict Detection ──


class ConflictDetail(BaseModel):
    """Detailed information about a detected conflict."""

    id: uuid.UUID = Field(..., description="Unique conflict identifier")
    conflict_type: ConflictType = Field(..., description="Type of conflict detected (8 patterns)")
    severity_score: int = Field(
        ..., ge=0, le=100, description="Severity score from 0 (low) to 100 (critical)"
    )
    description: str = Field(..., description="Human-readable conflict description")
    entities_involved: List[EntityRef] = Field(
        ..., description="Entities involved in this conflict"
    )
    detected_at: datetime = Field(..., description="When the conflict was detected")


class ConflictCheckRequest(BaseModel):
    """Request to check for conflicts involving a contact."""

    contact_id: uuid.UUID = Field(..., description="Contact to check for conflicts")
    case_id: Optional[uuid.UUID] = Field(
        None, description="Optional case context for the conflict check"
    )
    include_graph: bool = Field(
        False, description="Whether to include graph visualization data"
    )


class ConflictCheckResponse(BaseModel):
    """Response containing conflict check results."""

    conflicts: List[ConflictDetail] = Field(
        ..., description="List of detected conflicts"
    )
    total_count: int = Field(..., description="Total number of conflicts detected")
    highest_severity: int = Field(
        ..., ge=0, le=100, description="Highest severity score among all conflicts"
    )
    check_timestamp: datetime = Field(..., description="When the check was performed")


# ── Conflict Listing ──


class ConflictSummary(BaseModel):
    """Summary information for a conflict in list views."""

    id: uuid.UUID = Field(..., description="Unique conflict identifier")
    conflict_type: ConflictType = Field(..., description="Type of conflict")
    severity_score: int = Field(..., ge=0, le=100, description="Severity score")
    description: str = Field(..., description="Brief conflict description")
    entities_involved: List[EntityRef] = Field(..., description="Entities involved")
    detected_at: datetime = Field(..., description="Detection timestamp")
    status: Literal["active", "resolved", "dismissed"] = Field(
        ..., description="Current status of the conflict"
    )
    resolved_at: Optional[datetime] = Field(None, description="Resolution timestamp")


class PaginationInfo(BaseModel):
    """Pagination metadata for list responses."""

    page: int = Field(..., ge=1, description="Current page number")
    per_page: int = Field(..., ge=1, le=100, description="Items per page")
    total: int = Field(..., ge=0, description="Total number of items")
    total_pages: int = Field(..., ge=0, description="Total number of pages")


class ConflictListResponse(BaseModel):
    """Response for listing conflicts with pagination."""

    conflicts: List[ConflictSummary] = Field(..., description="List of conflicts")
    pagination: PaginationInfo = Field(..., description="Pagination information")


# ── Conflict Resolution ──


class ConflictResolveRequest(BaseModel):
    """Request to resolve a conflict."""

    resolution: Literal["refused", "waiver_obtained", "false_positive"] = Field(
        ..., description="Type of resolution applied"
    )
    notes: Optional[str] = Field(None, max_length=5000, description="Optional resolution notes")
    resolved_by: uuid.UUID = Field(..., description="User ID who resolved the conflict")


class ConflictResolveResponse(BaseModel):
    """Response after resolving a conflict."""

    id: uuid.UUID = Field(..., description="Conflict identifier")
    status: Literal["active", "resolved", "dismissed"] = Field(..., description="New status after resolution")
    resolved_at: datetime = Field(..., description="When the conflict was resolved")
    resolved_by: uuid.UUID = Field(..., description="User who resolved it")


# ── Graph Synchronization ──


class SyncRequest(BaseModel):
    """Request to synchronize entities to the knowledge graph."""

    entity_ids: Optional[List[uuid.UUID]] = Field(
        None, max_length=10000, description="Specific entities to sync (if not syncing all)"
    )
    sync_all: bool = Field(False, description="Sync all entities in tenant")
    limit: int = Field(
        1000, ge=1, le=10000, description="Maximum number of entities to sync"
    )


class SyncResponse(BaseModel):
    """Response after graph synchronization."""

    synced_count: int = Field(..., ge=0, description="Number of entities synced")
    failed_count: int = Field(..., ge=0, description="Number of entities that failed")
    duration_seconds: float = Field(..., ge=0, description="Time taken to sync")


# ── Graph Data ──


class GraphNode(BaseModel):
    """A node in the graph visualization."""

    id: str = Field(..., description="Node identifier")
    label: str = Field(..., description="Node type/label")
    name: str = Field(..., description="Display name")
    properties: Dict[str, Any] = Field(
        default_factory=dict, description="Additional node properties"
    )


class GraphEdge(BaseModel):
    """An edge/relationship in the graph visualization."""

    from_id: str = Field(..., alias="from", description="Source node ID")
    to_id: str = Field(..., alias="to", description="Target node ID")
    type: str = Field(..., description="Relationship type")
    properties: Dict[str, Any] = Field(
        default_factory=dict, description="Additional edge properties"
    )

    # Using populate_by_name to handle 'from' field (Python reserved keyword)
    model_config = {"populate_by_name": True}


class GraphDataResponse(BaseModel):
    """Response containing graph data for visualization."""

    nodes: List[GraphNode] = Field(..., description="Graph nodes")
    edges: List[GraphEdge] = Field(..., description="Graph edges/relationships")
    center_entity_id: uuid.UUID = Field(
        ..., description="Central entity the graph is focused on"
    )


# ── Entity Search ──


class EntitySearchResult(BaseModel):
    """Search result for entity search."""

    id: uuid.UUID = Field(..., description="Entity identifier")
    name: str = Field(..., description="Entity name")
    type: str = Field(..., description="Entity type")
    bce_number: Optional[str] = Field(None, description="BCE number if applicable")
    email: Optional[str] = Field(None, description="Email if applicable")
    phone: Optional[str] = Field(None, description="Phone if applicable")
    conflict_count: int = Field(
        0, ge=0, description="Number of active conflicts for this entity"
    )
    last_checked: Optional[datetime] = Field(
        None, description="Last conflict check timestamp"
    )


class EntitySearchResponse(BaseModel):
    """Response for entity search."""

    results: List[EntitySearchResult] = Field(..., description="Search results")
    total: int = Field(..., ge=0, description="Total matching entities")


# ── Alert Streaming ──


class AlertStreamEvent(BaseModel):
    """Server-sent event for real-time conflict alerts."""

    event_type: Literal["conflict_detected", "conflict_resolved"] = Field(
        ..., description="Type of alert event"
    )
    data: Dict[str, Any] = Field(..., description="Event-specific data payload")
    timestamp: datetime = Field(..., description="When the event occurred")
