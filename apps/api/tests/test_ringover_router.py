"""Tests for Ringover router — call management, details, stats."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.auth.jwt import create_access_token
from apps.api.dependencies import get_current_tenant, get_current_user, get_db_session
from apps.api.main import app

TENANT_ID = uuid.uuid4()
USER_ID = uuid.uuid4()
TOKEN = create_access_token(USER_ID, TENANT_ID, "partner", "ringover@test.be")
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


def _override_deps():
    mock_session = AsyncMock()

    async def override_user(request=None):
        return {
            "user_id": USER_ID,
            "tenant_id": TENANT_ID,
            "role": "partner",
            "email": "ringover@test.be",
        }

    async def override_db(tenant_id=None):
        yield mock_session

    async def override_tenant(request=None):
        return TENANT_ID

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_current_tenant] = override_tenant
    return mock_session


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    app.dependency_overrides.clear()


def _make_call_event(**overrides):
    defaults = {
        "id": uuid.uuid4(),
        "tenant_id": TENANT_ID,
        "source": "RINGOVER",
        "event_type": "CALL",
        "title": "Appel entrant - +32470123456",
        "body": None,
        "occurred_at": datetime(2026, 2, 20, 10, 0),
        "metadata_": {
            "direction": "inbound",
            "duration_seconds": 120,
            "caller_number": "+32470123456",
            "call_type": "answered",
        },
        "created_at": datetime(2026, 2, 20, 10, 0),
        "case_id": None,
        "contact_id": None,
    }
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


@pytest.mark.asyncio
async def test_list_calls():
    """GET /api/v1/ringover/calls should list calls with pagination."""
    mock_session = _override_deps()

    events = [_make_call_event(), _make_call_event()]
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = events
    mock_count = MagicMock()
    mock_count.scalar_one.return_value = 2

    mock_session.execute = AsyncMock(side_effect=[mock_count, mock_result])

    with patch(
        "apps.api.routers.ringover.RingoverClient", side_effect=Exception("no key")
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/ringover/calls", headers=HEADERS)

    assert response.status_code == 200
    data = response.json()
    assert "items" in data or "calls" in data


@pytest.mark.asyncio
async def test_call_stats():
    """GET /api/v1/ringover/stats should return call statistics."""
    mock_session = _override_deps()

    mock_result = MagicMock()
    mock_result.scalar_one.return_value = 10
    mock_result.scalar.return_value = 10
    mock_session.execute = AsyncMock(return_value=mock_result)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/api/v1/ringover/stats", headers=HEADERS, params={"days": 30}
        )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_ringover_requires_auth():
    """Ringover endpoints should require authentication."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/ringover/calls")
    assert response.status_code in (401, 403)
