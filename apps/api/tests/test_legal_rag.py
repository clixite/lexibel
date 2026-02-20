"""Tests for Legal RAG router — search, chat, explain, predict, conflicts, timeline."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.auth.jwt import create_access_token
from apps.api.main import app

# ── Test data ──

TENANT_A = uuid.uuid4()
USER_A = uuid.uuid4()

TOKEN_A = create_access_token(USER_A, TENANT_A, "partner", "alice@alpha.be")

NOW = datetime(2026, 2, 15, 12, 0, 0)


def _make_search_result(**overrides):
    """Create a mock LegalSearchResult dataclass."""
    from apps.api.services.rag_service import LegalSearchResult

    defaults = {
        "chunk_text": "Article 1382 du Code civil belge...",
        "score": 0.95,
        "source": "Code Civil Belge",
        "document_type": "code_civil",
        "jurisdiction": "federal",
        "article_number": "1382",
        "date_published": None,
        "url": None,
        "page_number": None,
        "highlighted_passages": ["responsabilite civile"],
        "related_articles": ["1383", "1384"],
        "entities": [],
    }
    defaults.update(overrides)
    return LegalSearchResult(**defaults)


def _make_search_response(**overrides):
    """Create a mock LegalSearchResponse."""
    from apps.api.services.rag_service import LegalSearchResponse

    defaults = {
        "query": "responsabilite civile",
        "expanded_query": "responsabilite civile delictuelle",
        "results": [_make_search_result()],
        "total": 1,
        "search_time_ms": 42.5,
        "suggested_queries": ["article 1383"],
        "detected_entities": [],
    }
    defaults.update(overrides)
    return LegalSearchResponse(**defaults)


def _patch_db():
    mock_session = AsyncMock()

    async def override_db(tenant_id=None):
        yield mock_session

    return mock_session, override_db


# ── Tests ──


@pytest.mark.asyncio
async def test_legal_search():
    mock_session, override_db = _patch_db()
    search_resp = _make_search_response()

    with patch("apps.api.routers.legal_rag.get_legal_rag_service") as mock_svc_fn:
        mock_svc = MagicMock()
        mock_svc.search = AsyncMock(return_value=search_resp)
        mock_svc_fn.return_value = mock_svc

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/v1/legal/search?q=responsabilite+civile",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["query"] == "responsabilite civile"
    assert data["total"] == 1
    assert len(data["results"]) == 1
    assert data["results"][0]["source"] == "Code Civil Belge"
    assert data["search_time_ms"] > 0


@pytest.mark.asyncio
async def test_legal_search_with_filters():
    mock_session, override_db = _patch_db()
    search_resp = _make_search_response()

    with patch("apps.api.routers.legal_rag.get_legal_rag_service") as mock_svc_fn:
        mock_svc = MagicMock()
        mock_svc.search = AsyncMock(return_value=search_resp)
        mock_svc_fn.return_value = mock_svc

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/v1/legal/search?q=divorce&jurisdiction=federal&document_type=code_civil",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    # Verify the service was called with correct filters
    call_kwargs = mock_svc.search.call_args.kwargs
    assert call_kwargs["filters"]["jurisdiction"] == "federal"
    assert call_kwargs["filters"]["document_type"] == "code_civil"


@pytest.mark.asyncio
async def test_legal_search_requires_query():
    mock_session, override_db = _patch_db()

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/legal/search",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_legal_chat():
    mock_session, override_db = _patch_db()
    search_resp = _make_search_response()

    with (
        patch("apps.api.routers.legal_rag.get_legal_rag_service") as mock_svc_fn,
        patch("apps.api.routers.legal_rag.get_llm_gateway") as mock_gw_fn,
    ):
        mock_svc = MagicMock()
        mock_svc.search = AsyncMock(return_value=search_resp)
        mock_svc_fn.return_value = mock_svc

        mock_gw = MagicMock()
        llm_response = MagicMock()
        llm_response.text = "La responsabilite civile en droit belge..."
        mock_gw.generate = AsyncMock(return_value=llm_response)
        mock_gw_fn.return_value = mock_gw

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/legal/chat",
                json={"message": "Expliquez la responsabilite civile"},
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["message"]["role"] == "assistant"
    assert "responsabilite" in data["message"]["content"].lower()
    assert "conversation_id" in data
    assert "suggested_followups" in data


@pytest.mark.asyncio
async def test_legal_chat_with_case_context():
    mock_session, override_db = _patch_db()
    search_resp = _make_search_response()

    with (
        patch("apps.api.routers.legal_rag.get_legal_rag_service") as mock_svc_fn,
        patch("apps.api.routers.legal_rag.get_llm_gateway") as mock_gw_fn,
    ):
        mock_svc = MagicMock()
        mock_svc.search = AsyncMock(return_value=search_resp)
        mock_svc_fn.return_value = mock_svc

        mock_gw = MagicMock()
        llm_response = MagicMock()
        llm_response.text = "Reponse avec contexte du dossier."
        mock_gw.generate = AsyncMock(return_value=llm_response)
        mock_gw_fn.return_value = mock_gw

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/legal/chat",
                json={
                    "message": "Quel est le risque?",
                    "case_id": str(uuid.uuid4()),
                    "conversation_id": "conv-123",
                },
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["conversation_id"] == "conv-123"


@pytest.mark.asyncio
async def test_explain_article():
    mock_session, override_db = _patch_db()

    with patch("apps.api.routers.legal_rag.get_llm_gateway") as mock_gw_fn:
        mock_gw = MagicMock()
        llm_response = MagicMock()
        llm_response.text = (
            "Explication simple:\n"
            "- Point 1: La responsabilite civile\n"
            "- Point 2: Les dommages et interets\n"
            "- Point 3: La faute"
        )
        mock_gw.generate = AsyncMock(return_value=llm_response)
        mock_gw_fn.return_value = mock_gw

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/legal/explain-article",
                json={
                    "article_text": "Tout fait quelconque de l'homme, qui cause a autrui un dommage, oblige celui par la faute duquel il est arrive, a le reparer.",
                    "simplification_level": "basic",
                },
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert "original_text" in data
    assert "simplified_explanation" in data
    assert isinstance(data["key_points"], list)


@pytest.mark.asyncio
async def test_predict_jurisprudence():
    mock_session, override_db = _patch_db()
    search_resp = _make_search_response()

    with patch("apps.api.routers.legal_rag.get_legal_rag_service") as mock_svc_fn:
        mock_svc = MagicMock()
        mock_svc.search = AsyncMock(return_value=search_resp)
        mock_svc.predict_jurisprudence = MagicMock(
            return_value={
                "predicted_outcome": "favorable",
                "confidence": 0.72,
            }
        )
        mock_svc_fn.return_value = mock_svc

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/legal/predict-jurisprudence",
                json={
                    "case_facts": "Le demandeur a subi un prejudice suite a un accident de la route cause par le defendeur.",
                    "relevant_articles": ["1382", "1383"],
                },
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["predicted_outcome"] == "favorable"
    assert data["confidence"] == 0.72
    assert "similar_cases" in data
    assert "reasoning" in data


@pytest.mark.asyncio
async def test_detect_conflicts():
    mock_session, override_db = _patch_db()

    with patch("apps.api.routers.legal_rag.get_legal_rag_service") as mock_svc_fn:
        mock_svc = MagicMock()
        mock_svc.detect_conflicts = MagicMock(
            return_value={
                "has_conflict": True,
                "explanation": "Conflit detecte entre les deux articles.",
            }
        )
        mock_svc_fn.return_value = mock_svc

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/legal/detect-conflicts",
                json={
                    "article1": "Article 1382 du Code civil...",
                    "article2": "Article 1384 du Code civil...",
                },
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["has_conflict"] is True
    assert data["severity"] == "minor"
    assert len(data["recommendations"]) > 0


@pytest.mark.asyncio
async def test_detect_conflicts_no_conflict():
    mock_session, override_db = _patch_db()

    with patch("apps.api.routers.legal_rag.get_legal_rag_service") as mock_svc_fn:
        mock_svc = MagicMock()
        mock_svc.detect_conflicts = MagicMock(
            return_value={
                "has_conflict": False,
                "explanation": "Aucun conflit detecte.",
            }
        )
        mock_svc_fn.return_value = mock_svc

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/legal/detect-conflicts",
                json={
                    "article1": "Article 1382 du Code civil...",
                    "article2": "Article 1383 du Code civil...",
                },
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["has_conflict"] is False
    assert data["severity"] == "none"
    assert data["recommendations"] == []


@pytest.mark.asyncio
async def test_legal_timeline():
    mock_session, override_db = _patch_db()

    with patch("apps.api.routers.legal_rag.get_legal_rag_service") as mock_svc_fn:
        mock_svc = MagicMock()
        mock_svc.get_timeline = MagicMock(
            return_value=[
                {
                    "date": NOW,
                    "change": "Modification de l'article 1382",
                    "source": "Moniteur Belge",
                },
            ]
        )
        mock_svc_fn.return_value = mock_svc

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/v1/legal/timeline?law_reference=Article+1382+Code+Civil",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["law_reference"] == "Article 1382 Code Civil"
    assert len(data["events"]) == 1
    assert data["events"][0]["type"] == "modification"


@pytest.mark.asyncio
async def test_legal_timeline_requires_reference():
    mock_session, override_db = _patch_db()

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/legal/timeline",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 422
