"""GraphRAG service — graph-enhanced Retrieval-Augmented Generation.

Combines knowledge graph traversal with vector search to produce
enriched context for AI generation. Finds similar cases based on
shared entities and legal concepts.
"""

from collections import Counter
from dataclasses import dataclass, field
from typing import Optional

from apps.api.services.graph.neo4j_service import (
    InMemoryGraphService,
    GraphNode,
    GraphRelationship,
)
from apps.api.services.graph.ner_service import NERService


@dataclass
class GraphContext:
    """Context extracted from the knowledge graph for RAG."""

    nodes: list[dict] = field(default_factory=list)
    relationships: list[dict] = field(default_factory=list)
    paths: list[list[str]] = field(default_factory=list)
    text_summary: str = ""
    entity_count: int = 0
    relationship_count: int = 0


@dataclass
class SimilarCase:
    """A case similar to the query case based on shared graph entities."""

    case_id: str
    case_title: str
    similarity_score: float
    shared_entities: list[str]
    shared_legal_concepts: list[str]


class GraphRAGService:
    """Graph-enhanced RAG: combine graph context with vector search."""

    def __init__(self, graph_service: Optional[InMemoryGraphService] = None) -> None:
        self.graph = graph_service or InMemoryGraphService()
        self.ner = NERService()

    def get_context_for_query(
        self,
        query: str,
        tenant_id: str,
        case_id: Optional[str] = None,
    ) -> GraphContext:
        """Get graph context to enhance a RAG query.

        Extracts entities from the query, finds them in the graph,
        and traverses to build relevant context.

        Args:
            query: User's search query
            tenant_id: Tenant UUID
            case_id: Optional case ID to scope the search

        Returns:
            GraphContext with nodes, relationships, and summary
        """
        context = GraphContext()

        # Extract entities from query
        entities = self.ner.extract(query)
        if not entities:
            return context

        # Find matching nodes in graph (exact then substring)
        matched_node_ids: set[str] = set()

        for entity in entities:
            # Exact match first
            matching_nodes = self.graph.find_nodes_by_property(
                "name", entity.text, tenant_id
            )
            for node in matching_nodes:
                matched_node_ids.add(node.id)
            # Substring match fallback
            if not matching_nodes:
                fuzzy_nodes = self.graph.find_nodes_by_name_contains(
                    entity.text, tenant_id
                )
                for node in fuzzy_nodes:
                    matched_node_ids.add(node.id)

        # Also try raw query words for simple lookups
        if not matched_node_ids:
            for word in query.split():
                if len(word) >= 3:
                    fuzzy = self.graph.find_nodes_by_name_contains(word, tenant_id)
                    for node in fuzzy:
                        matched_node_ids.add(node.id)

        if not matched_node_ids:
            return context

        # Get subgraph for matched nodes + case context
        if case_id:
            case_nodes, case_rels = self.graph.get_case_subgraph(case_id, tenant_id)
            for node in case_nodes:
                matched_node_ids.add(node.id)

        # Expand to neighbors (1 hop)
        expanded_ids = set(matched_node_ids)
        for node_id in matched_node_ids:
            neighbors = self.graph.get_neighbors(node_id, tenant_id, depth=1)
            for n in neighbors:
                if isinstance(n.get("node"), GraphNode):
                    expanded_ids.add(n["node"].id)

        # Get full subgraph
        nodes, rels = self.graph.get_subgraph(expanded_ids, tenant_id)

        # Build context
        context.nodes = [
            {
                "id": n.id,
                "label": n.label,
                "name": n.properties.get("name", n.id),
                "properties": {
                    k: v for k, v in n.properties.items() if k not in ("tenant_id",)
                },
            }
            for n in nodes
        ]
        context.relationships = [
            {
                "from": r.from_id,
                "to": r.to_id,
                "type": r.rel_type,
                "properties": r.properties,
            }
            for r in rels
        ]
        context.entity_count = len(nodes)
        context.relationship_count = len(rels)

        # Generate text summary
        context.text_summary = self._generate_summary(nodes, rels)
        context.paths = self._extract_paths(nodes, rels)

        return context

    def graph_search(
        self,
        query: str,
        tenant_id: str,
        depth: int = 2,
    ) -> GraphContext:
        """Search the graph using NER-extracted entities.

        Args:
            query: Search query text
            tenant_id: Tenant UUID
            depth: Max traversal depth

        Returns:
            GraphContext with matching subgraph
        """
        entities = self.ner.extract(query)

        all_node_ids: set[str] = set()

        # Search by NER entities (exact + substring)
        for entity in entities:
            matching = self.graph.find_nodes_by_property("name", entity.text, tenant_id)
            if not matching:
                matching = self.graph.find_nodes_by_name_contains(
                    entity.text, tenant_id
                )
            for node in matching:
                all_node_ids.add(node.id)
                neighbors = self.graph.get_neighbors(node.id, tenant_id, depth=depth)
                for n in neighbors:
                    if isinstance(n.get("node"), GraphNode):
                        all_node_ids.add(n["node"].id)

        # Fallback: try raw query words
        if not all_node_ids:
            for word in query.split():
                if len(word) >= 3:
                    fuzzy = self.graph.find_nodes_by_name_contains(word, tenant_id)
                    for node in fuzzy:
                        all_node_ids.add(node.id)

        if not all_node_ids:
            return GraphContext()

        nodes, rels = self.graph.get_subgraph(all_node_ids, tenant_id)

        return GraphContext(
            nodes=[
                {
                    "id": n.id,
                    "label": n.label,
                    "name": n.properties.get("name", n.id),
                    "properties": n.properties,
                }
                for n in nodes
            ],
            relationships=[
                {
                    "from": r.from_id,
                    "to": r.to_id,
                    "type": r.rel_type,
                    "properties": r.properties,
                }
                for r in rels
            ],
            entity_count=len(nodes),
            relationship_count=len(rels),
            text_summary=self._generate_summary(nodes, rels),
        )

    def find_similar_cases(
        self,
        case_id: str,
        tenant_id: str,
    ) -> list[SimilarCase]:
        """Find cases similar to the given case based on shared entities.

        Compares the entity set (persons, orgs, legal concepts, courts)
        of the target case with all other cases in the graph.

        Args:
            case_id: Target case ID
            tenant_id: Tenant UUID

        Returns:
            List of SimilarCase sorted by similarity (descending)
        """
        # Get entities connected to the target case
        case_nodes, case_rels = self.graph.get_case_subgraph(case_id, tenant_id)

        target_entities: set[str] = set()
        target_concepts: set[str] = set()
        entity_names: dict[str, str] = {}

        for node in case_nodes:
            if node.id == case_id:
                continue
            name = node.properties.get("name", node.id)
            entity_names[node.id] = name
            if node.label == "LegalConcept":
                target_concepts.add(node.id)
            elif node.label in ("Person", "Organization", "Court"):
                target_entities.add(node.id)

        if not target_entities and not target_concepts:
            return []

        # Find all other cases
        all_cases = self.graph.find_nodes_by_label("Case", tenant_id)
        similar: list[SimilarCase] = []

        for other_case in all_cases:
            if other_case.id == case_id:
                continue

            other_nodes, _ = self.graph.get_case_subgraph(other_case.id, tenant_id)
            other_entity_ids = set()
            other_concept_ids = set()

            for node in other_nodes:
                if node.id == other_case.id:
                    continue
                if node.label == "LegalConcept":
                    other_concept_ids.add(node.id)
                elif node.label in ("Person", "Organization", "Court"):
                    other_entity_ids.add(node.id)

            # Compute similarity (Jaccard-like)
            shared_ent = target_entities & other_entity_ids
            shared_con = target_concepts & other_concept_ids
            all_items = (
                target_entities | target_concepts | other_entity_ids | other_concept_ids
            )

            if not all_items:
                continue

            # Weighted: legal concepts count more
            score = (len(shared_ent) + len(shared_con) * 2) / (
                len(all_items) + len(target_concepts | other_concept_ids)
            )

            if score > 0.01:
                similar.append(
                    SimilarCase(
                        case_id=other_case.id,
                        case_title=other_case.properties.get("name", other_case.id),
                        similarity_score=min(score, 1.0),
                        shared_entities=[entity_names.get(e, e) for e in shared_ent],
                        shared_legal_concepts=[
                            entity_names.get(c, c) for c in shared_con
                        ],
                    )
                )

        similar.sort(key=lambda s: s.similarity_score, reverse=True)
        return similar

    def _generate_summary(
        self, nodes: list[GraphNode], rels: list[GraphRelationship]
    ) -> str:
        """Generate a text summary of the graph context for LLM consumption."""
        if not nodes:
            return ""

        parts = []

        # Group nodes by label
        by_label: dict[str, list[str]] = {}
        for node in nodes:
            label = node.label
            name = node.properties.get("name", node.id)
            by_label.setdefault(label, []).append(name)

        for label, names in by_label.items():
            parts.append(f"{label}: {', '.join(names[:5])}")

        # Summarize relationships
        rel_types = Counter(r.rel_type for r in rels)
        if rel_types:
            rel_parts = [f"{t}({c})" for t, c in rel_types.most_common(5)]
            parts.append(f"Relations: {', '.join(rel_parts)}")

        return " | ".join(parts)

    def _extract_paths(
        self,
        nodes: list[GraphNode],
        rels: list[GraphRelationship],
    ) -> list[list[str]]:
        """Extract readable paths from the subgraph."""
        paths: list[list[str]] = []
        node_names = {n.id: n.properties.get("name", n.id) for n in nodes}

        for rel in rels[:10]:  # Limit paths
            from_name = node_names.get(rel.from_id, rel.from_id)
            to_name = node_names.get(rel.to_id, rel.to_id)
            paths.append([from_name, rel.rel_type, to_name])

        return paths
