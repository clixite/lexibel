"""Tests for Calls router — call listing and stats."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.auth.jwt import create_access_token
from apps.api.dependencies import get_current_user, get_db_session
from apps.api.main import app

TENANT_ID = uuid.uuid4()
USER_ID = uuid.uuid4()
TOKEN = create_access_token(USER_ID, TENANT_ID, "partner", "calls@test.be")
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


def _patch_deps():
    """Override auth + DB dependencies."""
    mock_session = AsyncMock()

    async def override_user(request=None):
        return {
            "user_id": USER_ID,
            "tenant_id": TENANT_ID,
            "role": "partner",
            "email": "calls@test.be",
        }

    async def override_db(tenant_id=None):
        yield mock_session

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db_session] = override_db
    return mock_session


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    app.dependency_overrides.clear()


def _make_event(**overrides):
    defaults = {
        "id": uuid.uuid4(),
        "tenant_id": TENANT_ID,
        "source": "RINGOVER",
        "event_type": "CALL",
        "title": "Appel entrant",
        "body": None,
        "case_id": None,
        "occurred_at": datetime(2026, 2, 20, 10, 0),
        "metadata_": {"direction": "inbound", "duration_seconds": 120},
        "created_at": datetime(2026, 2, 20, 10, 0),
    }
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


@pytest.mark.asyncio
async def test_list_calls_success():
    """GET /api/v1/calls should return call list."""
    mock_session = _patch_deps()
    events = [_make_event(), _make_event()]

    # Mock the DB query result
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = events
    mock_session.execute = AsyncMock(return_value=mock_result)

    with patch("apps.api.routers.calls.os") as mock_os:
        mock_os.getenv.return_value = None  # No RINGOVER_API_KEY
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/calls", headers=HEADERS)

    assert response.status_code == 200
    data = response.json()
    assert "calls" in data
    assert len(data["calls"]) == 2


@pytest.mark.asyncio
async def test_list_calls_requires_auth():
    """GET /api/v1/calls without auth should fail."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/calls")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_call_stats():
    """GET /api/v1/calls/stats should return statistics."""
    mock_session = _patch_deps()

    # Mock scalar result for total count
    mock_result = MagicMock()
    mock_result.scalar.return_value = 42
    mock_session.execute = AsyncMock(return_value=mock_result)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/calls/stats", headers=HEADERS)

    assert response.status_code == 200
    data = response.json()
    assert data["total_calls"] == 42
