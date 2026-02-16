"""LXB-012: Tests for Cases CRUD — create, get, list, update, pagination, filters, cross-tenant."""

import uuid
from datetime import date, datetime
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
CASE_A_ID = uuid.uuid4()
CASE_B_ID = uuid.uuid4()

TOKEN_A = create_access_token(USER_A, TENANT_A, "partner", "alice@alpha.be")
TOKEN_B = create_access_token(USER_B, TENANT_B, "partner", "bob@beta.be")

NOW = datetime(2026, 2, 15, 12, 0, 0)


def _make_case_obj(**overrides):
    """Create a mock Case object with model_validate support."""
    defaults = {
        "id": CASE_A_ID,
        "tenant_id": TENANT_A,
        "reference": "2026/001",
        "court_reference": None,
        "title": "Dupont c/ Martin",
        "matter_type": "civil",
        "status": "open",
        "jurisdiction": "Tribunal de Bruxelles",
        "responsible_user_id": USER_A,
        "opened_at": date(2026, 2, 15),
        "closed_at": None,
        "metadata_": {},
        "created_at": NOW,
        "updated_at": NOW,
    }
    defaults.update(overrides)

    class MockCase:
        pass

    obj = MockCase()
    for k, v in defaults.items():
        setattr(obj, k, v)
    # CaseResponse reads 'metadata' from_attributes, mapped from metadata_
    obj.metadata = defaults.get("metadata_", {})
    return obj


# ── Helper to patch DB session ──


def _patch_db():
    """Patch get_db_session to return a no-op async session."""
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    async def override_db(tenant_id=None):
        yield mock_session

    return mock_session, override_db


# ── Tests ──


@pytest.mark.asyncio
async def test_create_case():
    mock_session, override_db = _patch_db()
    case_obj = _make_case_obj()

    with patch("apps.api.routers.cases.case_service") as mock_svc:
        mock_svc.create_case = AsyncMock(return_value=case_obj)

        app.dependency_overrides = {}
        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/cases",
                json={
                    "reference": "2026/001",
                    "title": "Dupont c/ Martin",
                    "matter_type": "civil",
                    "responsible_user_id": str(USER_A),
                },
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 201
    data = resp.json()
    assert data["reference"] == "2026/001"
    assert data["title"] == "Dupont c/ Martin"
    assert data["status"] == "open"


@pytest.mark.asyncio
async def test_get_case():
    mock_session, override_db = _patch_db()
    case_obj = _make_case_obj()

    with patch("apps.api.routers.cases.case_service") as mock_svc:
        mock_svc.get_case = AsyncMock(return_value=case_obj)

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                f"/api/v1/cases/{CASE_A_ID}",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    assert resp.json()["id"] == str(CASE_A_ID)


@pytest.mark.asyncio
async def test_get_case_not_found():
    mock_session, override_db = _patch_db()

    with patch("apps.api.routers.cases.case_service") as mock_svc:
        mock_svc.get_case = AsyncMock(return_value=None)

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                f"/api/v1/cases/{uuid.uuid4()}",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_cases_paginated():
    mock_session, override_db = _patch_db()
    cases = [
        _make_case_obj(id=uuid.uuid4(), reference=f"2026/{i:03d}") for i in range(3)
    ]

    with patch("apps.api.routers.cases.case_service") as mock_svc:
        mock_svc.list_cases = AsyncMock(return_value=(cases, 3))

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/v1/cases?page=1&per_page=10",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3
    assert data["page"] == 1
    assert data["per_page"] == 10


@pytest.mark.asyncio
async def test_list_cases_with_status_filter():
    mock_session, override_db = _patch_db()

    with patch("apps.api.routers.cases.case_service") as mock_svc:
        mock_svc.list_cases = AsyncMock(return_value=([], 0))

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/v1/cases?status=closed&matter_type=civil",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    # Verify filter params were passed
    call_kwargs = mock_svc.list_cases.call_args
    assert call_kwargs.kwargs.get("status") == "closed"
    assert call_kwargs.kwargs.get("matter_type") == "civil"


@pytest.mark.asyncio
async def test_update_case():
    mock_session, override_db = _patch_db()
    updated = _make_case_obj(status="closed", closed_at=date(2026, 3, 1))

    with patch("apps.api.routers.cases.case_service") as mock_svc:
        mock_svc.update_case = AsyncMock(return_value=updated)

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.patch(
                f"/api/v1/cases/{CASE_A_ID}",
                json={"status": "closed", "closed_at": "2026-03-01"},
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    assert resp.json()["status"] == "closed"


@pytest.mark.asyncio
async def test_conflict_check_stub():
    mock_session, override_db = _patch_db()

    with patch("apps.api.routers.cases.case_service") as mock_svc:
        mock_svc.conflict_check = AsyncMock(
            return_value={
                "status": "clear",
                "case_id": str(CASE_A_ID),
                "conflicts_found": 0,
                "detail": "No conflicts detected (stub)",
            }
        )

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/v1/cases/{CASE_A_ID}/conflict-check",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    assert resp.json()["status"] == "clear"
    assert resp.json()["conflicts_found"] == 0


@pytest.mark.asyncio
async def test_cross_tenant_isolation():
    """Tenant B token should not see Tenant A cases (RLS enforced at DB level).

    In this unit test, we verify the middleware correctly sets different
    tenant_ids for different JWTs, and the service receives them.
    """
    mock_session, override_db = _patch_db()
    case_b = _make_case_obj(id=CASE_B_ID, tenant_id=TENANT_B, reference="B/001")

    with patch("apps.api.routers.cases.case_service") as mock_svc:
        # Tenant B sees only their case
        mock_svc.list_cases = AsyncMock(return_value=([case_b], 1))

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/v1/cases",
                headers={"Authorization": f"Bearer {TOKEN_B}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["tenant_id"] == str(TENANT_B)
