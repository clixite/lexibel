"""Graph router — Knowledge Graph and GraphRAG endpoints.

GET  /api/v1/graph/case/{case_id}                          — case subgraph
GET  /api/v1/graph/case/{case_id}/conflicts                — basic conflict detection
GET  /api/v1/graph/case/{case_id}/conflicts/advanced       — advanced multi-hop conflicts (2026)
GET  /api/v1/graph/case/{case_id}/conflicts/predict/{id}   — predict conflict risk (ML-powered)
GET  /api/v1/graph/case/{case_id}/similar                  — similar cases
GET  /api/v1/graph/entity/{entity_id}/connections          — entity neighborhood
POST /api/v1/graph/search                                  — graph-enhanced search
POST /api/v1/graph/build/{case_id}                         — trigger graph build
POST /api/v1/graph/sync/case/{case_id}                     — sync case to Neo4j
POST /api/v1/graph/sync/contact/{contact_id}               — sync contact to Neo4j
GET  /api/v1/graph/network/stats                           — network statistics
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException

from apps.api.dependencies import get_current_user
from apps.api.schemas.graph import (
    CaseSubgraphResponse,
    GraphNodeResponse,
    GraphRelationshipResponse,
    EntityConnectionResponse,
    GraphSearchRequest,
    GraphSearchResponse,
    GraphContextResponse,
    ConflictListResponse,
    ConflictResponse,
    SimilarCasesResponse,
    SimilarCaseResponse,
    BuildRequest,
    BuildResponse,
)
from apps.api.services.graph.neo4j_service import InMemoryGraphService
from apps.api.services.graph.graph_builder import GraphBuilder
from apps.api.services.graph.graph_rag_service import GraphRAGService
from apps.api.services.graph.conflict_detection_service import ConflictDetectionService
from apps.api.services.graph.graph_sync_service import GraphSyncService

router = APIRouter(prefix="/api/v1/graph", tags=["graph"])

# Shared in-memory graph for dev/test (production: Neo4j)
_graph = InMemoryGraphService()
_builder = GraphBuilder(graph_service=_graph)
_rag = GraphRAGService(graph_service=_graph)
_conflict_detector = ConflictDetectionService(graph_service=_graph)
_sync_service = GraphSyncService(graph_service=_graph)


def get_graph() -> InMemoryGraphService:
    return _graph


def get_builder() -> GraphBuilder:
    return _builder


def get_rag() -> GraphRAGService:
    return _rag


def get_conflict_detector() -> ConflictDetectionService:
    return _conflict_detector


def get_sync_service() -> GraphSyncService:
    return _sync_service


@router.get("/case/{case_id}", response_model=CaseSubgraphResponse)
async def get_case_subgraph(
    case_id: str,
    current_user: dict = Depends(get_current_user),
) -> CaseSubgraphResponse:
    """Get the full knowledge graph for a case."""
    tenant_id = str(current_user["tenant_id"])
    graph = get_graph()

    nodes, rels = graph.get_case_subgraph(case_id, tenant_id)

    return CaseSubgraphResponse(
        case_id=case_id,
        nodes=[
            GraphNodeResponse(
                id=n.id,
                label=n.label,
                name=n.properties.get("name", n.id),
                properties={k: v for k, v in n.properties.items() if k != "tenant_id"},
            )
            for n in nodes
        ],
        relationships=[
            GraphRelationshipResponse(
                **{
                    "from": r.from_id,
                    "to": r.to_id,
                    "type": r.rel_type,
                    "properties": r.properties,
                }
            )
            for r in rels
        ],
        total_nodes=len(nodes),
        total_relationships=len(rels),
    )


@router.get("/case/{case_id}/conflicts", response_model=ConflictListResponse)
async def detect_conflicts(
    case_id: str,
    current_user: dict = Depends(get_current_user),
) -> ConflictListResponse:
    """Detect entities with conflicting roles in a case."""
    tenant_id = str(current_user["tenant_id"])
    builder = get_builder()

    conflicts = builder.detect_conflicts(case_id, tenant_id)

    return ConflictListResponse(
        case_id=case_id,
        conflicts=[
            ConflictResponse(
                entity_id=c.entity_id,
                entity_name=c.entity_name,
                entity_type=c.entity_type,
                roles=c.roles,
                confidence=c.confidence,
                description=c.description,
            )
            for c in conflicts
        ],
        total=len(conflicts),
    )


@router.get("/case/{case_id}/similar", response_model=SimilarCasesResponse)
async def find_similar_cases(
    case_id: str,
    current_user: dict = Depends(get_current_user),
) -> SimilarCasesResponse:
    """Find cases similar to the given case based on shared entities."""
    tenant_id = str(current_user["tenant_id"])
    rag = get_rag()

    similar = rag.find_similar_cases(case_id, tenant_id)

    return SimilarCasesResponse(
        source_case_id=case_id,
        similar_cases=[
            SimilarCaseResponse(
                case_id=s.case_id,
                case_title=s.case_title,
                similarity_score=s.similarity_score,
                shared_entities=s.shared_entities,
                shared_legal_concepts=s.shared_legal_concepts,
            )
            for s in similar
        ],
        total=len(similar),
    )


@router.get("/entity/{entity_id}/connections", response_model=EntityConnectionResponse)
async def get_entity_connections(
    entity_id: str,
    current_user: dict = Depends(get_current_user),
) -> EntityConnectionResponse:
    """Get an entity's neighborhood in the graph."""
    tenant_id = str(current_user["tenant_id"])
    graph = get_graph()

    node = graph.get_node(entity_id, tenant_id)
    if not node:
        raise HTTPException(status_code=404, detail="Entity not found")

    neighbors = graph.get_neighbors(entity_id, tenant_id, depth=2)
    connections = []
    for n in neighbors:
        neighbor_node = n.get("node")
        if isinstance(neighbor_node, type(node)):
            connections.append(
                {
                    "id": neighbor_node.id,
                    "label": neighbor_node.label,
                    "name": neighbor_node.properties.get("name", neighbor_node.id),
                    "rel_type": n.get("rel_type", ""),
                    "direction": n.get("direction", ""),
                }
            )

    return EntityConnectionResponse(
        entity_id=entity_id,
        entity_name=node.properties.get("name", entity_id),
        connections=connections,
        total=len(connections),
    )


@router.post("/search", response_model=GraphSearchResponse)
async def graph_search(
    body: GraphSearchRequest,
    current_user: dict = Depends(get_current_user),
) -> GraphSearchResponse:
    """Graph-enhanced search combining NER + graph traversal."""
    tenant_id = str(current_user["tenant_id"])
    rag = get_rag()

    if body.case_id:
        context = rag.get_context_for_query(body.query, tenant_id, case_id=body.case_id)
    else:
        context = rag.graph_search(body.query, tenant_id, depth=body.depth)

    return GraphSearchResponse(
        query=body.query,
        context=GraphContextResponse(
            nodes=[
                GraphNodeResponse(
                    id=n["id"],
                    label=n["label"],
                    name=n.get("name", n["id"]),
                    properties=n.get("properties", {}),
                )
                for n in context.nodes
            ],
            relationships=[
                GraphRelationshipResponse(
                    **{
                        "from": r["from"],
                        "to": r["to"],
                        "type": r["type"],
                        "properties": r.get("properties", {}),
                    }
                )
                for r in context.relationships
            ],
            paths=context.paths,
            text_summary=context.text_summary,
            entity_count=context.entity_count,
            relationship_count=context.relationship_count,
        ),
    )


@router.post("/build/{case_id}", response_model=BuildResponse)
async def build_case_graph(
    case_id: str,
    body: BuildRequest,
    current_user: dict = Depends(get_current_user),
) -> BuildResponse:
    """Trigger graph build for a case from its documents."""
    tenant_id = str(current_user["tenant_id"])
    builder = get_builder()

    result = builder.process_case(case_id, body.documents, tenant_id)

    return BuildResponse(
        case_id=case_id,
        nodes_created=result.nodes_created,
        nodes_merged=result.nodes_merged,
        relationships_created=result.relationships_created,
        entities_extracted=result.entities_extracted,
        errors=result.errors,
    )


# ═══════════════════════════════════════════════════════════════════════════
# ADVANCED CONFLICT DETECTION (2026)
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/case/{case_id}/conflicts/advanced")
async def detect_advanced_conflicts(
    case_id: str,
    max_depth: int = 3,
    min_confidence: float = 0.3,
    current_user: dict = Depends(get_current_user),
):
    """Advanced multi-hop conflict detection with ML-powered scoring.

    Args:
        case_id: Case ID to analyze
        max_depth: Maximum graph traversal depth (1-5 hops)
        min_confidence: Minimum confidence threshold (0.0-1.0)

    Returns:
        Comprehensive conflict report with:
        - Direct conflicts (1-hop)
        - Associate conflicts (2-hop)
        - Complex network conflicts (3-hop)
        - Risk scores and network analysis
        - AI-powered recommendations
    """
    tenant_id = str(current_user["tenant_id"])
    detector = get_conflict_detector()

    report = detector.detect_all_conflicts(
        case_id=case_id,
        tenant_id=tenant_id,
        max_depth=max_depth,
        min_confidence=min_confidence,
    )

    return {
        "case_id": report.case_id,
        "total_conflicts": report.total_conflicts,
        "by_severity": {k.value: v for k, v in report.by_severity.items()},
        "by_type": {k.value: v for k, v in report.by_type.items()},
        "conflicts": [
            {
                "conflict_id": c.conflict_id,
                "entity_id": c.entity_id,
                "entity_name": c.entity_name,
                "entity_type": c.entity_type,
                "conflict_type": c.conflict_type.value,
                "severity": c.severity.value,
                "confidence": c.confidence,
                "risk_score": c.risk_score,
                "hop_distance": c.hop_distance,
                "description": c.description,
                "paths": [
                    {
                        "nodes": p.node_names,
                        "relationships": p.relationships,
                        "description": p.path_description,
                        "hops": p.hop_count,
                    }
                    for p in c.paths
                ],
                "network_centrality": c.network_centrality,
                "recommendations": c.recommendations,
                "related_cases": c.related_cases,
            }
            for c in report.conflicts
        ],
        "network_analysis": report.network_analysis,
        "recommendations": report.recommendations,
        "report_generated_at": report.report_generated_at,
    }


@router.get("/case/{case_id}/conflicts/predict/{entity_id}")
async def predict_conflict_risk(
    case_id: str,
    entity_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Predict conflict risk if new entity is added to case.

    Uses graph ML to estimate probability of future conflicts.

    Args:
        case_id: Current case ID
        entity_id: Potential new entity to add

    Returns:
        Conflict risk probability (0.0-1.0) and recommendations
    """
    tenant_id = str(current_user["tenant_id"])
    detector = get_conflict_detector()

    risk_probability = detector.predict_future_conflicts(
        case_id=case_id,
        new_entity_id=entity_id,
        tenant_id=tenant_id,
    )

    # Generate risk level and recommendations
    if risk_probability >= 0.8:
        risk_level = "critical"
        recommendations = [
            "High conflict risk detected",
            "Do not proceed without ethics review",
            "Consider alternative representation",
        ]
    elif risk_probability >= 0.6:
        risk_level = "high"
        recommendations = [
            "Significant conflict risk",
            "Conduct thorough conflict check",
            "Document decision process",
        ]
    elif risk_probability >= 0.4:
        risk_level = "medium"
        recommendations = [
            "Moderate conflict risk",
            "Review entity relationships",
            "Consider conflict waiver",
        ]
    elif risk_probability >= 0.2:
        risk_level = "low"
        recommendations = [
            "Low conflict risk",
            "Standard conflict check recommended",
        ]
    else:
        risk_level = "minimal"
        recommendations = [
            "Minimal conflict risk",
            "Safe to proceed with standard checks",
        ]

    return {
        "case_id": case_id,
        "entity_id": entity_id,
        "risk_probability": risk_probability,
        "risk_level": risk_level,
        "recommendations": recommendations,
        "analysis_timestamp": datetime.utcnow().isoformat(),
    }


# ═══════════════════════════════════════════════════════════════════════════
# GRAPH SYNC ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════


@router.post("/sync/case/{case_id}")
async def sync_case_to_graph(
    case_id: str,
    case_data: dict,
    current_user: dict = Depends(get_current_user),
):
    """Manually trigger sync of a case to Neo4j graph.

    Used for:
    - Initial case graph creation
    - Manual re-sync after updates
    - Recovery from sync failures

    Body should contain case data including parties, court, etc.
    """
    from apps.api.services.graph.graph_sync_service import SyncOperation

    tenant_id = str(current_user["tenant_id"])
    sync_service = get_sync_service()

    result = await sync_service.sync_case(
        case_id=case_id,
        case_data=case_data,
        tenant_id=tenant_id,
        operation=SyncOperation.CREATE,
    )

    return {
        "success": result.success,
        "case_id": result.entity_id,
        "nodes_affected": result.nodes_affected,
        "relationships_affected": result.relationships_affected,
        "error": result.error,
    }


@router.post("/sync/contact/{contact_id}")
async def sync_contact_to_graph(
    contact_id: str,
    contact_data: dict,
    current_user: dict = Depends(get_current_user),
):
    """Sync a contact (person/organization) to Neo4j graph."""
    from apps.api.services.graph.graph_sync_service import SyncOperation

    tenant_id = str(current_user["tenant_id"])
    sync_service = get_sync_service()

    result = await sync_service.sync_contact(
        contact_id=contact_id,
        contact_data=contact_data,
        tenant_id=tenant_id,
        operation=SyncOperation.CREATE,
    )

    return {
        "success": result.success,
        "contact_id": result.entity_id,
        "nodes_affected": result.nodes_affected,
        "relationships_affected": result.relationships_affected,
        "error": result.error,
    }


@router.get("/network/stats")
async def get_network_statistics(
    current_user: dict = Depends(get_current_user),
):
    """Get overall knowledge graph network statistics for tenant.

    Returns:
        - Total nodes by type
        - Total relationships by type
        - Network density
        - Most connected entities
        - Conflict hotspots
    """
    tenant_id = str(current_user["tenant_id"])
    graph = get_graph()

    # Get all nodes for tenant
    all_nodes = []
    all_rels = []

    # Count nodes by label
    nodes_by_type = {}
    for label in [
        "Case",
        "Person",
        "Organization",
        "Court",
        "Document",
        "LegalConcept",
    ]:
        nodes = graph.find_nodes_by_label(label, tenant_id)
        nodes_by_type[label] = len(nodes)
        all_nodes.extend(nodes)

    # Count relationships
    all_rels = [r for r in graph._relationships]
    rels_by_type = {}
    for rel in all_rels:
        rels_by_type[rel.rel_type] = rels_by_type.get(rel.rel_type, 0) + 1

    # Calculate network metrics
    total_nodes = len(all_nodes)
    total_rels = len(all_rels)

    # Graph density
    density = 0.0
    if total_nodes > 1:
        max_edges = total_nodes * (total_nodes - 1)
        density = total_rels / max_edges if max_edges > 0 else 0.0

    # Find most connected entities
    connection_counts = {}
    for rel in all_rels:
        connection_counts[rel.from_id] = connection_counts.get(rel.from_id, 0) + 1
        connection_counts[rel.to_id] = connection_counts.get(rel.to_id, 0) + 1

    # Get top 10 most connected
    node_map = {n.id: n for n in all_nodes}
    most_connected = []
    for node_id, count in sorted(
        connection_counts.items(), key=lambda x: x[1], reverse=True
    )[:10]:
        node = node_map.get(node_id)
        if node:
            most_connected.append(
                {
                    "entity_id": node.id,
                    "entity_name": node.properties.get("name", node.id),
                    "entity_type": node.label,
                    "connection_count": count,
                }
            )

    return {
        "tenant_id": tenant_id,
        "total_nodes": total_nodes,
        "total_relationships": total_rels,
        "nodes_by_type": nodes_by_type,
        "relationships_by_type": rels_by_type,
        "network_density": density,
        "most_connected_entities": most_connected,
        "stats_generated_at": datetime.utcnow().isoformat(),
    }
