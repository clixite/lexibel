"""Tests for Time Entries router — CRUD + submit/approve workflow."""

import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.auth.jwt import create_access_token
from apps.api.main import app

# -- Test data --

TENANT_A = uuid.uuid4()
TENANT_B = uuid.uuid4()
USER_A = uuid.uuid4()
USER_B = uuid.uuid4()
ENTRY_ID = uuid.uuid4()
CASE_ID = uuid.uuid4()

TOKEN_A = create_access_token(USER_A, TENANT_A, "partner", "alice@alpha.be")
TOKEN_B = create_access_token(USER_B, TENANT_B, "partner", "bob@beta.be")

NOW = datetime(2026, 2, 15, 12, 0, 0, tzinfo=timezone.utc)


def _make_time_entry_obj(**overrides):
    """Create a mock TimeEntry object compatible with TimeEntryResponse."""
    defaults = {
        "id": ENTRY_ID,
        "tenant_id": TENANT_A,
        "case_id": CASE_ID,
        "user_id": USER_A,
        "description": "Recherche jurisprudence",
        "duration_minutes": 90,
        "billable": True,
        "date": date(2026, 2, 15),
        "rounding_rule": "6min",
        "source": "MANUAL",
        "status": "draft",
        "hourly_rate_cents": 15000,
        "approved_by": None,
        "created_at": NOW,
        "updated_at": NOW,
    }
    defaults.update(overrides)

    class MockTimeEntry:
        pass

    obj = MockTimeEntry()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _patch_db():
    mock_session = AsyncMock()

    async def override_db(tenant_id=None):
        yield mock_session

    return mock_session, override_db


# -- Tests: GET /time-entries --


@pytest.mark.asyncio
async def test_list_time_entries():
    """GET /api/v1/time-entries returns paginated time entries."""
    mock_session, override_db = _patch_db()
    entry = _make_time_entry_obj()

    with patch("apps.api.routers.time_entries.time_service") as mock_svc:
        mock_svc.list_time_entries = AsyncMock(return_value=([entry], 1))

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/v1/time-entries?page=1&per_page=20",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["description"] == "Recherche jurisprudence"
    assert data["items"][0]["duration_minutes"] == 90
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_list_time_entries_empty():
    """GET /api/v1/time-entries returns empty list."""
    mock_session, override_db = _patch_db()

    with patch("apps.api.routers.time_entries.time_service") as mock_svc:
        mock_svc.list_time_entries = AsyncMock(return_value=([], 0))

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/v1/time-entries",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    assert resp.json()["total"] == 0
    assert resp.json()["items"] == []


@pytest.mark.asyncio
async def test_list_time_entries_with_filters():
    """GET /api/v1/time-entries with filters passes them to service."""
    mock_session, override_db = _patch_db()

    with patch("apps.api.routers.time_entries.time_service") as mock_svc:
        mock_svc.list_time_entries = AsyncMock(return_value=([], 0))

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                f"/api/v1/time-entries?case_id={CASE_ID}&status=draft"
                f"&date_from=2026-02-01&date_to=2026-02-28",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    call_kwargs = mock_svc.list_time_entries.call_args
    assert call_kwargs.kwargs.get("case_id") == CASE_ID
    assert call_kwargs.kwargs.get("status") == "draft"
    assert call_kwargs.kwargs.get("date_from") == date(2026, 2, 1)
    assert call_kwargs.kwargs.get("date_to") == date(2026, 2, 28)


# -- Tests: POST /time-entries --


@pytest.mark.asyncio
async def test_create_time_entry():
    """POST /api/v1/time-entries creates a new time entry."""
    mock_session, override_db = _patch_db()
    entry = _make_time_entry_obj()

    with patch("apps.api.routers.time_entries.time_service") as mock_svc:
        mock_svc.create_time_entry = AsyncMock(return_value=entry)

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/time-entries",
                json={
                    "case_id": str(CASE_ID),
                    "description": "Recherche jurisprudence",
                    "duration_minutes": 90,
                    "billable": True,
                    "date": "2026-02-15",
                    "rounding_rule": "6min",
                    "source": "MANUAL",
                },
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 201
    data = resp.json()
    assert data["description"] == "Recherche jurisprudence"
    assert data["duration_minutes"] == 90
    assert data["status"] == "draft"
    assert data["billable"] is True


@pytest.mark.asyncio
async def test_create_time_entry_validation_error():
    """POST /api/v1/time-entries with missing fields returns 422."""
    mock_session, override_db = _patch_db()

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/v1/time-entries",
            json={"description": "Missing fields"},
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_time_entry_invalid_rounding():
    """POST /api/v1/time-entries with invalid rounding_rule returns 422."""
    mock_session, override_db = _patch_db()

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/v1/time-entries",
            json={
                "case_id": str(CASE_ID),
                "description": "Test",
                "duration_minutes": 30,
                "date": "2026-02-15",
                "rounding_rule": "invalid",
            },
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 422


# -- Tests: PATCH /time-entries/{id} --


@pytest.mark.asyncio
async def test_update_time_entry():
    """PATCH /api/v1/time-entries/{id} updates a draft entry."""
    mock_session, override_db = _patch_db()
    updated = _make_time_entry_obj(description="Updated description")

    with patch("apps.api.routers.time_entries.time_service") as mock_svc:
        mock_svc.update_time_entry = AsyncMock(return_value=updated)

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.patch(
                f"/api/v1/time-entries/{ENTRY_ID}",
                json={"description": "Updated description"},
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    assert resp.json()["description"] == "Updated description"


@pytest.mark.asyncio
async def test_update_time_entry_not_found():
    """PATCH /api/v1/time-entries/{id} returns 404 for unknown entry."""
    mock_session, override_db = _patch_db()

    with patch("apps.api.routers.time_entries.time_service") as mock_svc:
        mock_svc.update_time_entry = AsyncMock(return_value=None)

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.patch(
                f"/api/v1/time-entries/{uuid.uuid4()}",
                json={"description": "Update"},
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_time_entry_not_draft():
    """PATCH /api/v1/time-entries/{id} returns 409 for non-draft entry."""
    mock_session, override_db = _patch_db()
    submitted = _make_time_entry_obj(status="submitted")

    with patch("apps.api.routers.time_entries.time_service") as mock_svc:
        mock_svc.update_time_entry = AsyncMock(return_value=submitted)

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.patch(
                f"/api/v1/time-entries/{ENTRY_ID}",
                json={"description": "Try update"},
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 409


# -- Tests: POST /time-entries/{id}/submit --


@pytest.mark.asyncio
async def test_submit_time_entry():
    """POST /api/v1/time-entries/{id}/submit submits entry for approval."""
    mock_session, override_db = _patch_db()
    submitted = _make_time_entry_obj(status="submitted")

    with patch("apps.api.routers.time_entries.time_service") as mock_svc:
        mock_svc.submit_time_entry = AsyncMock(return_value=submitted)

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/v1/time-entries/{ENTRY_ID}/submit",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    assert resp.json()["status"] == "submitted"


@pytest.mark.asyncio
async def test_submit_time_entry_not_found():
    """POST /api/v1/time-entries/{id}/submit returns 404."""
    mock_session, override_db = _patch_db()

    with patch("apps.api.routers.time_entries.time_service") as mock_svc:
        mock_svc.submit_time_entry = AsyncMock(return_value=None)

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/v1/time-entries/{uuid.uuid4()}/submit",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_submit_already_submitted():
    """POST /api/v1/time-entries/{id}/submit returns 409 if already submitted."""
    mock_session, override_db = _patch_db()
    # Simulate service returning the entry but not changing status
    already = _make_time_entry_obj(status="approved")

    with patch("apps.api.routers.time_entries.time_service") as mock_svc:
        mock_svc.submit_time_entry = AsyncMock(return_value=already)

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/v1/time-entries/{ENTRY_ID}/submit",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 409


# -- Tests: POST /time-entries/{id}/approve --


@pytest.mark.asyncio
async def test_approve_time_entry():
    """POST /api/v1/time-entries/{id}/approve approves the entry."""
    mock_session, override_db = _patch_db()
    approved = _make_time_entry_obj(status="approved", approved_by=USER_A)

    with patch("apps.api.routers.time_entries.time_service") as mock_svc:
        mock_svc.approve_time_entry = AsyncMock(return_value=approved)

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/v1/time-entries/{ENTRY_ID}/approve",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "approved"
    assert data["approved_by"] == str(USER_A)


@pytest.mark.asyncio
async def test_approve_time_entry_not_found():
    """POST /api/v1/time-entries/{id}/approve returns 404."""
    mock_session, override_db = _patch_db()

    with patch("apps.api.routers.time_entries.time_service") as mock_svc:
        mock_svc.approve_time_entry = AsyncMock(return_value=None)

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/v1/time-entries/{uuid.uuid4()}/approve",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_approve_already_approved():
    """POST /api/v1/time-entries/{id}/approve returns 409 for draft entry."""
    mock_session, override_db = _patch_db()
    draft = _make_time_entry_obj(status="draft")

    with patch("apps.api.routers.time_entries.time_service") as mock_svc:
        mock_svc.approve_time_entry = AsyncMock(return_value=draft)

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/v1/time-entries/{ENTRY_ID}/approve",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 409


# -- Tests: cross-tenant isolation --


@pytest.mark.asyncio
async def test_cross_tenant_time_entries_isolated():
    """Tenant B sees only their time entries."""
    mock_session, override_db = _patch_db()
    entry_b = _make_time_entry_obj(
        id=uuid.uuid4(),
        tenant_id=TENANT_B,
        user_id=USER_B,
    )

    with patch("apps.api.routers.time_entries.time_service") as mock_svc:
        mock_svc.list_time_entries = AsyncMock(return_value=([entry_b], 1))

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/v1/time-entries",
                headers={"Authorization": f"Bearer {TOKEN_B}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["tenant_id"] == str(TENANT_B)
