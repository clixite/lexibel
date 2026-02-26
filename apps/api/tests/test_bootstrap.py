"""Tests for Bootstrap router — admin creation endpoint."""

import os
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.main import app


@pytest.mark.asyncio
async def test_bootstrap_disabled_by_default():
    """Bootstrap endpoint should return 403 when BOOTSTRAP_ENABLED is not set."""
    with patch.dict(os.environ, {"BOOTSTRAP_ENABLED": "false"}, clear=False):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/api/v1/bootstrap/admin")
    assert response.status_code == 403
    assert "disabled" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_bootstrap_enabled_creates_admin():
    """Bootstrap endpoint should create admin when enabled."""
    with (
        patch.dict(os.environ, {"BOOTSTRAP_ENABLED": "true"}, clear=False),
        patch(
            "apps.api.routers.bootstrap.ensure_admin_user",
            new_callable=AsyncMock,
        ) as mock_ensure,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/api/v1/bootstrap/admin")
    assert response.status_code == 201
    mock_ensure.assert_awaited_once()
    data = response.json()
    assert "email" in data


@pytest.mark.asyncio
async def test_bootstrap_handles_failure():
    """Bootstrap endpoint should return 500 on failure."""
    with (
        patch.dict(os.environ, {"BOOTSTRAP_ENABLED": "true"}, clear=False),
        patch(
            "apps.api.routers.bootstrap.ensure_admin_user",
            new_callable=AsyncMock,
            side_effect=Exception("DB connection failed"),
        ),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/api/v1/bootstrap/admin")
    assert response.status_code == 500
