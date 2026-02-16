"""Tests for LXB-050-053: Knowledge Graph, NER, GraphBuilder."""

import uuid

import pytest
from fastapi.testclient import TestClient

from apps.api.services.graph.neo4j_service import (
    InMemoryGraphService,
    VALID_NODE_LABELS,
    VALID_RELATIONSHIP_TYPES,
)
from apps.api.services.graph.ner_service import NERService
from apps.api.services.graph.graph_builder import GraphBuilder
from apps.api.main import app
from apps.api.routers.graph import _graph


TENANT_ID = str(uuid.uuid4())
OTHER_TENANT = str(uuid.uuid4())
USER_ID = str(uuid.uuid4())


def _auth_headers() -> dict:
    return {
        "X-Tenant-ID": TENANT_ID,
        "X-User-ID": USER_ID,
        "X-User-Role": "super_admin",
        "X-User-Email": "test@lexibel.be",
    }


# ── Neo4j InMemoryGraphService tests ──


class TestInMemoryGraph:
    def setup_method(self):
        self.graph = InMemoryGraphService()

    def test_create_node(self):
        node = self.graph.create_node("Person", {"name": "Jean Dupont"}, TENANT_ID)
        assert node.label == "Person"
        assert node.properties["name"] == "Jean Dupont"
        assert node.tenant_id == TENANT_ID

    def test_create_node_invalid_label(self):
        with pytest.raises(ValueError, match="Invalid label"):
            self.graph.create_node("InvalidType", {"name": "X"}, TENANT_ID)

    def test_create_relationship(self):
        n1 = self.graph.create_node("Person", {"name": "Jean"}, TENANT_ID)
        n2 = self.graph.create_node("Case", {"name": "Dossier X"}, TENANT_ID)
        rel = self.graph.create_relationship(
            n1.id, n2.id, "PARTY_TO", tenant_id=TENANT_ID
        )
        assert rel.rel_type == "PARTY_TO"
        assert rel.from_id == n1.id
        assert rel.to_id == n2.id

    def test_create_relationship_invalid_type(self):
        n1 = self.graph.create_node("Person", {"name": "A"}, TENANT_ID)
        n2 = self.graph.create_node("Case", {"name": "B"}, TENANT_ID)
        with pytest.raises(ValueError, match="Invalid rel_type"):
            self.graph.create_relationship(
                n1.id, n2.id, "INVALID_REL", tenant_id=TENANT_ID
            )

    def test_create_relationship_node_not_found(self):
        n1 = self.graph.create_node("Person", {"name": "A"}, TENANT_ID)
        with pytest.raises(ValueError, match="not found"):
            self.graph.create_relationship(
                n1.id, "nonexistent", "PARTY_TO", tenant_id=TENANT_ID
            )

    def test_tenant_isolation(self):
        node = self.graph.create_node("Person", {"name": "Isolated"}, TENANT_ID)
        assert self.graph.get_node(node.id, TENANT_ID) is not None
        assert self.graph.get_node(node.id, OTHER_TENANT) is None

    def test_tenant_isolation_relationships(self):
        n1 = self.graph.create_node("Person", {"name": "A"}, TENANT_ID)
        n2 = self.graph.create_node("Case", {"name": "B"}, OTHER_TENANT)
        with pytest.raises(ValueError, match="different tenant"):
            self.graph.create_relationship(
                n1.id, n2.id, "PARTY_TO", tenant_id=TENANT_ID
            )

    def test_get_neighbors(self):
        n1 = self.graph.create_node("Person", {"name": "Jean"}, TENANT_ID)
        n2 = self.graph.create_node("Case", {"name": "Dossier"}, TENANT_ID)
        n3 = self.graph.create_node("Court", {"name": "TPI Bruxelles"}, TENANT_ID)
        self.graph.create_relationship(n1.id, n2.id, "PARTY_TO", tenant_id=TENANT_ID)
        self.graph.create_relationship(n2.id, n3.id, "FILED_AT", tenant_id=TENANT_ID)

        neighbors = self.graph.get_neighbors(n1.id, TENANT_ID, depth=1)
        assert len(neighbors) == 1  # Only n2 at depth 1
        assert neighbors[0]["node"].id == n2.id

        neighbors_d2 = self.graph.get_neighbors(n1.id, TENANT_ID, depth=2)
        assert len(neighbors_d2) == 2  # n2 and n3

    def test_case_subgraph(self):
        case = self.graph.create_node(
            "Case", {"name": "Test Case", "id": "case-1"}, TENANT_ID
        )
        person = self.graph.create_node("Person", {"name": "Jean"}, TENANT_ID)
        doc = self.graph.create_node("Document", {"name": "conclusions.pdf"}, TENANT_ID)
        self.graph.create_relationship(
            person.id, case.id, "PARTY_TO", tenant_id=TENANT_ID
        )
        self.graph.create_relationship(
            doc.id, case.id, "ATTACHED_TO", tenant_id=TENANT_ID
        )

        nodes, rels = self.graph.get_case_subgraph(case.id, TENANT_ID)
        assert len(nodes) == 3
        assert len(rels) == 2

    def test_delete_node(self):
        node = self.graph.create_node("Person", {"name": "ToDelete"}, TENANT_ID)
        assert self.graph.delete_node(node.id, TENANT_ID) is True
        assert self.graph.get_node(node.id, TENANT_ID) is None

    def test_delete_node_wrong_tenant(self):
        node = self.graph.create_node("Person", {"name": "Protected"}, TENANT_ID)
        assert self.graph.delete_node(node.id, OTHER_TENANT) is False

    def test_find_nodes_by_label(self):
        self.graph.create_node("Person", {"name": "A"}, TENANT_ID)
        self.graph.create_node("Person", {"name": "B"}, TENANT_ID)
        self.graph.create_node("Case", {"name": "C"}, TENANT_ID)

        persons = self.graph.find_nodes_by_label("Person", TENANT_ID)
        assert len(persons) == 2

    def test_find_nodes_by_property(self):
        self.graph.create_node("Person", {"name": "Target"}, TENANT_ID)
        self.graph.create_node("Person", {"name": "Other"}, TENANT_ID)

        found = self.graph.find_nodes_by_property("name", "Target", TENANT_ID)
        assert len(found) == 1

    def test_valid_labels(self):
        assert "Person" in VALID_NODE_LABELS
        assert "Organization" in VALID_NODE_LABELS
        assert "Case" in VALID_NODE_LABELS
        assert "LegalConcept" in VALID_NODE_LABELS

    def test_valid_relationship_types(self):
        assert "PARTY_TO" in VALID_RELATIONSHIP_TYPES
        assert "REPRESENTED_BY" in VALID_RELATIONSHIP_TYPES
        assert "OPPOSED_TO" in VALID_RELATIONSHIP_TYPES


# ── NER Service tests ──


class TestNERService:
    def setup_method(self):
        self.ner = NERService()

    def test_extract_court(self):
        entities = self.ner.extract(
            "Le Tribunal de première instance de Bruxelles a statué"
        )
        courts = [e for e in entities if e.entity_type == "COURT"]
        assert len(courts) >= 1
        assert "Bruxelles" in courts[0].text

    def test_extract_cour_appel(self):
        entities = self.ner.extract("La Cour d'appel de Liège a confirmé")
        courts = [e for e in entities if e.entity_type == "COURT"]
        assert len(courts) >= 1

    def test_extract_legal_reference(self):
        entities = self.ner.extract("Conformément à l'Art. 1382 C.C. et Art. 707 C.J.")
        legal = [e for e in entities if e.entity_type == "LEGAL_REFERENCE"]
        assert len(legal) >= 2

    def test_extract_person_maitre(self):
        entities = self.ner.extract("Maître Dupont a plaidé devant le tribunal")
        persons = [e for e in entities if e.entity_type == "PERSON"]
        assert len(persons) >= 1
        assert "Dupont" in persons[0].text

    def test_extract_person_vs(self):
        entities = self.ner.extract("Dupont c/ Martin")
        persons = [e for e in entities if e.entity_type == "PERSON"]
        assert len(persons) == 2

    def test_extract_organization(self):
        entities = self.ner.extract("La société Acme SA a été condamnée")
        orgs = [e for e in entities if e.entity_type == "ORGANIZATION"]
        assert len(orgs) >= 1

    def test_extract_monetary_amount(self):
        entities = self.ner.extract("Condamné à payer 15.000,00 EUR de dommages")
        money = [e for e in entities if e.entity_type == "MONETARY_AMOUNT"]
        assert len(money) >= 1

    def test_extract_date(self):
        entities = self.ner.extract("L'audience du 15/03/2026 est confirmée")
        dates = [e for e in entities if e.entity_type == "DATE"]
        assert len(dates) >= 1

    def test_extract_date_french(self):
        entities = self.ner.extract("Jugement du 15 mars 2026")
        dates = [e for e in entities if e.entity_type == "DATE"]
        assert len(dates) >= 1

    def test_extract_location(self):
        entities = self.ner.extract("L'accident a eu lieu à Bruxelles")
        locations = [e for e in entities if e.entity_type == "LOCATION"]
        assert len(locations) >= 1
        assert locations[0].text == "Bruxelles"

    def test_extract_empty(self):
        assert self.ner.extract("") == []
        assert self.ner.extract("   ") == []

    def test_extract_complex_text(self):
        text = (
            "Maître Dupont, représentant M. Martin devant le Tribunal de première instance de Bruxelles, "
            "invoque l'Art. 1382 C.C. et réclame 25.000 EUR de dommages. "
            "L'audience est fixée au 15 mars 2026."
        )
        entities = self.ner.extract(text)
        types = {e.entity_type for e in entities}
        assert "PERSON" in types
        assert "COURT" in types
        assert "LEGAL_REFERENCE" in types
        assert "MONETARY_AMOUNT" in types

    def test_deduplication(self):
        # Same entity mentioned twice should not create duplicates at same position
        entities = self.ner.extract("Bruxelles à Bruxelles")
        locations = [e for e in entities if e.entity_type == "LOCATION"]
        assert len(locations) == 2  # Different positions = 2 entities


# ── GraphBuilder tests ──


class TestGraphBuilder:
    def setup_method(self):
        self.graph = InMemoryGraphService()
        self.builder = GraphBuilder(graph_service=self.graph)

    def test_process_document(self):
        result = self.builder.process_document(
            doc_id="doc-1",
            text="Maître Dupont représente M. Martin devant le Tribunal de première instance de Bruxelles",
            case_id="case-1",
            tenant_id=TENANT_ID,
        )
        assert result.entities_extracted >= 2
        assert result.nodes_created >= 3  # case + doc + entities
        assert result.relationships_created >= 2

    def test_process_case_multiple_docs(self):
        docs = [
            {
                "id": "doc-1",
                "text": "Art. 1382 C.C. — Maître Dupont plaide pour M. Martin",
            },
            {"id": "doc-2", "text": "La Cour d'appel de Liège confirme le jugement"},
        ]
        result = self.builder.process_case("case-1", docs, TENANT_ID)
        assert result.entities_extracted >= 3
        assert result.nodes_created >= 4  # case + 2 docs + entities (some merged)

    def test_node_merging(self):
        # Same entity in two documents should be merged
        docs = [
            {"id": "doc-1", "text": "Maître Dupont a plaidé"},
            {"id": "doc-2", "text": "Maître Dupont a gagné"},
        ]
        result = self.builder.process_case("case-1", docs, TENANT_ID)
        # "Maître Dupont" should be merged (created once, merged once)
        assert result.nodes_merged >= 1

    def test_conflict_detection_no_conflict(self):
        # Build a simple graph without conflicts
        self.graph.create_node("Case", {"name": "Case A", "id": "case-a"}, TENANT_ID)
        person = self.graph.create_node("Person", {"name": "Jean"}, TENANT_ID)
        self.graph.create_relationship(
            person.id, "case-a", "PARTY_TO", tenant_id=TENANT_ID
        )

        conflicts = self.builder.detect_conflicts("case-a", TENANT_ID)
        assert len(conflicts) == 0

    def test_conflict_detection(self):
        # Build graph with conflicting roles
        case = self.graph.create_node(
            "Case", {"name": "Conflict Case", "id": "case-c"}, TENANT_ID
        )
        person = self.graph.create_node("Person", {"name": "Suspect"}, TENANT_ID)
        self.graph.create_relationship(
            person.id, case.id, "PARTY_TO", {"role": "PARTY_TO"}, TENANT_ID
        )
        self.graph.create_relationship(
            person.id, case.id, "OPPOSED_TO", {"role": "OPPOSED_TO"}, TENANT_ID
        )

        conflicts = self.builder.detect_conflicts(case.id, TENANT_ID)
        assert len(conflicts) >= 1
        assert conflicts[0].entity_name == "Suspect"


# ── Graph API endpoint tests ──


class TestGraphEndpoints:
    def setup_method(self):
        _graph.reset()

    def test_build_endpoint(self):
        client = TestClient(app)
        r = client.post(
            "/api/v1/graph/build/case-1",
            json={
                "documents": [
                    {
                        "id": "doc-1",
                        "text": "Maître Dupont représente M. Martin devant le Tribunal de première instance de Bruxelles",
                    },
                ]
            },
            headers=_auth_headers(),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["case_id"] == "case-1"
        assert data["entities_extracted"] >= 2
        assert data["nodes_created"] >= 3

    def test_case_subgraph_endpoint(self):
        client = TestClient(app)
        # Build first
        client.post(
            "/api/v1/graph/build/case-2",
            json={
                "documents": [
                    {
                        "id": "doc-2",
                        "text": "Art. 1382 C.C. appliqué par la Cour de cassation",
                    },
                ]
            },
            headers=_auth_headers(),
        )

        r = client.get("/api/v1/graph/case/case-2", headers=_auth_headers())
        assert r.status_code == 200
        data = r.json()
        assert data["total_nodes"] >= 2

    def test_search_endpoint(self):
        client = TestClient(app)
        # Build some data
        client.post(
            "/api/v1/graph/build/case-3",
            json={
                "documents": [
                    {"id": "d1", "text": "Maître Dupont à Bruxelles"},
                ]
            },
            headers=_auth_headers(),
        )

        r = client.post(
            "/api/v1/graph/search",
            json={"query": "Bruxelles", "depth": 2},
            headers=_auth_headers(),
        )
        assert r.status_code == 200

    def test_conflicts_endpoint(self):
        client = TestClient(app)
        r = client.get(
            "/api/v1/graph/case/nonexistent/conflicts", headers=_auth_headers()
        )
        assert r.status_code == 200
        assert r.json()["total"] == 0

    def test_similar_cases_endpoint(self):
        client = TestClient(app)
        # Build two cases with shared entities
        client.post(
            "/api/v1/graph/build/case-a",
            json={"documents": [{"id": "d1", "text": "Art. 1382 C.C. à Bruxelles"}]},
            headers=_auth_headers(),
        )
        client.post(
            "/api/v1/graph/build/case-b",
            json={
                "documents": [{"id": "d2", "text": "Art. 1382 C.C. à Bruxelles aussi"}]
            },
            headers=_auth_headers(),
        )

        r = client.get("/api/v1/graph/case/case-a/similar", headers=_auth_headers())
        assert r.status_code == 200

    def test_requires_auth(self):
        client = TestClient(app)
        r = client.get("/api/v1/graph/case/x")
        assert r.status_code == 401
