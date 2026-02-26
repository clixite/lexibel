"""Tests for Integration Health router — circuit breakers, BCE, KYC, events."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.auth.jwt import create_access_token
from apps.api.dependencies import get_current_user
from apps.api.main import app

TENANT_ID = uuid.uuid4()
USER_ID = uuid.uuid4()
TOKEN = create_access_token(USER_ID, TENANT_ID, "partner", "health@test.be")
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


def _override_user():
    async def dep(request=None):
        return {
            "user_id": USER_ID,
            "tenant_id": TENANT_ID,
            "role": "partner",
            "email": "health@test.be",
        }

    app.dependency_overrides[get_current_user] = dep


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health_endpoint():
    """GET /api/v1/integrations/health should return integration status."""
    _override_user()

    with (
        patch(
            "apps.api.routers.integration_health.get_all_breaker_statuses",
            return_value={"bce": "closed", "dpa": "closed"},
        ),
        patch(
            "apps.api.routers.integration_health.get_bce_status",
            return_value={"status": "healthy", "cached_entries": 10},
        ),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/integrations/health", headers=HEADERS)

    assert response.status_code == 200
    data = response.json()
    assert "circuit_breakers" in data or "status" in data


@pytest.mark.asyncio
async def test_bce_lookup():
    """GET /api/v1/integrations/bce/{number} should return company info."""
    _override_user()

    # lookup_bce returns an object with .to_dict() method
    mock_company_data = {
        "bce_number": "0123.456.789",
        "name": "Test SA",
        "legal_form": "SA",
        "status": "active",
        "address": "Rue de la Loi 1, 1000 Bruxelles",
    }

    from unittest.mock import MagicMock

    mock_bce_result = MagicMock()
    mock_bce_result.to_dict.return_value = mock_company_data

    with patch(
        "apps.api.routers.integration_health.lookup_bce",
        new_callable=AsyncMock,
        return_value=mock_bce_result,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/v1/integrations/bce/0123456789", headers=HEADERS
            )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test SA"


@pytest.mark.asyncio
async def test_kyc_check():
    """POST /api/v1/integrations/kyc should return risk assessment."""
    _override_user()

    # perform_kyc_check returns an object with .to_dict() method
    mock_result_data = {
        "risk_level": "low",
        "risk_score": 15,
        "checks": [],
        "recommendations": [],
    }

    from unittest.mock import MagicMock

    mock_kyc_result = MagicMock()
    mock_kyc_result.to_dict.return_value = mock_result_data

    with patch(
        "apps.api.routers.integration_health.perform_kyc_check",
        new_callable=AsyncMock,
        return_value=mock_kyc_result,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/integrations/kyc",
                headers=HEADERS,
                json={
                    "contact_id": str(uuid.uuid4()),
                    "contact_name": "Jean Dupont",
                    "contact_type": "natural",
                },
            )

    assert response.status_code == 200
    data = response.json()
    assert "risk_level" in data or "risk_score" in data


@pytest.mark.asyncio
async def test_events_info():
    """GET /api/v1/integrations/events should return stream info."""
    _override_user()

    with patch(
        "apps.api.routers.integration_health.get_event_bus",
    ) as mock_bus:
        mock_bus.return_value.get_stream_info = AsyncMock(
            return_value={"streams": [], "total_events": 0}
        )

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/integrations/events", headers=HEADERS)

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_requires_auth():
    """Endpoints should require authentication."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/integrations/health")
    assert response.status_code in (401, 403)
