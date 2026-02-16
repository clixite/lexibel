"""Neo4j graph database service — knowledge graph storage.

Connects to Neo4j (bolt://neo4j:7687). Tenant isolation via tenant_id
property on all nodes. Provides CRUD for nodes and relationships,
plus Cypher query execution.

Node types: Person, Organization, Case, Document, Event, LegalConcept
Relationship types: PARTY_TO, REPRESENTED_BY, RELATED_TO, REFERENCES,
                    OCCURRED_IN, FILED_AT, OPPOSED_TO
"""

import os
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional


# ── Constants ──

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "lexibel2026")

VALID_NODE_LABELS = {
    "Person",
    "Organization",
    "Case",
    "Document",
    "Event",
    "LegalConcept",
    "Court",
    "Location",
}

VALID_RELATIONSHIP_TYPES = {
    "PARTY_TO",
    "REPRESENTED_BY",
    "RELATED_TO",
    "REFERENCES",
    "OCCURRED_IN",
    "FILED_AT",
    "OPPOSED_TO",
    "AUTHORED_BY",
    "MENTIONS",
    "CITES",
    "ATTACHED_TO",
    "BELONGS_TO",
}


# ── Data classes ──


@dataclass
class GraphNode:
    """A node in the knowledge graph."""

    id: str
    label: str
    properties: dict = field(default_factory=dict)
    tenant_id: str = ""


@dataclass
class GraphRelationship:
    """A relationship between two nodes."""

    id: str
    from_id: str
    to_id: str
    rel_type: str
    properties: dict = field(default_factory=dict)


@dataclass
class GraphPath:
    """A path through the graph (sequence of nodes and relationships)."""

    nodes: list[GraphNode]
    relationships: list[GraphRelationship]
    length: int = 0


# ── Neo4j Service ──


class Neo4jService:
    """Neo4j graph database client.

    In production, uses the neo4j Python driver for Bolt protocol.
    Falls back to InMemoryGraphService for testing.
    """

    def __init__(
        self,
        uri: str = NEO4J_URI,
        user: str = NEO4J_USER,
        password: str = NEO4J_PASSWORD,
    ):
        self.uri = uri
        self.user = user
        self.password = password
        self._driver = None

    def _get_driver(self):
        """Get or create Neo4j driver (lazy init)."""
        if self._driver is None:
            try:
                import neo4j

                self._driver = neo4j.GraphDatabase.driver(
                    self.uri, auth=(self.user, self.password)
                )
            except ImportError:
                raise RuntimeError(
                    "neo4j driver not installed. Use InMemoryGraphService for testing."
                )
        return self._driver

    def close(self) -> None:
        """Close the driver connection."""
        if self._driver:
            self._driver.close()
            self._driver = None

    def create_node(
        self,
        label: str,
        properties: dict,
        tenant_id: str,
    ) -> GraphNode:
        """Create a node in the graph.

        Args:
            label: Node label (Person, Organization, Case, etc.)
            properties: Node properties dict
            tenant_id: Tenant UUID for isolation

        Returns:
            Created GraphNode
        """
        if label not in VALID_NODE_LABELS:
            raise ValueError(f"Invalid label: {label}. Valid: {VALID_NODE_LABELS}")

        node_id = properties.get("id") or str(uuid.uuid4())
        props = {**properties, "id": node_id, "tenant_id": tenant_id}

        driver = self._get_driver()
        with driver.session() as session:
            query = f"CREATE (n:{label} $props) RETURN n"
            session.run(query, props=props)

        return GraphNode(id=node_id, label=label, properties=props, tenant_id=tenant_id)

    def create_relationship(
        self,
        from_id: str,
        to_id: str,
        rel_type: str,
        properties: dict | None = None,
        tenant_id: str = "",
    ) -> GraphRelationship:
        """Create a relationship between two nodes.

        Args:
            from_id: Source node ID
            to_id: Target node ID
            rel_type: Relationship type
            properties: Optional relationship properties
            tenant_id: Tenant UUID for isolation

        Returns:
            Created GraphRelationship
        """
        if rel_type not in VALID_RELATIONSHIP_TYPES:
            raise ValueError(
                f"Invalid rel_type: {rel_type}. Valid: {VALID_RELATIONSHIP_TYPES}"
            )

        rel_id = str(uuid.uuid4())
        props = {**(properties or {}), "id": rel_id}

        driver = self._get_driver()
        with driver.session() as session:
            query = (
                "MATCH (a {id: $from_id, tenant_id: $tenant_id}), "
                "(b {id: $to_id, tenant_id: $tenant_id}) "
                f"CREATE (a)-[r:{rel_type} $props]->(b) RETURN r"
            )
            session.run(
                query, from_id=from_id, to_id=to_id, tenant_id=tenant_id, props=props
            )

        return GraphRelationship(
            id=rel_id, from_id=from_id, to_id=to_id, rel_type=rel_type, properties=props
        )

    def query(
        self,
        cypher: str,
        params: dict | None = None,
        tenant_id: str = "",
    ) -> list[dict]:
        """Execute a Cypher query with tenant isolation.

        Args:
            cypher: Cypher query string
            params: Query parameters
            tenant_id: Tenant UUID for isolation

        Returns:
            List of result records as dicts
        """
        query_params = {**(params or {}), "tenant_id": tenant_id}
        driver = self._get_driver()
        with driver.session() as session:
            result = session.run(cypher, **query_params)
            return [dict(record) for record in result]

    def get_node(self, node_id: str, tenant_id: str) -> Optional[GraphNode]:
        """Get a node by ID with tenant isolation."""
        driver = self._get_driver()
        with driver.session() as session:
            result = session.run(
                "MATCH (n {id: $id, tenant_id: $tid}) RETURN n, labels(n) as labels",
                id=node_id,
                tid=tenant_id,
            )
            record = result.single()
            if not record:
                return None
            node = record["n"]
            labels = record["labels"]
            return GraphNode(
                id=node_id,
                label=labels[0] if labels else "Unknown",
                properties=dict(node),
                tenant_id=tenant_id,
            )

    def get_neighbors(self, node_id: str, tenant_id: str, depth: int = 1) -> list[dict]:
        """Get neighboring nodes up to N hops."""
        driver = self._get_driver()
        with driver.session() as session:
            result = session.run(
                f"MATCH (n {{id: $id, tenant_id: $tid}})-[r*1..{depth}]-(m {{tenant_id: $tid}}) "
                "RETURN DISTINCT m, labels(m) as labels, type(r[0]) as rel_type",
                id=node_id,
                tid=tenant_id,
            )
            return [dict(record) for record in result]

    def delete_node(self, node_id: str, tenant_id: str) -> bool:
        """Delete a node and its relationships."""
        driver = self._get_driver()
        with driver.session() as session:
            result = session.run(
                "MATCH (n {id: $id, tenant_id: $tid}) DETACH DELETE n RETURN count(n) as deleted",
                id=node_id,
                tid=tenant_id,
            )
            record = result.single()
            return record and record["deleted"] > 0


# ── In-Memory Graph Service (for testing) ──


class InMemoryGraphService:
    """In-memory graph for testing without Neo4j."""

    def __init__(self) -> None:
        self._nodes: dict[str, GraphNode] = {}
        self._relationships: list[GraphRelationship] = []

    def reset(self) -> None:
        """Clear all data."""
        self._nodes.clear()
        self._relationships.clear()

    def close(self) -> None:
        """No-op for in-memory."""
        pass

    def create_node(
        self,
        label: str,
        properties: dict,
        tenant_id: str,
    ) -> GraphNode:
        if label not in VALID_NODE_LABELS:
            raise ValueError(f"Invalid label: {label}. Valid: {VALID_NODE_LABELS}")

        node_id = properties.get("id") or str(uuid.uuid4())
        props = {**properties, "id": node_id, "tenant_id": tenant_id}
        node = GraphNode(id=node_id, label=label, properties=props, tenant_id=tenant_id)
        self._nodes[node_id] = node
        return node

    def create_relationship(
        self,
        from_id: str,
        to_id: str,
        rel_type: str,
        properties: dict | None = None,
        tenant_id: str = "",
    ) -> GraphRelationship:
        if rel_type not in VALID_RELATIONSHIP_TYPES:
            raise ValueError(
                f"Invalid rel_type: {rel_type}. Valid: {VALID_RELATIONSHIP_TYPES}"
            )

        if from_id not in self._nodes:
            raise ValueError(f"Node {from_id} not found")
        if to_id not in self._nodes:
            raise ValueError(f"Node {to_id} not found")

        # Tenant isolation check
        if tenant_id:
            if self._nodes[from_id].tenant_id != tenant_id:
                raise ValueError(f"Node {from_id} belongs to different tenant")
            if self._nodes[to_id].tenant_id != tenant_id:
                raise ValueError(f"Node {to_id} belongs to different tenant")

        rel_id = str(uuid.uuid4())
        props = {**(properties or {}), "id": rel_id}
        rel = GraphRelationship(
            id=rel_id, from_id=from_id, to_id=to_id, rel_type=rel_type, properties=props
        )
        self._relationships.append(rel)
        return rel

    def get_node(self, node_id: str, tenant_id: str) -> Optional[GraphNode]:
        node = self._nodes.get(node_id)
        if node and node.tenant_id == tenant_id:
            return node
        return None

    def get_neighbors(self, node_id: str, tenant_id: str, depth: int = 1) -> list[dict]:
        """BFS to find neighbors up to depth hops."""
        if node_id not in self._nodes or self._nodes[node_id].tenant_id != tenant_id:
            return []

        visited: set[str] = {node_id}
        frontier: set[str] = {node_id}
        results: list[dict] = []

        for _ in range(depth):
            next_frontier: set[str] = set()
            for nid in frontier:
                for rel in self._relationships:
                    neighbor_id = None
                    if rel.from_id == nid and rel.to_id not in visited:
                        neighbor_id = rel.to_id
                    elif rel.to_id == nid and rel.from_id not in visited:
                        neighbor_id = rel.from_id

                    if neighbor_id and neighbor_id in self._nodes:
                        neighbor = self._nodes[neighbor_id]
                        if neighbor.tenant_id == tenant_id:
                            visited.add(neighbor_id)
                            next_frontier.add(neighbor_id)
                            results.append(
                                {
                                    "node": neighbor,
                                    "rel_type": rel.rel_type,
                                    "direction": "outgoing"
                                    if rel.from_id == nid
                                    else "incoming",
                                }
                            )
            frontier = next_frontier

        return results

    def get_subgraph(
        self, node_ids: set[str], tenant_id: str
    ) -> tuple[list[GraphNode], list[GraphRelationship]]:
        """Get subgraph containing specified nodes and their relationships."""
        nodes = [
            n
            for n in self._nodes.values()
            if n.id in node_ids and n.tenant_id == tenant_id
        ]
        rels = [
            r
            for r in self._relationships
            if r.from_id in node_ids and r.to_id in node_ids
        ]
        return nodes, rels

    def get_case_subgraph(
        self, case_id: str, tenant_id: str
    ) -> tuple[list[GraphNode], list[GraphRelationship]]:
        """Get the full subgraph for a case."""
        # Find case node
        case_node = None
        for node in self._nodes.values():
            if node.id == case_id and node.tenant_id == tenant_id:
                case_node = node
                break

        if not case_node:
            return [], []

        # BFS to get all connected nodes
        connected_ids: set[str] = {case_id}
        frontier: set[str] = {case_id}

        for _ in range(3):  # Max 3 hops from case
            next_frontier: set[str] = set()
            for nid in frontier:
                for rel in self._relationships:
                    if rel.from_id == nid and rel.to_id not in connected_ids:
                        neighbor = self._nodes.get(rel.to_id)
                        if neighbor and neighbor.tenant_id == tenant_id:
                            connected_ids.add(rel.to_id)
                            next_frontier.add(rel.to_id)
                    elif rel.to_id == nid and rel.from_id not in connected_ids:
                        neighbor = self._nodes.get(rel.from_id)
                        if neighbor and neighbor.tenant_id == tenant_id:
                            connected_ids.add(rel.from_id)
                            next_frontier.add(rel.from_id)
            frontier = next_frontier

        return self.get_subgraph(connected_ids, tenant_id)

    def find_nodes_by_label(self, label: str, tenant_id: str) -> list[GraphNode]:
        """Find all nodes with a given label for a tenant."""
        return [
            n
            for n in self._nodes.values()
            if n.label == label and n.tenant_id == tenant_id
        ]

    def find_nodes_by_property(
        self, key: str, value: Any, tenant_id: str
    ) -> list[GraphNode]:
        """Find nodes by a property value."""
        return [
            n
            for n in self._nodes.values()
            if n.tenant_id == tenant_id and n.properties.get(key) == value
        ]

    def find_nodes_by_name_contains(self, text: str, tenant_id: str) -> list[GraphNode]:
        """Find nodes whose name contains the text (case-insensitive), or vice versa."""
        text_lower = text.lower()
        return [
            n
            for n in self._nodes.values()
            if n.tenant_id == tenant_id
            and (
                text_lower in n.properties.get("name", "").lower()
                or n.properties.get("name", "").lower() in text_lower
            )
        ]

    def query(
        self,
        cypher: str,
        params: dict | None = None,
        tenant_id: str = "",
    ) -> list[dict]:
        """Stub for Cypher queries — returns empty in memory mode."""
        return []

    def delete_node(self, node_id: str, tenant_id: str) -> bool:
        node = self._nodes.get(node_id)
        if not node or node.tenant_id != tenant_id:
            return False
        del self._nodes[node_id]
        self._relationships = [
            r
            for r in self._relationships
            if r.from_id != node_id and r.to_id != node_id
        ]
        return True
