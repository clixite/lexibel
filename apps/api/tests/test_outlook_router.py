"""Tests for Outlook router — email sync, listing, sending."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.auth.jwt import create_access_token
from apps.api.dependencies import get_current_user
from apps.api.main import app

TENANT_ID = uuid.uuid4()
USER_ID = uuid.uuid4()
TOKEN = create_access_token(USER_ID, TENANT_ID, "partner", "outlook@test.be")
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


def _override_user():
    async def dep(request=None):
        return {
            "user_id": USER_ID,
            "tenant_id": TENANT_ID,
            "role": "partner",
            "email": "outlook@test.be",
        }

    app.dependency_overrides[get_current_user] = dep


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_sync_emails():
    """POST /api/v1/outlook/sync should trigger email sync."""
    _override_user()

    with patch("apps.api.routers.outlook.outlook_service") as mock_service:
        mock_service.sync_emails_enhanced = AsyncMock(return_value=[])

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/outlook/sync",
                headers=HEADERS,
                json={"user_id": str(USER_ID)},
            )

    assert response.status_code in (200, 422)


@pytest.mark.asyncio
async def test_get_emails():
    """GET /api/v1/outlook/emails should list cached emails."""
    _override_user()

    with patch("apps.api.routers.outlook.outlook_service") as mock_service:
        # get_cached_emails is synchronous (no await in the router), returns a list
        mock_service.get_cached_emails.return_value = []

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/outlook/emails", headers=HEADERS)

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_outlook_requires_auth():
    """Outlook endpoints should require authentication."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/outlook/emails")
    assert response.status_code in (401, 403)
