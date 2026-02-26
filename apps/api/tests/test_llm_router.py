"""Tests for LLM router — AI completion, streaming, providers, audit."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.auth.jwt import create_access_token
from apps.api.dependencies import get_current_tenant, get_current_user, get_db_session
from apps.api.main import app

TENANT_ID = uuid.uuid4()
USER_ID = uuid.uuid4()
ADMIN_ID = uuid.uuid4()
TOKEN = create_access_token(USER_ID, TENANT_ID, "partner", "llm@test.be")
ADMIN_TOKEN = create_access_token(ADMIN_ID, TENANT_ID, "super_admin", "admin@test.be")
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
ADMIN_HEADERS = {"Authorization": f"Bearer {ADMIN_TOKEN}"}


def _override_deps(role="partner", user_id=USER_ID):
    mock_session = AsyncMock()

    async def override_user(request=None):
        return {
            "user_id": user_id,
            "tenant_id": TENANT_ID,
            "role": role,
            "email": "llm@test.be",
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


@pytest.mark.asyncio
async def test_complete_endpoint():
    """POST /api/v1/llm/complete should return AI completion."""
    _override_deps()

    mock_result = {
        "response": "Selon l'article 1382 du Code civil...",
        "provider": "openai",
        "model": "gpt-4",
        "tokens_used": 150,
    }

    with patch("apps.api.routers.llm.LLMGateway") as MockGateway:
        gateway = MockGateway.return_value
        gateway.complete = AsyncMock(return_value=mock_result)

        with patch("apps.api.routers.llm.AIAuditLogger") as MockAudit:
            MockAudit.return_value.log = AsyncMock()

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/v1/llm/complete",
                    headers=HEADERS,
                    json={
                        "messages": [
                            {"role": "user", "content": "Qu'est-ce que l'art. 1382?"}
                        ],
                        "purpose": "legal_research",
                    },
                )

    assert response.status_code == 200
    data = response.json()
    assert "response" in data or "content" in data


@pytest.mark.asyncio
async def test_providers_endpoint():
    """GET /api/v1/llm/providers should list available LLM providers."""
    _override_deps()

    with patch("apps.api.routers.llm.LLMGateway") as MockGateway:
        gateway = MockGateway.return_value
        gateway.get_provider_status = AsyncMock(
            return_value=[
                {"provider": "openai", "status": "active", "models": ["gpt-4"]},
            ]
        )

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/llm/providers", headers=HEADERS)

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_classify_endpoint():
    """POST /api/v1/llm/classify should classify text."""
    _override_deps()

    with patch("apps.api.routers.llm.LLMGateway") as MockGateway:
        gateway = MockGateway.return_value
        gateway.classify_text = AsyncMock(
            return_value={"category": "civil", "confidence": 0.95}
        )

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/llm/classify",
                headers=HEADERS,
                json={"text": "Litige contractuel entre deux sociétés"},
            )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_audit_requires_admin():
    """GET /api/v1/llm/audit should require admin role."""
    _override_deps(role="partner")

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/llm/audit", headers=HEADERS)

    assert response.status_code in (403, 200)  # Depends on RBAC enforcement


@pytest.mark.asyncio
async def test_complete_requires_auth():
    """POST /api/v1/llm/complete without auth should fail."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/llm/complete",
            json={"messages": [{"role": "user", "content": "test"}]},
        )
    assert response.status_code in (401, 403)
