"""Tests for OAuth router — authorize, callback, tokens, config."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.auth.jwt import create_access_token
from apps.api.main import app

# ── Test data ──

TENANT_A = uuid.uuid4()
USER_A = uuid.uuid4()
TOKEN_ID = uuid.uuid4()

TOKEN_A = create_access_token(USER_A, TENANT_A, "partner", "alice@alpha.be")

NOW = datetime(2026, 2, 15, 12, 0, 0)


def _make_user_obj():
    """Create a mock User object matching what the OAuth router expects."""

    class MockUser:
        pass

    obj = MockUser()
    obj.id = USER_A
    obj.email = "alice@alpha.be"
    obj.role = "partner"
    obj.tenant_id = TENANT_A
    return obj


def _make_oauth_token_obj(**overrides):
    defaults = {
        "id": TOKEN_ID,
        "tenant_id": TENANT_A,
        "user_id": USER_A,
        "provider": "google",
        "email_address": "alice@gmail.com",
        "display_name": "Alice",
        "avatar_url": None,
        "status": "active",
        "scope": "email drive",
        "expires_at": NOW,
        "last_sync_at": None,
        "sync_status": "idle",
        "created_at": NOW,
    }
    defaults.update(overrides)

    class MockOAuthToken:
        pass

    obj = MockOAuthToken()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _make_tenant_obj(**overrides):
    defaults = {
        "id": TENANT_A,
        "config": {
            "oauth": {
                "google": {
                    "enabled": True,
                    "client_id": "google-client-123",
                },
                "microsoft": {
                    "enabled": False,
                    "client_id": None,
                },
            }
        },
    }
    defaults.update(overrides)

    class MockTenant:
        pass

    obj = MockTenant()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _patch_db():
    mock_session = AsyncMock()

    async def override_db(tenant_id=None):
        yield mock_session

    return mock_session, override_db


def _make_scalars_result(items):
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = items
    mock_result.scalars.return_value = mock_scalars
    return mock_result


def _setup_overrides(override_db):
    """Set up dependency overrides for OAuth tests.

    The OAuth router type-hints user as User (with .id attribute),
    so we override get_current_user to return a mock User object.
    """
    from apps.api.dependencies import get_current_user, get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async def override_user(request=None):
        return _make_user_obj()

    app.dependency_overrides[get_current_user] = override_user


def _setup_overrides_with_tenant(override_db):
    """Set up overrides including get_current_tenant for callback endpoints."""
    from apps.api.dependencies import get_current_tenant, get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async def override_tenant(request=None):
        return TENANT_A

    app.dependency_overrides[get_current_tenant] = override_tenant


# ── Tests ──


@pytest.mark.asyncio
async def test_get_authorization_url():
    mock_session, override_db = _patch_db()

    with patch("apps.api.routers.oauth.get_oauth_engine") as mock_engine_fn:
        mock_engine = MagicMock()
        mock_engine.get_authorization_url = AsyncMock(
            return_value={
                "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?...",
                "state": "jwt-state-token",
                "code_verifier": "pkce-verifier",
            }
        )
        mock_engine_fn.return_value = mock_engine

        _setup_overrides(override_db)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/v1/oauth/google/authorize",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert "authorization_url" in data
    assert "state" in data
    assert "code_verifier" in data


@pytest.mark.asyncio
async def test_get_authorization_url_invalid_provider():
    mock_session, override_db = _patch_db()

    _setup_overrides(override_db)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/oauth/invalid_provider/authorize",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_oauth_callback_success():
    mock_session, override_db = _patch_db()

    mock_token_obj = _make_oauth_token_obj()

    with patch("apps.api.routers.oauth.get_oauth_engine") as mock_engine_fn:
        mock_engine = MagicMock()
        mock_engine.handle_callback = AsyncMock(return_value=mock_token_obj)
        mock_engine_fn.return_value = mock_engine

        _setup_overrides_with_tenant(override_db)

        # Callback has no JWT; use X-Tenant-ID header to pass middleware
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=False,
        ) as client:
            resp = await client.get(
                "/api/v1/oauth/google/callback"
                "?code=auth-code&state=state-token&code_verifier=pkce-verifier",
                headers={"X-Tenant-ID": str(TENANT_A)},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 307
    assert "status=success" in resp.headers["location"]


@pytest.mark.asyncio
async def test_oauth_callback_error():
    mock_session, override_db = _patch_db()

    with patch("apps.api.routers.oauth.get_oauth_engine") as mock_engine_fn:
        mock_engine = MagicMock()
        mock_engine.handle_callback = AsyncMock(
            side_effect=ValueError("Invalid state token")
        )
        mock_engine_fn.return_value = mock_engine

        _setup_overrides_with_tenant(override_db)

        # Callback has no JWT; use X-Tenant-ID header to pass middleware
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=False,
        ) as client:
            resp = await client.get(
                "/api/v1/oauth/google/callback"
                "?code=bad-code&state=bad-state&code_verifier=bad-verifier",
                headers={"X-Tenant-ID": str(TENANT_A)},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 307
    assert "status=error" in resp.headers["location"]


@pytest.mark.asyncio
async def test_list_oauth_tokens():
    mock_session, override_db = _patch_db()
    tokens = [_make_oauth_token_obj()]

    tokens_result = _make_scalars_result(tokens)
    mock_session.execute = AsyncMock(return_value=tokens_result)

    _setup_overrides(override_db)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/oauth/tokens",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["provider"] == "google"
    assert data[0]["email_address"] == "alice@gmail.com"


@pytest.mark.asyncio
async def test_list_oauth_tokens_empty():
    mock_session, override_db = _patch_db()

    tokens_result = _make_scalars_result([])
    mock_session.execute = AsyncMock(return_value=tokens_result)

    _setup_overrides(override_db)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/oauth/tokens",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_revoke_oauth_token():
    mock_session, override_db = _patch_db()
    token_obj = _make_oauth_token_obj()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = token_obj
    mock_session.execute = AsyncMock(return_value=mock_result)

    with patch("apps.api.routers.oauth.get_oauth_engine") as mock_engine_fn:
        mock_engine = MagicMock()
        mock_engine.revoke_token = AsyncMock()
        mock_engine_fn.return_value = mock_engine

        _setup_overrides(override_db)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.delete(
                f"/api/v1/oauth/tokens/{TOKEN_ID}",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_revoke_oauth_token_not_found():
    mock_session, override_db = _patch_db()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    _setup_overrides(override_db)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.delete(
            f"/api/v1/oauth/tokens/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_test_oauth_token_not_found():
    mock_session, override_db = _patch_db()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    _setup_overrides(override_db)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            f"/api/v1/oauth/tokens/{uuid.uuid4()}/test",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_oauth_config():
    mock_session, override_db = _patch_db()
    tenant = _make_tenant_obj()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = tenant
    mock_session.execute = AsyncMock(return_value=mock_result)

    _setup_overrides(override_db)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/oauth/config",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["google_enabled"] is True
    assert data["microsoft_enabled"] is False
    assert data["google_client_id"] == "google-client-123"


@pytest.mark.asyncio
async def test_get_oauth_config_tenant_not_found():
    mock_session, override_db = _patch_db()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    _setup_overrides(override_db)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/oauth/config",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_oauth_config():
    mock_session, override_db = _patch_db()
    tenant = _make_tenant_obj()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = tenant
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()

    _setup_overrides(override_db)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.put(
            "/api/v1/oauth/config",
            json={
                "google_client_id": "new-google-client-id",
                "google_enabled": True,
            },
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 200
    assert resp.json()["message"] == "OAuth configuration updated successfully"


@pytest.mark.asyncio
async def test_update_oauth_config_tenant_not_found():
    mock_session, override_db = _patch_db()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    _setup_overrides(override_db)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.put(
            "/api/v1/oauth/config",
            json={"google_enabled": True},
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 404
