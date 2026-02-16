"""Tests for LXB-054-055: GraphRAG — context enrichment, combined search, similar cases."""
import uuid

import pytest

from apps.api.services.graph.neo4j_service import InMemoryGraphService
from apps.api.services.graph.graph_builder import GraphBuilder
from apps.api.services.graph.graph_rag_service import GraphRAGService


TENANT_ID = str(uuid.uuid4())


class TestGraphRAGService:
    def setup_method(self):
        self.graph = InMemoryGraphService()
        self.builder = GraphBuilder(graph_service=self.graph)
        self.rag = GraphRAGService(graph_service=self.graph)

    def _build_case(self, case_id: str, docs: list[dict]) -> None:
        self.builder.process_case(case_id, docs, TENANT_ID)

    def test_context_for_query_basic(self):
        self._build_case("case-1", [
            {"id": "d1", "text": "Maître Dupont représente M. Martin à Bruxelles"},
        ])
        context = self.rag.get_context_for_query("Bruxelles", TENANT_ID)
        assert context.entity_count >= 1
        assert context.text_summary != ""

    def test_context_for_query_with_case(self):
        self._build_case("case-1", [
            {"id": "d1", "text": "Art. 1382 C.C. appliqué à Bruxelles"},
        ])
        context = self.rag.get_context_for_query("Art. 1382", TENANT_ID, case_id="case-1")
        assert context.entity_count >= 1

    def test_context_for_empty_query(self):
        context = self.rag.get_context_for_query("xyz unknown entity", TENANT_ID)
        # No entities found, empty context
        assert context.entity_count == 0

    def test_graph_search(self):
        self._build_case("case-1", [
            {"id": "d1", "text": "Le Tribunal de première instance de Bruxelles a jugé"},
        ])
        context = self.rag.graph_search("Bruxelles", TENANT_ID, depth=2)
        assert context.entity_count >= 1

    def test_graph_search_depth(self):
        self._build_case("case-1", [
            {"id": "d1", "text": "Maître Dupont à Bruxelles"},
        ])
        # Depth 1 vs depth 2 should find more nodes
        ctx1 = self.rag.graph_search("Bruxelles", TENANT_ID, depth=1)
        ctx2 = self.rag.graph_search("Bruxelles", TENANT_ID, depth=2)
        assert ctx2.entity_count >= ctx1.entity_count

    def test_find_similar_cases_shared_entities(self):
        # Two cases sharing the same legal reference and location
        self._build_case("case-1", [
            {"id": "d1", "text": "Art. 1382 C.C. appliqué à Bruxelles pour accident"},
        ])
        self._build_case("case-2", [
            {"id": "d2", "text": "Art. 1382 C.C. invoqué à Bruxelles pour responsabilité"},
        ])

        similar = self.rag.find_similar_cases("case-1", TENANT_ID)
        assert len(similar) >= 1
        assert similar[0].case_id == "case-2"
        assert similar[0].similarity_score > 0

    def test_find_similar_cases_no_match(self):
        self._build_case("case-lonely", [
            {"id": "d1", "text": "Un texte sans entités reconnues"},
        ])
        similar = self.rag.find_similar_cases("case-lonely", TENANT_ID)
        # No similar cases (or the only entities are dates/etc)
        # This should not raise an error
        assert isinstance(similar, list)

    def test_find_similar_cases_different_entities(self):
        self._build_case("case-a", [
            {"id": "d1", "text": "Maître Dupont à Bruxelles invoque Art. 1382 C.C."},
        ])
        self._build_case("case-b", [
            {"id": "d2", "text": "La société Acme SA à Gand devant le Tribunal de première instance de Gand"},
        ])

        similar = self.rag.find_similar_cases("case-a", TENANT_ID)
        # These cases share very few entities
        if similar:
            assert similar[0].similarity_score < 0.5

    def test_context_text_summary(self):
        self._build_case("case-1", [
            {"id": "d1", "text": "Maître Dupont et Me Martin plaident devant le Tribunal de première instance de Bruxelles"},
        ])
        context = self.rag.get_context_for_query("Bruxelles", TENANT_ID, case_id="case-1")
        # Summary should mention entity types
        assert context.text_summary

    def test_context_paths(self):
        self._build_case("case-1", [
            {"id": "d1", "text": "Maître Dupont à Bruxelles devant le Tribunal de première instance de Bruxelles"},
        ])
        context = self.rag.get_context_for_query("Bruxelles", TENANT_ID, case_id="case-1")
        # Should have some paths
        assert isinstance(context.paths, list)

    def test_subgraph_query(self):
        # Build case and verify subgraph extraction
        self._build_case("case-1", [
            {"id": "d1", "text": "Art. 707 C.J. et Art. 1382 C.C."},
        ])
        nodes, rels = self.graph.get_case_subgraph("case-1", TENANT_ID)
        assert len(nodes) >= 2  # case + doc + legal refs
        node_ids = {n.id for n in nodes}
        for rel in rels:
            assert rel.from_id in node_ids
            assert rel.to_id in node_ids

    def test_combined_vector_graph_context(self):
        """Test that graph context can enhance vector search results."""
        self._build_case("case-1", [
            {"id": "d1", "text": "Maître Dupont invoque Art. 1382 C.C. pour un accident à Bruxelles"},
        ])

        # Get graph context
        graph_ctx = self.rag.get_context_for_query(
            "accident responsabilité Bruxelles",
            TENANT_ID,
            case_id="case-1",
        )

        # Verify context can be used to enrich RAG
        assert graph_ctx.text_summary  # Non-empty summary for LLM
        assert graph_ctx.nodes  # Has entities
        # In production, this would be combined with vector_service.search() results

    def test_multiple_cases_shared_court(self):
        """Cases filed at the same court should show up as similar."""
        self._build_case("case-x", [
            {"id": "d1", "text": "Devant le Tribunal de première instance de Bruxelles, Art. 1382 C.C."},
        ])
        self._build_case("case-y", [
            {"id": "d2", "text": "Le Tribunal de première instance de Bruxelles a statué, Art. 1382 C.C."},
        ])

        similar = self.rag.find_similar_cases("case-x", TENANT_ID)
        assert len(similar) >= 1
        case_ids = [s.case_id for s in similar]
        assert "case-y" in case_ids
