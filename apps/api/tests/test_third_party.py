"""Tests for Third-Party Account router — list, create, balance."""

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
CASE_ID = uuid.uuid4()
ENTRY_ID = uuid.uuid4()

TOKEN_A = create_access_token(USER_A, TENANT_A, "partner", "alice@alpha.be")
TOKEN_B = create_access_token(USER_B, TENANT_B, "partner", "bob@beta.be")

NOW = datetime(2026, 2, 15, 12, 0, 0)


def _make_entry_obj(**overrides):
    defaults = {
        "id": ENTRY_ID,
        "tenant_id": TENANT_A,
        "case_id": CASE_ID,
        "entry_type": "deposit",
        "amount_cents": 50000,
        "description": "Provision initiale",
        "reference": "PRO-2026-001",
        "entry_date": date(2026, 2, 15),
        "created_by": USER_A,
        "created_at": NOW,
    }
    defaults.update(overrides)

    class MockEntry:
        pass

    obj = MockEntry()
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
async def test_list_third_party_entries():
    mock_session, override_db = _patch_db()
    entries = [
        _make_entry_obj(),
        _make_entry_obj(
            id=uuid.uuid4(),
            entry_type="withdrawal",
            amount_cents=10000,
            reference="WIT-2026-001",
        ),
    ]

    with patch("apps.api.routers.third_party.third_party_service") as mock_svc:
        mock_svc.list_by_case = AsyncMock(return_value=(entries, 2))

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                f"/api/v1/cases/{CASE_ID}/third-party",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["per_page"] == 50


@pytest.mark.asyncio
async def test_list_third_party_entries_empty():
    mock_session, override_db = _patch_db()

    with patch("apps.api.routers.third_party.third_party_service") as mock_svc:
        mock_svc.list_by_case = AsyncMock(return_value=([], 0))

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                f"/api/v1/cases/{CASE_ID}/third-party",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_list_third_party_entries_paginated():
    mock_session, override_db = _patch_db()
    entries = [_make_entry_obj()]

    with patch("apps.api.routers.third_party.third_party_service") as mock_svc:
        mock_svc.list_by_case = AsyncMock(return_value=(entries, 10))

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                f"/api/v1/cases/{CASE_ID}/third-party?page=2&per_page=5",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["page"] == 2
    assert data["per_page"] == 5
    # Verify pagination params were passed to service
    call_kwargs = mock_svc.list_by_case.call_args
    assert call_kwargs.kwargs["page"] == 2
    assert call_kwargs.kwargs["per_page"] == 5


@pytest.mark.asyncio
async def test_create_third_party_entry():
    mock_session, override_db = _patch_db()
    entry = _make_entry_obj()

    with patch("apps.api.routers.third_party.third_party_service") as mock_svc:
        mock_svc.create_entry = AsyncMock(return_value=entry)

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/v1/cases/{CASE_ID}/third-party",
                json={
                    "entry_type": "deposit",
                    "amount_cents": 50000,
                    "description": "Provision initiale",
                    "reference": "PRO-2026-001",
                    "entry_date": "2026-02-15",
                },
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 201
    data = resp.json()
    assert data["entry_type"] == "deposit"
    assert data["amount_cents"] == 50000
    assert data["reference"] == "PRO-2026-001"


@pytest.mark.asyncio
async def test_create_third_party_entry_invalid_type():
    mock_session, override_db = _patch_db()

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            f"/api/v1/cases/{CASE_ID}/third-party",
            json={
                "entry_type": "invalid_type",
                "amount_cents": 50000,
                "description": "Test",
                "reference": "REF-001",
                "entry_date": "2026-02-15",
            },
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_third_party_entry_missing_required_fields():
    mock_session, override_db = _patch_db()

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            f"/api/v1/cases/{CASE_ID}/third-party",
            json={"entry_type": "deposit"},
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_third_party_entry_service_value_error():
    mock_session, override_db = _patch_db()

    with patch("apps.api.routers.third_party.third_party_service") as mock_svc:
        mock_svc.create_entry = AsyncMock(side_effect=ValueError("Case not found"))

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/v1/cases/{CASE_ID}/third-party",
                json={
                    "entry_type": "deposit",
                    "amount_cents": 50000,
                    "description": "Test",
                    "reference": "REF-001",
                    "entry_date": "2026-02-15",
                },
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_create_third_party_entry_service_exception():
    mock_session, override_db = _patch_db()

    with patch("apps.api.routers.third_party.third_party_service") as mock_svc:
        mock_svc.create_entry = AsyncMock(side_effect=RuntimeError("DB error"))

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/v1/cases/{CASE_ID}/third-party",
                json={
                    "entry_type": "withdrawal",
                    "amount_cents": 10000,
                    "description": "Test",
                    "reference": "REF-002",
                    "entry_date": "2026-02-15",
                },
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_get_third_party_balance():
    mock_session, override_db = _patch_db()

    with patch("apps.api.routers.third_party.third_party_service") as mock_svc:
        mock_svc.calculate_balance = AsyncMock(
            return_value={
                "case_id": CASE_ID,
                "deposits": 50000,
                "withdrawals": 10000,
                "interest": 500,
                "balance": 40500,
            }
        )

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                f"/api/v1/cases/{CASE_ID}/third-party/balance",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["deposits"] == 50000
    assert data["withdrawals"] == 10000
    assert data["interest"] == 500
    assert data["balance"] == 40500


@pytest.mark.asyncio
async def test_get_third_party_balance_zero():
    mock_session, override_db = _patch_db()

    with patch("apps.api.routers.third_party.third_party_service") as mock_svc:
        mock_svc.calculate_balance = AsyncMock(
            return_value={
                "case_id": CASE_ID,
                "deposits": 0,
                "withdrawals": 0,
                "interest": 0,
                "balance": 0,
            }
        )

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                f"/api/v1/cases/{CASE_ID}/third-party/balance",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["balance"] == 0


@pytest.mark.asyncio
async def test_cross_tenant_isolation():
    """Verify different tenants get their own entries."""
    mock_session, override_db = _patch_db()
    entry_b = _make_entry_obj(
        id=uuid.uuid4(),
        tenant_id=TENANT_B,
        case_id=CASE_ID,
    )

    with patch("apps.api.routers.third_party.third_party_service") as mock_svc:
        mock_svc.list_by_case = AsyncMock(return_value=([entry_b], 1))

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                f"/api/v1/cases/{CASE_ID}/third-party",
                headers={"Authorization": f"Bearer {TOKEN_B}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["tenant_id"] == str(TENANT_B)
