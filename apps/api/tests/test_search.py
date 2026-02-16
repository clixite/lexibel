"""Tests for LXB-030-032: Chunking, Vector search, Hybrid search."""

import uuid


from apps.api.services.chunking_service import (
    chunk_text,
    count_tokens,
    generate_embeddings,
    _split_text_into_chunks,
)
from apps.api.services.vector_service import InMemoryVectorService
from apps.api.services.search_service import SearchResult, SearchService, _keyword_score


# ── Chunking tests ──


class TestChunking:
    def test_count_tokens(self):
        tokens = count_tokens("Hello world")
        assert tokens >= 2

    def test_short_text_single_chunk(self):
        chunks = _split_text_into_chunks("Short text.", max_tokens=512)
        assert len(chunks) == 1
        assert chunks[0] == "Short text."

    def test_long_text_multiple_chunks(self):
        # Create text longer than 512 tokens
        long_text = " ".join(["word"] * 1000)
        chunks = _split_text_into_chunks(long_text, max_tokens=100, overlap_tokens=20)
        assert len(chunks) > 1
        # Each chunk should be <= 100 tokens
        for c in chunks:
            assert count_tokens(c) <= 101  # Allow 1 token tolerance

    def test_overlap_between_chunks(self):
        long_text = " ".join([f"word{i}" for i in range(500)])
        chunks = _split_text_into_chunks(long_text, max_tokens=100, overlap_tokens=20)
        # Consecutive chunks should share some content (overlap)
        if len(chunks) >= 2:
            words_0 = set(chunks[0].split()[-30:])
            words_1 = set(chunks[1].split()[:30])
            overlap = words_0 & words_1
            assert len(overlap) > 0

    def test_chunk_text_with_metadata(self):
        case_id = str(uuid.uuid4())
        doc_id = str(uuid.uuid4())
        chunks = chunk_text(
            "Test content for chunking.",
            case_id=case_id,
            document_id=doc_id,
            tenant_id="tenant-1",
            page_number=5,
        )
        assert len(chunks) == 1
        assert chunks[0].case_id == case_id
        assert chunks[0].document_id == doc_id
        assert chunks[0].tenant_id == "tenant-1"
        assert chunks[0].page_number == 5
        assert chunks[0].chunk_index == 0

    def test_generate_embeddings_dimensions(self):
        embeddings = generate_embeddings(["Hello world", "Test sentence"])
        assert len(embeddings) == 2
        assert len(embeddings[0]) == 384
        assert len(embeddings[1]) == 384

    def test_generate_embeddings_deterministic(self):
        e1 = generate_embeddings(["Same text"])
        e2 = generate_embeddings(["Same text"])
        assert e1[0] == e2[0]

    def test_generate_embeddings_different_texts(self):
        e = generate_embeddings(["Text A", "Text B"])
        assert e[0] != e[1]


# ── Vector service tests ──


class TestVectorService:
    def setup_method(self):
        self.svc = InMemoryVectorService()
        self.tenant_id = str(uuid.uuid4())
        self.other_tenant = str(uuid.uuid4())
        self.case_id = str(uuid.uuid4())
        self.doc_id = str(uuid.uuid4())

    def test_upsert_and_search(self):
        embeddings = generate_embeddings(["contrat de travail"])
        self.svc.upsert_chunks(
            chunk_ids=["chunk-1"],
            embeddings=embeddings,
            payloads=[
                {
                    "content": "Contrat de travail à durée indéterminée",
                    "tenant_id": self.tenant_id,
                    "case_id": self.case_id,
                    "document_id": self.doc_id,
                }
            ],
        )

        query_emb = generate_embeddings(["contrat de travail"])[0]
        results = self.svc.search(query_emb, self.tenant_id, top_k=5)
        assert len(results) == 1
        assert results[0].chunk_id == "chunk-1"
        assert results[0].content == "Contrat de travail à durée indéterminée"

    def test_tenant_isolation(self):
        """Tenant A cannot see tenant B's documents."""
        embeddings = generate_embeddings(["secret document"])
        self.svc.upsert_chunks(
            chunk_ids=["chunk-secret"],
            embeddings=embeddings,
            payloads=[
                {
                    "content": "Secret professionnel - confidentiel",
                    "tenant_id": self.tenant_id,
                    "document_id": self.doc_id,
                }
            ],
        )

        query_emb = generate_embeddings(["secret document"])[0]
        # Other tenant should get no results
        results = self.svc.search(query_emb, self.other_tenant, top_k=5)
        assert len(results) == 0

        # Same tenant should find it
        results = self.svc.search(query_emb, self.tenant_id, top_k=5)
        assert len(results) == 1

    def test_case_filter(self):
        other_case = str(uuid.uuid4())
        embeddings = generate_embeddings(["doc A", "doc B"])
        self.svc.upsert_chunks(
            chunk_ids=["c1", "c2"],
            embeddings=embeddings,
            payloads=[
                {
                    "content": "Doc A",
                    "tenant_id": self.tenant_id,
                    "case_id": self.case_id,
                    "document_id": "d1",
                },
                {
                    "content": "Doc B",
                    "tenant_id": self.tenant_id,
                    "case_id": other_case,
                    "document_id": "d2",
                },
            ],
        )

        query_emb = generate_embeddings(["doc"])[0]
        results = self.svc.search(query_emb, self.tenant_id, case_id=self.case_id)
        assert len(results) == 1
        assert results[0].chunk_id == "c1"

    def test_delete_by_document(self):
        embeddings = generate_embeddings(["test"])
        self.svc.upsert_chunks(
            chunk_ids=["d1"],
            embeddings=embeddings,
            payloads=[
                {
                    "content": "test",
                    "tenant_id": self.tenant_id,
                    "document_id": self.doc_id,
                }
            ],
        )
        assert len(self.svc._store) == 1

        self.svc.delete_by_document(self.doc_id)
        assert len(self.svc._store) == 0

    def test_top_k_limit(self):
        texts = [f"document {i}" for i in range(20)]
        embeddings = generate_embeddings(texts)
        self.svc.upsert_chunks(
            chunk_ids=[f"c{i}" for i in range(20)],
            embeddings=embeddings,
            payloads=[
                {"content": t, "tenant_id": self.tenant_id, "document_id": f"d{i}"}
                for i, t in enumerate(texts)
            ],
        )

        query_emb = generate_embeddings(["document"])[0]
        results = self.svc.search(query_emb, self.tenant_id, top_k=5)
        assert len(results) == 5


# ── Hybrid search tests ──


class TestHybridSearch:
    def setup_method(self):
        self.vector_svc = InMemoryVectorService()
        self.search_svc = SearchService(self.vector_svc)
        self.tenant_id = str(uuid.uuid4())

    def _index_docs(self, texts: list[str], case_id: str | None = None):
        embeddings = generate_embeddings(texts)
        self.vector_svc.upsert_chunks(
            chunk_ids=[f"c{i}" for i in range(len(texts))],
            embeddings=embeddings,
            payloads=[
                {
                    "content": t,
                    "tenant_id": self.tenant_id,
                    "case_id": case_id,
                    "document_id": f"doc-{i}",
                    "evidence_link_id": f"ev-{i}",
                }
                for i, t in enumerate(texts)
            ],
        )

    def test_hybrid_search_returns_results(self):
        self._index_docs(["Le contrat de bail est signé.", "La facture est impayée."])
        response = self.search_svc.search("contrat bail", self.tenant_id)
        assert response.total > 0
        assert response.query == "contrat bail"

    def test_hybrid_search_empty_index(self):
        response = self.search_svc.search("anything", self.tenant_id)
        assert response.total == 0
        assert response.results == []

    def test_keyword_score_basic(self):
        score = _keyword_score("Le contrat de travail est valide", "contrat travail")
        assert score > 0

    def test_keyword_score_no_match(self):
        score = _keyword_score("Le chat dort", "contrat travail")
        assert score == 0.0

    def test_search_result_has_source(self):
        result_with_source = SearchResult(chunk_text="test", document_id="doc-1")
        assert result_with_source.has_source is True

        result_without = SearchResult(chunk_text="test")
        assert result_without.has_source is False

    def test_hybrid_scores_sorted(self):
        self._index_docs(
            [
                "Le contrat de bail commercial est signé le 15 janvier.",
                "Le droit pénal belge prévoit des sanctions.",
                "Le contrat de bail résidentiel a une durée de 9 ans.",
            ]
        )
        response = self.search_svc.search("contrat bail", self.tenant_id)
        if len(response.results) >= 2:
            scores = [r.score for r in response.results]
            assert scores == sorted(scores, reverse=True)
