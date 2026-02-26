"""Tests for Events router — SSE stream endpoint."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.auth.jwt import create_access_token
from apps.api.dependencies import get_current_tenant, get_db_session
from apps.api.main import app

TENANT_ID = uuid.uuid4()
USER_ID = uuid.uuid4()
TOKEN = create_access_token(USER_ID, TENANT_ID, "partner", "events@test.be")
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_events_stream_requires_auth():
    """GET /api/v1/events/stream without auth should fail."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/events/stream")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_events_stream_returns_sse():
    """GET /api/v1/events/stream should return text/event-stream content type."""

    async def override_tenant():
        return TENANT_ID

    async def override_db(tenant_id=None):
        yield AsyncMock()

    app.dependency_overrides[get_current_tenant] = override_tenant
    app.dependency_overrides[get_db_session] = override_db

    # Mock the SSE manager to yield one event then stop
    async def mock_subscribe(tenant_id):
        yield 'data: {"type": "ping"}\n\n'

    with (
        patch("apps.api.routers.events.sse_manager") as mock_sse,
        patch("apps.api.middleware.audit.get_tenant_session"),
        patch("apps.api.middleware.audit.get_superadmin_session"),
    ):
        mock_sse.subscribe = mock_subscribe

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/events/stream", headers=HEADERS)
            assert response.status_code == 200
            content_type = response.headers.get("content-type", "")
            assert "text/event-stream" in content_type
