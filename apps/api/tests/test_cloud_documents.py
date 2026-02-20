"""Tests for Cloud Documents router — list, search, get, content, link-case, sync."""

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
DOC_ID = uuid.uuid4()
CASE_ID = uuid.uuid4()
OAUTH_TOKEN_ID = uuid.uuid4()

TOKEN_A = create_access_token(USER_A, TENANT_A, "partner", "alice@alpha.be")

NOW = datetime(2026, 2, 15, 12, 0, 0)


def _make_cloud_doc(**overrides):
    defaults = {
        "id": DOC_ID,
        "tenant_id": TENANT_A,
        "oauth_token_id": OAUTH_TOKEN_ID,
        "case_id": None,
        "provider": "google_drive",
        "external_id": "ext-123",
        "name": "Contract.pdf",
        "mime_type": "application/pdf",
        "size_bytes": 12345,
        "web_url": "https://drive.google.com/file/123",
        "edit_url": None,
        "thumbnail_url": None,
        "is_folder": False,
        "path": "/Documents",
        "last_modified_at": NOW,
        "last_modified_by": "user@example.com",
        "is_indexed": True,
        "index_status": "completed",
        "created_at": NOW,
        "updated_at": NOW,
        "external_parent_id": None,
    }
    defaults.update(overrides)

    class MockDoc:
        pass

    obj = MockDoc()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _make_sync_job(**overrides):
    defaults = {
        "id": uuid.uuid4(),
        "tenant_id": TENANT_A,
        "oauth_token_id": OAUTH_TOKEN_ID,
        "job_type": "full_sync",
        "status": "completed",
        "provider": "google_drive",
        "scope": "all",
        "total_items": 100,
        "processed_items": 100,
        "error_count": 0,
        "started_at": NOW,
        "completed_at": NOW,
        "error_message": None,
        "created_at": NOW,
    }
    defaults.update(overrides)

    class MockJob:
        pass

    obj = MockJob()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _make_oauth_token(**overrides):
    defaults = {
        "id": OAUTH_TOKEN_ID,
        "tenant_id": TENANT_A,
        "provider": "google",
    }
    defaults.update(overrides)

    class MockToken:
        pass

    obj = MockToken()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _patch_db():
    mock_session = AsyncMock()

    async def override_db(tenant_id=None):
        yield mock_session

    return mock_session, override_db


def _make_scalars_result(items):
    """Create a mock result for session.execute() that supports .scalars().all()."""
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = items
    mock_result.scalars.return_value = mock_scalars
    mock_result.scalar.return_value = len(items)
    mock_result.scalar_one_or_none.return_value = items[0] if items else None
    return mock_result


def _make_count_result(count):
    """Create a mock result for count queries."""
    mock_result = MagicMock()
    mock_result.scalar.return_value = count
    return mock_result


# ── Tests ──


@pytest.mark.asyncio
async def test_list_cloud_documents():
    mock_session, override_db = _patch_db()
    docs = [_make_cloud_doc(), _make_cloud_doc(id=uuid.uuid4(), name="Brief.docx")]

    # First call: count query, Second call: paginated query
    count_result = _make_count_result(2)
    docs_result = _make_scalars_result(docs)
    mock_session.execute = AsyncMock(side_effect=[count_result, docs_result])

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/cloud-documents",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["documents"]) == 2
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_search_cloud_documents():
    mock_session, override_db = _patch_db()
    docs = [_make_cloud_doc(name="Contract.pdf")]

    docs_result = _make_scalars_result(docs)
    mock_session.execute = AsyncMock(return_value=docs_result)

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/cloud-documents/search?q=Contract",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["query"] == "Contract"
    assert data["total"] == 1
    assert data["results"][0]["name"] == "Contract.pdf"


@pytest.mark.asyncio
async def test_search_cloud_documents_requires_query():
    mock_session, override_db = _patch_db()

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/cloud-documents/search",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_cloud_document():
    mock_session, override_db = _patch_db()
    doc = _make_cloud_doc()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = doc
    mock_session.execute = AsyncMock(return_value=mock_result)

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            f"/api/v1/cloud-documents/{DOC_ID}",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(DOC_ID)
    assert data["name"] == "Contract.pdf"


@pytest.mark.asyncio
async def test_get_cloud_document_not_found():
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
            f"/api/v1/cloud-documents/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_cloud_document_content_folder_error():
    """Downloading a folder should return 400."""
    mock_session, override_db = _patch_db()
    folder = _make_cloud_doc(is_folder=True, name="MyFolder")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = folder
    mock_session.execute = AsyncMock(return_value=mock_result)

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            f"/api/v1/cloud-documents/{DOC_ID}/content",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_get_cloud_document_content_not_found():
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
            f"/api/v1/cloud-documents/{uuid.uuid4()}/content",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_link_document_to_case():
    mock_session, override_db = _patch_db()
    doc = _make_cloud_doc()

    # First execute: find doc, second: check existing link, then add+commit+refresh
    doc_result = MagicMock()
    doc_result.scalar_one_or_none.return_value = doc

    no_link_result = MagicMock()
    no_link_result.scalar_one_or_none.return_value = None

    mock_session.execute = AsyncMock(side_effect=[doc_result, no_link_result])
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    link_id = uuid.uuid4()

    async def mock_refresh(obj):
        obj.id = link_id
        obj.cloud_document_id = DOC_ID
        obj.case_id = CASE_ID
        obj.link_type = "reference"
        obj.notes = None
        obj.created_at = NOW

    mock_session.refresh = AsyncMock(side_effect=mock_refresh)

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            f"/api/v1/cloud-documents/{DOC_ID}/link-case",
            json={"case_id": str(CASE_ID)},
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["case_id"] == str(CASE_ID)
    assert data["link_type"] == "reference"


@pytest.mark.asyncio
async def test_link_document_to_case_not_found():
    mock_session, override_db = _patch_db()

    doc_result = MagicMock()
    doc_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=doc_result)

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            f"/api/v1/cloud-documents/{uuid.uuid4()}/link-case",
            json={"case_id": str(CASE_ID)},
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_link_document_to_case_conflict():
    mock_session, override_db = _patch_db()
    doc = _make_cloud_doc()

    doc_result = MagicMock()
    doc_result.scalar_one_or_none.return_value = doc

    existing_link = MagicMock()
    link_result = MagicMock()
    link_result.scalar_one_or_none.return_value = existing_link

    mock_session.execute = AsyncMock(side_effect=[doc_result, link_result])

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            f"/api/v1/cloud-documents/{DOC_ID}/link-case",
            json={"case_id": str(CASE_ID)},
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_unlink_document_from_case():
    mock_session, override_db = _patch_db()

    link_mock = MagicMock()
    link_result = MagicMock()
    link_result.scalar_one_or_none.return_value = link_mock
    mock_session.execute = AsyncMock(return_value=link_result)
    mock_session.delete = AsyncMock()
    mock_session.commit = AsyncMock()

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.delete(
            f"/api/v1/cloud-documents/{DOC_ID}/link-case/{CASE_ID}",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_unlink_document_from_case_not_found():
    mock_session, override_db = _patch_db()

    link_result = MagicMock()
    link_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=link_result)

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.delete(
            f"/api/v1/cloud-documents/{DOC_ID}/link-case/{CASE_ID}",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_start_sync():
    mock_session, override_db = _patch_db()
    token = _make_oauth_token()

    token_result = MagicMock()
    token_result.scalar_one_or_none.return_value = token
    mock_session.execute = AsyncMock(return_value=token_result)
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    job_id = uuid.uuid4()

    async def mock_refresh(obj):
        obj.id = job_id

    mock_session.refresh = AsyncMock(side_effect=mock_refresh)

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    with patch("apps.api.routers.cloud_documents.sync_documents", create=True):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/sync",
                json={"connection_id": str(OAUTH_TOKEN_ID)},
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

    app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "started"


@pytest.mark.asyncio
async def test_start_sync_connection_not_found():
    mock_session, override_db = _patch_db()

    token_result = MagicMock()
    token_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=token_result)

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/v1/sync",
            json={"connection_id": str(uuid.uuid4())},
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_sync_history():
    mock_session, override_db = _patch_db()
    jobs = [_make_sync_job()]

    count_result = _make_count_result(1)
    jobs_result = _make_scalars_result(jobs)
    mock_session.execute = AsyncMock(side_effect=[count_result, jobs_result])

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/sync/history",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["jobs"]) == 1


@pytest.mark.asyncio
async def test_get_sync_job():
    mock_session, override_db = _patch_db()
    job = _make_sync_job()
    job_id = job.id

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = job
    mock_session.execute = AsyncMock(return_value=mock_result)

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            f"/api/v1/sync/{job_id}",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(job_id)
    assert data["status"] == "completed"


@pytest.mark.asyncio
async def test_get_sync_job_not_found():
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
            f"/api/v1/sync/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 404
