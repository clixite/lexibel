"""Tests for LXB-033-034: LLM Gateway, AI generation endpoints."""

import uuid

import pytest
from fastapi.testclient import TestClient

from apps.api.services.llm_gateway import (
    ContextChunk,
    LLMResponse,
    StubLLMGateway,
    check_rate_limit,
    reset_rate_limits,
    validate_citations,
    LLMSource,
    RATE_LIMIT_MAX,
)
from apps.api.main import app


TENANT_ID = str(uuid.uuid4())
USER_ID = str(uuid.uuid4())


def _auth_headers() -> dict:
    return {
        "X-Tenant-ID": TENANT_ID,
        "X-User-ID": USER_ID,
        "X-User-Role": "super_admin",
        "X-User-Email": "test@lexibel.be",
    }


# ── LLM Gateway unit tests ──


class TestLLMGateway:
    def setup_method(self):
        reset_rate_limits()

    @pytest.mark.asyncio
    async def test_stub_gateway_returns_response(self):
        gateway = StubLLMGateway(canned_response="Voici le résumé du dossier.")
        context = [
            ContextChunk(
                content="Le contrat a été signé le 15 janvier 2024.",
                document_id="doc-1",
                case_id="case-1",
            )
        ]
        response = await gateway.generate("Résume le dossier", context)
        assert isinstance(response, LLMResponse)
        assert response.text == "Voici le résumé du dossier."
        assert response.model == "stub"
        assert len(response.sources) == 1
        assert response.sources[0].document_id == "doc-1"

    @pytest.mark.asyncio
    async def test_stub_gateway_no_context(self):
        gateway = StubLLMGateway(canned_response="Pas de contexte.")
        response = await gateway.generate("Bonjour", [])
        assert response.text == "Pas de contexte."
        assert len(response.sources) == 0

    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        reset_rate_limits()
        gateway = StubLLMGateway()
        tenant = "rate-test-tenant"

        # Exhaust rate limit
        for _ in range(RATE_LIMIT_MAX):
            assert check_rate_limit(tenant) is True

        # Next call should be rate limited
        assert check_rate_limit(tenant) is False

        # Gateway should return rate limit error
        response = await gateway.generate("test", [], tenant_id=tenant)
        assert "limite" in response.text.lower()

    @pytest.mark.asyncio
    async def test_multiple_context_chunks(self):
        gateway = StubLLMGateway(canned_response="Analyse complète.")
        chunks = [
            ContextChunk(content=f"Chunk {i}", document_id=f"doc-{i}") for i in range(5)
        ]
        response = await gateway.generate("Analyse", chunks)
        assert len(response.sources) == 5


# ── Citation validation (P3) tests ──


class TestCitationValidation:
    def test_no_claims_is_valid(self):
        is_valid, uncited = validate_citations("Bonjour, comment allez-vous ?", [])
        assert is_valid is True
        assert uncited == []

    def test_claim_without_source_flagged(self):
        text = "Selon l'article 1382 du Code civil, la responsabilité est engagée."
        is_valid, uncited = validate_citations(text, [])
        assert is_valid is False
        assert len(uncited) > 0

    def test_claim_with_matching_source_valid(self):
        text = "Selon l'article 1382, la responsabilité est engagée."
        sources = [
            LLMSource(
                document_id="doc-1",
                chunk_text="article 1382 code civil responsabilité engagée dommage",
            )
        ]
        is_valid, uncited = validate_citations(text, sources)
        assert is_valid is True

    def test_monetary_claim_without_source(self):
        text = "Le montant dû est de 5000 EUR."
        is_valid, uncited = validate_citations(text, [])
        assert is_valid is False

    def test_legal_reference_with_source(self):
        text = "L'article 458 du Code pénal protège le secret professionnel."
        sources = [
            LLMSource(
                document_id="doc-2",
                chunk_text="article 458 code pénal secret professionnel avocat protection",
            )
        ]
        is_valid, uncited = validate_citations(text, sources)
        assert is_valid is True


# ── API endpoint tests ──


class TestSearchEndpoint:
    def setup_method(self):
        reset_rate_limits()

    def test_search_endpoint(self):
        client = TestClient(app)
        response = client.post(
            "/api/v1/search",
            json={"query": "contrat de bail", "top_k": 5},
            headers=_auth_headers(),
        )
        assert response.status_code == 200
        data = response.json()
        assert "query" in data
        assert "results" in data
        assert data["query"] == "contrat de bail"

    def test_search_requires_auth(self):
        client = TestClient(app)
        response = client.post(
            "/api/v1/search",
            json={"query": "test"},
        )
        assert response.status_code == 401

    def test_search_empty_query_rejected(self):
        client = TestClient(app)
        response = client.post(
            "/api/v1/search",
            json={"query": "", "top_k": 5},
            headers=_auth_headers(),
        )
        assert response.status_code == 422


class TestAIGenerateEndpoint:
    def setup_method(self):
        reset_rate_limits()

    def test_ai_generate(self):
        client = TestClient(app)
        response = client.post(
            "/api/v1/ai/generate",
            json={"prompt": "Résume le dossier"},
            headers=_auth_headers(),
        )
        assert response.status_code == 200
        data = response.json()
        assert "text" in data
        assert "sources" in data
        assert "model" in data

    def test_ai_generate_requires_auth(self):
        client = TestClient(app)
        response = client.post(
            "/api/v1/ai/generate",
            json={"prompt": "test"},
        )
        assert response.status_code == 401


class TestAIDraftEndpoint:
    def setup_method(self):
        reset_rate_limits()

    def test_ai_draft(self):
        client = TestClient(app)
        case_id = str(uuid.uuid4())
        response = client.post(
            "/api/v1/ai/draft",
            json={"case_id": case_id, "draft_type": "courrier"},
            headers=_auth_headers(),
        )
        assert response.status_code == 200
        data = response.json()
        assert "text" in data

    def test_ai_draft_invalid_type(self):
        client = TestClient(app)
        response = client.post(
            "/api/v1/ai/draft",
            json={"case_id": str(uuid.uuid4()), "draft_type": "invalid"},
            headers=_auth_headers(),
        )
        assert response.status_code == 422


class TestAISummarizeEndpoint:
    def setup_method(self):
        reset_rate_limits()

    def test_ai_summarize(self):
        client = TestClient(app)
        response = client.post(
            "/api/v1/ai/summarize",
            json={"case_id": str(uuid.uuid4())},
            headers=_auth_headers(),
        )
        assert response.status_code == 200
        data = response.json()
        assert "text" in data


class TestAIAnalyzeEndpoint:
    def setup_method(self):
        reset_rate_limits()

    def test_ai_analyze(self):
        client = TestClient(app)
        response = client.post(
            "/api/v1/ai/analyze",
            json={"document_id": str(uuid.uuid4())},
            headers=_auth_headers(),
        )
        assert response.status_code == 200
        data = response.json()
        assert "text" in data
