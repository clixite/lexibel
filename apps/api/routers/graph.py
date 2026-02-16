"""Graph router — Knowledge Graph and GraphRAG endpoints.

GET  /api/v1/graph/case/{case_id}            — case subgraph
GET  /api/v1/graph/case/{case_id}/conflicts   — conflict detection
GET  /api/v1/graph/case/{case_id}/similar      — similar cases
GET  /api/v1/graph/entity/{entity_id}/connections — entity neighborhood
POST /api/v1/graph/search                      — graph-enhanced search
POST /api/v1/graph/build/{case_id}             — trigger graph build
"""

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

router = APIRouter(prefix="/api/v1/graph", tags=["graph"])

# Shared in-memory graph for dev/test (production: Neo4j)
_graph = InMemoryGraphService()
_builder = GraphBuilder(graph_service=_graph)
_rag = GraphRAGService(graph_service=_graph)


def get_graph() -> InMemoryGraphService:
    return _graph


def get_builder() -> GraphBuilder:
    return _builder


def get_rag() -> GraphRAGService:
    return _rag


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
