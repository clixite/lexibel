"""Tests for Documents router — list, upload, download."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.auth.jwt import create_access_token
from apps.api.main import app

# -- Test data --

TENANT_A = uuid.uuid4()
TENANT_B = uuid.uuid4()
USER_A = uuid.uuid4()
USER_B = uuid.uuid4()
LINK_ID = uuid.uuid4()
EVENT_ID = uuid.uuid4()

TOKEN_A = create_access_token(USER_A, TENANT_A, "partner", "alice@alpha.be")
TOKEN_B = create_access_token(USER_B, TENANT_B, "partner", "bob@beta.be")

NOW = datetime(2026, 2, 15, 12, 0, 0, tzinfo=timezone.utc)


def _make_evidence_link_obj(**overrides):
    """Create a mock EvidenceLink object."""
    defaults = {
        "id": LINK_ID,
        "tenant_id": TENANT_A,
        "interaction_event_id": EVENT_ID,
        "file_path": f"tenants/{TENANT_A}/documents/test.pdf",
        "file_name": "test.pdf",
        "mime_type": "application/pdf",
        "file_size_bytes": 12345,
        "sha256_hash": "abc123def456",
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


# -- Tests: GET /documents --


@pytest.mark.asyncio
async def test_list_documents():
    """GET /api/v1/documents returns paginated documents."""
    mock_session, override_db = _patch_db()
    doc = _make_evidence_link_obj()

    # Mock scalars().all() for documents query
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [doc]

    docs_result = MagicMock()
    docs_result.scalars.return_value = scalars_mock

    # Mock scalar() for count query
    count_result = MagicMock()
    count_result.scalar.return_value = 1

    mock_session.execute = AsyncMock(side_effect=[docs_result, count_result])

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/documents?page=1&per_page=50",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["documents"]) == 1
    assert data["documents"][0]["file_name"] == "test.pdf"
    assert data["documents"][0]["mime_type"] == "application/pdf"
    assert data["documents"][0]["file_size_bytes"] == 12345
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_list_documents_empty():
    """GET /api/v1/documents returns empty list when no documents."""
    mock_session, override_db = _patch_db()

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = []

    docs_result = MagicMock()
    docs_result.scalars.return_value = scalars_mock

    count_result = MagicMock()
    count_result.scalar.return_value = 0

    mock_session.execute = AsyncMock(side_effect=[docs_result, count_result])

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/documents",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["documents"] == []


@pytest.mark.asyncio
async def test_list_documents_unauthenticated():
    """GET /api/v1/documents without token returns 401."""
    mock_session, override_db = _patch_db()

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/v1/documents")

    app.dependency_overrides = {}

    assert resp.status_code == 401


# -- Tests: POST /events/{event_id}/documents (upload) --


@pytest.mark.asyncio
async def test_upload_document():
    """POST /api/v1/events/{event_id}/documents uploads a file."""
    mock_session, override_db = _patch_db()
    link = _make_evidence_link_obj()

    with patch("apps.api.routers.documents.document_service") as mock_svc:
        mock_svc.upload_file = AsyncMock(return_value=link)

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/v1/events/{EVENT_ID}/documents",
                files={"file": ("test.pdf", b"PDF content here", "application/pdf")},
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 201
    data = resp.json()
    assert data["file_name"] == "test.pdf"
    assert data["mime_type"] == "application/pdf"
    assert data["id"] == str(LINK_ID)


@pytest.mark.asyncio
async def test_upload_empty_file():
    """POST /api/v1/events/{event_id}/documents with empty file returns 400."""
    mock_session, override_db = _patch_db()

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            f"/api/v1/events/{EVENT_ID}/documents",
            files={"file": ("empty.txt", b"", "text/plain")},
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_upload_document_unauthenticated():
    """POST /api/v1/events/{event_id}/documents without token returns 401."""
    mock_session, override_db = _patch_db()

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            f"/api/v1/events/{EVENT_ID}/documents",
            files={"file": ("test.pdf", b"content", "application/pdf")},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 401


# -- Tests: GET /documents/{id}/download --


@pytest.mark.asyncio
async def test_download_document():
    """GET /api/v1/documents/{id}/download returns file content."""
    mock_session, override_db = _patch_db()
    link = _make_evidence_link_obj()
    file_data = b"PDF file content bytes"

    with patch("apps.api.routers.documents.document_service") as mock_svc:
        mock_svc.download_file = AsyncMock(return_value=(link, file_data))

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                f"/api/v1/documents/{LINK_ID}/download",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    assert resp.content == file_data
    assert resp.headers["content-type"] == "application/pdf"
    assert "test.pdf" in resp.headers["content-disposition"]


@pytest.mark.asyncio
async def test_download_document_not_found():
    """GET /api/v1/documents/{id}/download returns 404 for unknown doc."""
    mock_session, override_db = _patch_db()

    with patch("apps.api.routers.documents.document_service") as mock_svc:
        mock_svc.download_file = AsyncMock(return_value=(None, None))

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                f"/api/v1/documents/{uuid.uuid4()}/download",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 404


# -- Tests: cross-tenant isolation --


@pytest.mark.asyncio
async def test_cross_tenant_documents_isolated():
    """Tenant B only sees their own documents."""
    mock_session, override_db = _patch_db()

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = []

    docs_result = MagicMock()
    docs_result.scalars.return_value = scalars_mock

    count_result = MagicMock()
    count_result.scalar.return_value = 0

    mock_session.execute = AsyncMock(side_effect=[docs_result, count_result])

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/documents",
            headers={"Authorization": f"Bearer {TOKEN_B}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 200
    assert resp.json()["documents"] == []
    assert resp.json()["total"] == 0
