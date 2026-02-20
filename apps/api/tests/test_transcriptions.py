"""Tests for Transcriptions router — list, get, link-case, delete."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.auth.jwt import create_access_token
from apps.api.main import app

# ── Test data ──

TENANT_A = uuid.uuid4()
USER_A = uuid.uuid4()
TRANS_ID = uuid.uuid4()
CASE_ID = uuid.uuid4()

TOKEN_A = create_access_token(USER_A, TENANT_A, "partner", "alice@alpha.be")

NOW = datetime(2026, 2, 15, 12, 0, 0)


def _make_transcription(**overrides):
    defaults = {
        "id": TRANS_ID,
        "tenant_id": TENANT_A,
        "case_id": None,
        "source": "plaud",
        "status": "completed",
        "language": "fr",
        "audio_url": "https://storage.test/audio.mp3",
        "audio_duration_seconds": 300,
        "full_text": "Ceci est le texte complet de la transcription.",
        "summary": "Resume de la conversation.",
        "sentiment_score": 0.75,
        "sentiment_label": "positive",
        "extracted_tasks": ["task1", "task2"],
        "completed_at": NOW,
        "created_at": NOW,
        "metadata": {"device": "plaud-note"},
    }
    defaults.update(overrides)

    class MockTranscription:
        pass

    obj = MockTranscription()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _patch_db():
    mock_session = AsyncMock()

    async def override_db(tenant_id=None):
        yield mock_session

    return mock_session, override_db


def _make_scalars_result(items):
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = items
    mock_result.scalars.return_value = mock_scalars
    return mock_result


# ── Tests ──


@pytest.mark.asyncio
async def test_list_transcriptions():
    mock_session, override_db = _patch_db()
    transcriptions = [
        _make_transcription(),
        _make_transcription(id=uuid.uuid4(), source="ringover"),
    ]

    result = _make_scalars_result(transcriptions)
    mock_session.execute = AsyncMock(return_value=result)

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/transcriptions",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["transcriptions"]) == 2


@pytest.mark.asyncio
async def test_list_transcriptions_with_filters():
    mock_session, override_db = _patch_db()
    transcriptions = [_make_transcription(source="plaud")]

    result = _make_scalars_result(transcriptions)
    mock_session.execute = AsyncMock(return_value=result)

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/transcriptions?source=plaud&status=completed",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["transcriptions"][0]["source"] == "plaud"


@pytest.mark.asyncio
async def test_list_transcriptions_empty():
    mock_session, override_db = _patch_db()

    result = _make_scalars_result([])
    mock_session.execute = AsyncMock(return_value=result)

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/transcriptions",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["transcriptions"] == []


@pytest.mark.asyncio
async def test_get_transcription_detail():
    mock_session, override_db = _patch_db()
    transcription = _make_transcription()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = transcription
    mock_session.execute = AsyncMock(return_value=mock_result)

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    # Pass include_segments=false to avoid selectinload on non-existent relationship
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            f"/api/v1/transcriptions/{TRANS_ID}?include_segments=false",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(TRANS_ID)
    assert data["source"] == "plaud"
    assert data["status"] == "completed"
    assert data["full_text"] is not None


@pytest.mark.asyncio
async def test_get_transcription_detail_not_found():
    mock_session, override_db = _patch_db()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            f"/api/v1/transcriptions/{uuid.uuid4()}?include_segments=false",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_transcription_invalid_uuid():
    mock_session, override_db = _patch_db()

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/transcriptions/not-a-uuid",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_link_transcription_to_case():
    mock_session, override_db = _patch_db()
    transcription = _make_transcription()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = transcription
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.flush = AsyncMock()

    async def mock_refresh(obj):
        obj.case_id = CASE_ID

    mock_session.refresh = AsyncMock(side_effect=mock_refresh)

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            f"/api/v1/transcriptions/{TRANS_ID}/link-case?case_id={CASE_ID}",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["case_id"] == str(CASE_ID)
    assert data["status"] == "linked"


@pytest.mark.asyncio
async def test_link_transcription_not_found():
    mock_session, override_db = _patch_db()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            f"/api/v1/transcriptions/{uuid.uuid4()}/link-case?case_id={CASE_ID}",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_link_transcription_invalid_uuid():
    mock_session, override_db = _patch_db()

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/v1/transcriptions/not-a-uuid/link-case?case_id=also-not-uuid",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_delete_transcription():
    mock_session, override_db = _patch_db()

    mock_result = MagicMock()
    mock_result.rowcount = 1
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.delete(
            f"/api/v1/transcriptions/{TRANS_ID}",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_transcription_not_found():
    mock_session, override_db = _patch_db()

    mock_result = MagicMock()
    mock_result.rowcount = 0
    mock_session.execute = AsyncMock(return_value=mock_result)

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.delete(
            f"/api/v1/transcriptions/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_transcription_invalid_uuid():
    mock_session, override_db = _patch_db()

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.delete(
            "/api/v1/transcriptions/not-a-uuid",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 400
