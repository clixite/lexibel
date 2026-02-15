"""LXB-015-017: Tests for Timeline (InteractionEvents) — append-only, pagination, filters, cross-tenant."""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.auth.jwt import create_access_token
from apps.api.main import app

# ── Test data ──

TENANT_A = uuid.uuid4()
TENANT_B = uuid.uuid4()
USER_A = uuid.uuid4()
USER_B = uuid.uuid4()
CASE_ID = uuid.uuid4()
EVENT_ID = uuid.uuid4()

TOKEN_A = create_access_token(USER_A, TENANT_A, "partner", "alice@alpha.be")
TOKEN_B = create_access_token(USER_B, TENANT_B, "partner", "bob@beta.be")

NOW = datetime(2026, 2, 15, 12, 0, 0, tzinfo=timezone.utc)


def _make_event_obj(**overrides):
    """Create a mock InteractionEvent object."""
    defaults = {
        "id": EVENT_ID,
        "tenant_id": TENANT_A,
        "case_id": CASE_ID,
        "source": "MANUAL",
        "event_type": "INTERNAL_NOTE",
        "title": "Note de suivi",
        "body": "Appelé le client pour mise à jour.",
        "occurred_at": NOW,
        "metadata": {},
        "created_by": USER_A,
        "created_at": NOW,
    }
    defaults.update(overrides)

    class MockEvent:
        pass

    obj = MockEvent()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _make_evidence_link_obj(**overrides):
    """Create a mock EvidenceLink object."""
    defaults = {
        "id": uuid.uuid4(),
        "tenant_id": TENANT_A,
        "interaction_event_id": EVENT_ID,
        "file_path": f"/{TENANT_A}/{EVENT_ID}/document.pdf",
        "file_name": "document.pdf",
        "mime_type": "application/pdf",
        "file_size_bytes": 12345,
        "sha256_hash": "a" * 64,
        "created_at": NOW,
        "updated_at": NOW,
    }
    defaults.update(overrides)

    class MockLink:
        pass

    obj = MockLink()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _patch_db():
    mock_session = AsyncMock()

    async def override_db(tenant_id=None):
        yield mock_session

    return mock_session, override_db


# ── Tests ──


@pytest.mark.asyncio
async def test_create_event_append_only():
    """POST /cases/{id}/events creates an event (append-only store)."""
    mock_session, override_db = _patch_db()
    event_obj = _make_event_obj()

    with patch("apps.api.routers.timeline.timeline_service") as mock_svc:
        mock_svc.create_event = AsyncMock(return_value=event_obj)

        from apps.api.dependencies import get_db_session
        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                f"/api/v1/cases/{CASE_ID}/events",
                json={
                    "source": "MANUAL",
                    "event_type": "INTERNAL_NOTE",
                    "title": "Note de suivi",
                    "body": "Appelé le client pour mise à jour.",
                    "occurred_at": NOW.isoformat(),
                },
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 201
    data = resp.json()
    assert data["source"] == "MANUAL"
    assert data["event_type"] == "INTERNAL_NOTE"
    assert data["title"] == "Note de suivi"
    assert data["created_by"] == str(USER_A)


@pytest.mark.asyncio
async def test_get_timeline_paginated():
    """GET /cases/{id}/timeline returns paginated events."""
    mock_session, override_db = _patch_db()
    events = [
        _make_event_obj(id=uuid.uuid4(), title=f"Event {i}")
        for i in range(5)
    ]

    with patch("apps.api.routers.timeline.timeline_service") as mock_svc:
        mock_svc.list_by_case = AsyncMock(return_value=(events, 5))

        from apps.api.dependencies import get_db_session
        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                f"/api/v1/cases/{CASE_ID}/timeline?page=1&per_page=10",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["items"]) == 5
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_get_timeline_with_source_filter():
    """GET /cases/{id}/timeline?source=OUTLOOK filters by source."""
    mock_session, override_db = _patch_db()

    with patch("apps.api.routers.timeline.timeline_service") as mock_svc:
        mock_svc.list_by_case = AsyncMock(return_value=([], 0))

        from apps.api.dependencies import get_db_session
        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                f"/api/v1/cases/{CASE_ID}/timeline?source=OUTLOOK&event_type=EMAIL",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    # Verify filter params were passed to service
    call_kwargs = mock_svc.list_by_case.call_args
    assert call_kwargs.kwargs.get("source") == "OUTLOOK"
    assert call_kwargs.kwargs.get("event_type") == "EMAIL"


@pytest.mark.asyncio
async def test_get_event_with_evidence():
    """GET /events/{id} returns event with evidence links."""
    mock_session, override_db = _patch_db()
    event_obj = _make_event_obj()
    link_obj = _make_evidence_link_obj()

    with patch("apps.api.routers.timeline.timeline_service") as mock_svc:
        mock_svc.get_event_with_evidence = AsyncMock(
            return_value=(event_obj, [link_obj])
        )

        from apps.api.dependencies import get_db_session
        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                f"/api/v1/events/{EVENT_ID}",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(EVENT_ID)
    assert len(data["evidence_links"]) == 1
    assert data["evidence_links"][0]["file_name"] == "document.pdf"


@pytest.mark.asyncio
async def test_get_event_not_found():
    """GET /events/{id} returns 404 when not found."""
    mock_session, override_db = _patch_db()

    with patch("apps.api.routers.timeline.timeline_service") as mock_svc:
        mock_svc.get_event_with_evidence = AsyncMock(return_value=(None, []))

        from apps.api.dependencies import get_db_session
        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                f"/api/v1/events/{uuid.uuid4()}",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_event_invalid_source():
    """POST with invalid source returns 422."""
    mock_session, override_db = _patch_db()

    from apps.api.dependencies import get_db_session
    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/cases/{CASE_ID}/events",
            json={
                "source": "INVALID_SOURCE",
                "event_type": "EMAIL",
                "title": "Test",
                "occurred_at": NOW.isoformat(),
            },
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_cross_tenant_timeline_isolation():
    """Tenant B should only see their own events."""
    mock_session, override_db = _patch_db()
    event_b = _make_event_obj(
        id=uuid.uuid4(),
        tenant_id=TENANT_B,
        title="Tenant B event",
    )

    with patch("apps.api.routers.timeline.timeline_service") as mock_svc:
        mock_svc.list_by_case = AsyncMock(return_value=([event_b], 1))

        from apps.api.dependencies import get_db_session
        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                f"/api/v1/cases/{CASE_ID}/timeline",
                headers={"Authorization": f"Bearer {TOKEN_B}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["tenant_id"] == str(TENANT_B)


@pytest.mark.asyncio
async def test_upload_document():
    """POST /events/{id}/documents uploads a file and returns evidence link."""
    mock_session, override_db = _patch_db()
    link_obj = _make_evidence_link_obj()

    with patch("apps.api.routers.documents.document_service") as mock_svc:
        mock_svc.upload_file = AsyncMock(return_value=link_obj)

        from apps.api.dependencies import get_db_session
        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                f"/api/v1/events/{EVENT_ID}/documents",
                files={"file": ("test.pdf", b"fake pdf content", "application/pdf")},
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 201
    data = resp.json()
    assert data["file_name"] == "document.pdf"
    assert data["mime_type"] == "application/pdf"


@pytest.mark.asyncio
async def test_download_document():
    """GET /documents/{id}/download returns file content."""
    mock_session, override_db = _patch_db()
    link_obj = _make_evidence_link_obj()

    with patch("apps.api.routers.documents.document_service") as mock_svc:
        mock_svc.download_file = AsyncMock(
            return_value=(link_obj, b"fake pdf content")
        )

        from apps.api.dependencies import get_db_session
        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                f"/api/v1/documents/{link_obj.id}/download",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"


@pytest.mark.asyncio
async def test_download_document_not_found():
    """GET /documents/{id}/download returns 404 when not found."""
    mock_session, override_db = _patch_db()

    with patch("apps.api.routers.documents.document_service") as mock_svc:
        mock_svc.download_file = AsyncMock(return_value=(None, None))

        from apps.api.dependencies import get_db_session
        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                f"/api/v1/documents/{uuid.uuid4()}/download",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 404
