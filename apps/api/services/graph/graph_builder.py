"""GraphBuilder — orchestrate entity extraction and graph population.

Processes documents and cases: extracts entities via NER, creates/merges
graph nodes, creates relationships. Detects conflicts (entity appearing
on both sides of a case).
"""
import uuid
from dataclasses import dataclass, field
from typing import Optional

from apps.api.services.graph.neo4j_service import (
    InMemoryGraphService,
    GraphNode,
    GraphRelationship,
)
from apps.api.services.graph.ner_service import NERService, Entity


@dataclass
class BuildResult:
    """Result of a graph build operation."""
    nodes_created: int = 0
    nodes_merged: int = 0
    relationships_created: int = 0
    entities_extracted: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class Conflict:
    """A detected conflict — entity appears on both sides of a case."""
    entity_id: str
    entity_name: str
    entity_type: str
    roles: list[str]  # e.g. ["plaintiff_witness", "defendant_counsel"]
    confidence: float = 0.0
    description: str = ""


# Entity type to graph label mapping
ENTITY_TYPE_TO_LABEL = {
    "PERSON": "Person",
    "ORGANIZATION": "Organization",
    "COURT": "Court",
    "LOCATION": "Location",
    "LEGAL_REFERENCE": "LegalConcept",
    "DATE": "Event",
    "MONETARY_AMOUNT": "Event",
}


class GraphBuilder:
    """Orchestrate NER extraction and knowledge graph population."""

    def __init__(self, graph_service: Optional[InMemoryGraphService] = None) -> None:
        self.graph = graph_service or InMemoryGraphService()
        self.ner = NERService()

    def process_document(
        self,
        doc_id: str,
        text: str,
        case_id: str,
        tenant_id: str,
    ) -> BuildResult:
        """Extract entities from a document and populate the graph.

        Args:
            doc_id: Document ID
            text: Document text content
            case_id: Associated case ID
            tenant_id: Tenant UUID

        Returns:
            BuildResult with counts
        """
        result = BuildResult()

        # Extract entities
        entities = self.ner.extract(text)
        result.entities_extracted = len(entities)

        # Ensure case node exists
        case_node = self._ensure_node(
            label="Case",
            name=case_id,
            properties={"id": case_id, "type": "case"},
            tenant_id=tenant_id,
            result=result,
        )

        # Ensure document node exists
        doc_node = self._ensure_node(
            label="Document",
            name=doc_id,
            properties={"id": doc_id, "type": "document"},
            tenant_id=tenant_id,
            result=result,
        )

        # Link document to case
        self._ensure_relationship(
            from_id=doc_node.id,
            to_id=case_node.id,
            rel_type="ATTACHED_TO",
            tenant_id=tenant_id,
            result=result,
        )

        # Process each entity
        for entity in entities:
            label = ENTITY_TYPE_TO_LABEL.get(entity.entity_type)
            if not label:
                continue

            # Create/merge entity node
            entity_node = self._ensure_node(
                label=label,
                name=entity.text,
                properties={
                    "name": entity.text,
                    "entity_type": entity.entity_type,
                    "confidence": entity.confidence,
                },
                tenant_id=tenant_id,
                result=result,
            )

            # Link entity to document
            self._ensure_relationship(
                from_id=doc_node.id,
                to_id=entity_node.id,
                rel_type="MENTIONS",
                properties={"start": entity.start, "end": entity.end},
                tenant_id=tenant_id,
                result=result,
            )

            # Link entity to case based on type
            rel_type = self._entity_to_case_rel(entity.entity_type)
            if rel_type:
                self._ensure_relationship(
                    from_id=entity_node.id,
                    to_id=case_node.id,
                    rel_type=rel_type,
                    tenant_id=tenant_id,
                    result=result,
                )

        return result

    def process_case(
        self,
        case_id: str,
        documents: list[dict],
        tenant_id: str,
    ) -> BuildResult:
        """Build full case graph from all documents.

        Args:
            case_id: Case ID
            documents: List of dicts with doc_id and text
            tenant_id: Tenant UUID

        Returns:
            Aggregated BuildResult
        """
        total = BuildResult()

        for doc in documents:
            doc_result = self.process_document(
                doc_id=doc.get("id", str(uuid.uuid4())),
                text=doc.get("text", ""),
                case_id=case_id,
                tenant_id=tenant_id,
            )
            total.nodes_created += doc_result.nodes_created
            total.nodes_merged += doc_result.nodes_merged
            total.relationships_created += doc_result.relationships_created
            total.entities_extracted += doc_result.entities_extracted
            total.errors.extend(doc_result.errors)

        return total

    def detect_conflicts(
        self,
        case_id: str,
        tenant_id: str,
    ) -> list[Conflict]:
        """Detect if any entity appears on both sides of a case.

        Checks for persons/organizations that are linked to the case
        with conflicting roles (e.g., appears as both plaintiff's contact
        and defendant's contact).

        Args:
            case_id: Case ID
            tenant_id: Tenant UUID

        Returns:
            List of Conflict objects
        """
        conflicts: list[Conflict] = []

        # Get case subgraph
        nodes, rels = self.graph.get_case_subgraph(case_id, tenant_id)

        # Find all person/org nodes connected to the case
        entity_roles: dict[str, list[str]] = {}  # entity_id -> [roles]
        entity_info: dict[str, dict] = {}

        for node in nodes:
            if node.label in ("Person", "Organization"):
                roles = []
                for rel in rels:
                    if rel.from_id == node.id or rel.to_id == node.id:
                        role = rel.properties.get("role", rel.rel_type)
                        roles.append(role)

                if roles:
                    entity_roles[node.id] = roles
                    entity_info[node.id] = {
                        "name": node.properties.get("name", node.id),
                        "type": node.label,
                    }

        # Check for conflicts: entity with multiple different roles
        opposing_role_pairs = {
            ("PARTY_TO", "OPPOSED_TO"),
            ("REPRESENTED_BY", "OPPOSED_TO"),
        }

        for entity_id, roles in entity_roles.items():
            unique_roles = set(roles)
            if len(unique_roles) > 1:
                # Check if any roles are conflicting
                for r1 in unique_roles:
                    for r2 in unique_roles:
                        if r1 != r2 and (r1, r2) in opposing_role_pairs:
                            info = entity_info[entity_id]
                            conflicts.append(Conflict(
                                entity_id=entity_id,
                                entity_name=info["name"],
                                entity_type=info["type"],
                                roles=list(unique_roles),
                                confidence=0.8,
                                description=f"{info['name']} has conflicting roles: {', '.join(unique_roles)}",
                            ))

        return conflicts

    def _ensure_node(
        self,
        label: str,
        name: str,
        properties: dict,
        tenant_id: str,
        result: BuildResult,
    ) -> GraphNode:
        """Create or find an existing node (merge by name + label + tenant)."""
        # Check if node already exists
        existing = self.graph.find_nodes_by_property("name", name, tenant_id)
        for node in existing:
            if node.label == label:
                result.nodes_merged += 1
                return node

        # Also check by ID
        node_id = properties.get("id")
        if node_id:
            existing_by_id = self.graph.get_node(node_id, tenant_id)
            if existing_by_id:
                result.nodes_merged += 1
                return existing_by_id

        # Create new node
        try:
            node = self.graph.create_node(label, properties, tenant_id)
            result.nodes_created += 1
            return node
        except Exception as e:
            result.errors.append(f"Failed to create {label} node '{name}': {e}")
            # Return a stub node so processing can continue
            return GraphNode(id=str(uuid.uuid4()), label=label, properties=properties, tenant_id=tenant_id)

    def _ensure_relationship(
        self,
        from_id: str,
        to_id: str,
        rel_type: str,
        tenant_id: str,
        result: BuildResult,
        properties: dict | None = None,
    ) -> Optional[GraphRelationship]:
        """Create a relationship if it doesn't already exist."""
        # Check for existing relationship
        for rel in self.graph._relationships:
            if rel.from_id == from_id and rel.to_id == to_id and rel.rel_type == rel_type:
                return rel

        try:
            rel = self.graph.create_relationship(from_id, to_id, rel_type, properties, tenant_id)
            result.relationships_created += 1
            return rel
        except Exception as e:
            result.errors.append(f"Failed to create {rel_type} relationship: {e}")
            return None

    @staticmethod
    def _entity_to_case_rel(entity_type: str) -> Optional[str]:
        """Map entity type to case relationship type."""
        mapping = {
            "PERSON": "PARTY_TO",
            "ORGANIZATION": "PARTY_TO",
            "COURT": "FILED_AT",
            "LEGAL_REFERENCE": "REFERENCES",
            "LOCATION": "OCCURRED_IN",
        }
        return mapping.get(entity_type)
