"""Tests for Admin Settings router — GET, GET/{category}, PUT, POST/test, DELETE."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.auth.jwt import create_access_token
from apps.api.main import app

# ── Test data ──

TENANT_A = uuid.uuid4()
USER_A = uuid.uuid4()

TOKEN_ADMIN = create_access_token(USER_A, TENANT_A, "super_admin", "admin@alpha.be")
TOKEN_NON_ADMIN = create_access_token(USER_A, TENANT_A, "partner", "alice@alpha.be")


def _patch_db():
    mock_session = AsyncMock()

    async def override_db(tenant_id=None):
        yield mock_session

    return mock_session, override_db


# ── Tests ──


@pytest.mark.asyncio
async def test_get_all_settings():
    mock_session, override_db = _patch_db()

    with patch("apps.api.routers.admin_settings.settings_service") as mock_svc:
        mock_svc.get_all_settings = AsyncMock(
            return_value=[
                {"key": "ANTHROPIC_API_KEY", "value": "sk-***", "category": "ai"},
                {"key": "SMTP_HOST", "value": "smtp.test.be", "category": "email"},
            ]
        )

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/v1/admin/settings",
                headers={"Authorization": f"Bearer {TOKEN_ADMIN}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert "ai" in data["settings"]
    assert "email" in data["settings"]


@pytest.mark.asyncio
async def test_get_all_settings_forbidden_for_non_admin():
    mock_session, override_db = _patch_db()

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/admin/settings",
            headers={"Authorization": f"Bearer {TOKEN_NON_ADMIN}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_settings_by_category():
    mock_session, override_db = _patch_db()

    with patch("apps.api.routers.admin_settings.settings_service") as mock_svc:
        mock_svc.get_all_settings = AsyncMock(
            return_value=[
                {"key": "ANTHROPIC_API_KEY", "value": "sk-***", "category": "ai"},
                {"key": "OPENAI_API_KEY", "value": "sk-***", "category": "ai"},
                {"key": "SMTP_HOST", "value": "smtp.test.be", "category": "email"},
            ]
        )

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/v1/admin/settings/ai",
                headers={"Authorization": f"Bearer {TOKEN_ADMIN}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["category"] == "ai"
    assert len(data["settings"]) == 2


@pytest.mark.asyncio
async def test_upsert_settings():
    mock_session, override_db = _patch_db()

    setting_mock = MagicMock()
    setting_mock.is_encrypted = True

    with patch("apps.api.routers.admin_settings.settings_service") as mock_svc:
        mock_svc.upsert_setting = AsyncMock(return_value=setting_mock)

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.put(
                "/api/v1/admin/settings",
                json={
                    "settings": [
                        {
                            "key": "ANTHROPIC_API_KEY",
                            "value": "sk-ant-new-key",
                            "category": "ai",
                            "label": "Anthropic Key",
                        }
                    ]
                },
                headers={"Authorization": f"Bearer {TOKEN_ADMIN}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["saved"] == 1
    assert data["results"][0]["key"] == "ANTHROPIC_API_KEY"
    assert data["results"][0]["status"] == "saved"
    assert data["results"][0]["is_encrypted"] is True


@pytest.mark.asyncio
async def test_upsert_settings_forbidden_for_non_admin():
    mock_session, override_db = _patch_db()

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.put(
            "/api/v1/admin/settings",
            json={
                "settings": [
                    {
                        "key": "ANTHROPIC_API_KEY",
                        "value": "sk-ant-new-key",
                        "category": "ai",
                    }
                ]
            },
            headers={"Authorization": f"Bearer {TOKEN_NON_ADMIN}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_test_connection():
    mock_session, override_db = _patch_db()

    with patch("apps.api.routers.admin_settings.settings_service") as mock_svc:
        mock_svc.get_settings_by_category = AsyncMock(
            return_value={"ANTHROPIC_API_KEY": "sk-ant-real-key"}
        )
        mock_svc.test_connection = AsyncMock(
            return_value={"status": "ok", "message": "Connection successful"}
        )

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/admin/settings/test/ai",
                headers={"Authorization": f"Bearer {TOKEN_ADMIN}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_delete_setting():
    mock_session, override_db = _patch_db()

    with patch("apps.api.routers.admin_settings.settings_service") as mock_svc:
        mock_svc.delete_setting = AsyncMock(return_value=True)

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.delete(
                "/api/v1/admin/settings/ANTHROPIC_API_KEY",
                headers={"Authorization": f"Bearer {TOKEN_ADMIN}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "deleted"
    assert data["key"] == "ANTHROPIC_API_KEY"


@pytest.mark.asyncio
async def test_delete_setting_not_found():
    mock_session, override_db = _patch_db()

    with patch("apps.api.routers.admin_settings.settings_service") as mock_svc:
        mock_svc.delete_setting = AsyncMock(return_value=False)

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.delete(
                "/api/v1/admin/settings/NONEXISTENT_KEY",
                headers={"Authorization": f"Bearer {TOKEN_ADMIN}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_setting_forbidden_for_non_admin():
    mock_session, override_db = _patch_db()

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.delete(
            "/api/v1/admin/settings/SOME_KEY",
            headers={"Authorization": f"Bearer {TOKEN_NON_ADMIN}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 403
