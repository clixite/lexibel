"""Tests for Emails router — GET list, GET stats, POST sync, GET detail."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.auth.jwt import create_access_token
from apps.api.main import app

# -- Test data --

TENANT_A = uuid.uuid4()
TENANT_B = uuid.uuid4()
USER_A = uuid.uuid4()
USER_B = uuid.uuid4()
EMAIL_ID = uuid.uuid4()

TOKEN_A = create_access_token(USER_A, TENANT_A, "partner", "alice@alpha.be")
TOKEN_B = create_access_token(USER_B, TENANT_B, "partner", "bob@beta.be")

NOW = datetime(2026, 2, 15, 12, 0, 0, tzinfo=timezone.utc)


def _make_email_obj(**overrides):
    """Create a mock InboxItem object that matches the real model."""
    defaults = {
        "id": EMAIL_ID,
        "tenant_id": TENANT_A,
        "source": "OUTLOOK",
        "status": "DRAFT",
        "raw_payload": {
            "subject": "Re: Dossier Dupont",
            "from_email": "jean@dupont.be",
            "from_name": "Jean Dupont",
            "body": "Bonjour, merci pour votre email.",
            "folder": "inbox",
        },
        "suggested_case_id": None,
        "confidence": None,
        "validated_by": None,
        "validated_at": None,
        "created_at": NOW,
    }
    defaults.update(overrides)

    class MockEmail:
        pass

    obj = MockEmail()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _patch_db():
    mock_session = AsyncMock()

    async def override_db(tenant_id=None):
        yield mock_session

    return mock_session, override_db


# -- Tests: GET /emails --


@pytest.mark.asyncio
async def test_list_emails():
    """GET /api/v1/emails returns emails list."""
    mock_session, override_db = _patch_db()
    email = _make_email_obj()

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [email]

    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock

    mock_session.execute = AsyncMock(return_value=result_mock)

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/emails",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["emails"]) == 1
    assert data["emails"][0]["subject"] == "Re: Dossier Dupont"
    assert data["emails"][0]["from_email"] == "jean@dupont.be"


@pytest.mark.asyncio
async def test_list_emails_empty():
    """GET /api/v1/emails returns empty list when no emails."""
    mock_session, override_db = _patch_db()

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = []

    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock

    mock_session.execute = AsyncMock(return_value=result_mock)

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/emails",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["emails"] == []


@pytest.mark.asyncio
async def test_list_emails_unauthenticated():
    """GET /api/v1/emails without token returns 401."""
    mock_session, override_db = _patch_db()

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/v1/emails")

    app.dependency_overrides = {}

    assert resp.status_code == 401


# -- Tests: GET /emails/stats --


@pytest.mark.asyncio
async def test_get_email_stats():
    """GET /api/v1/emails/stats returns email statistics."""
    mock_session, override_db = _patch_db()

    # 3 sequential session.execute: total, unread, validated
    mock_session.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar=MagicMock(return_value=100)),
            MagicMock(scalar=MagicMock(return_value=25)),
            MagicMock(scalar=MagicMock(return_value=60)),
        ]
    )

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/emails/stats",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 100
    assert data["unread"] == 25
    assert data["validated"] == 60
    assert data["refused"] == 15  # 100 - 25 - 60


@pytest.mark.asyncio
async def test_get_email_stats_all_zero():
    """GET /api/v1/emails/stats with no emails returns zeros."""
    mock_session, override_db = _patch_db()

    mock_session.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar=MagicMock(return_value=0)),
            MagicMock(scalar=MagicMock(return_value=0)),
            MagicMock(scalar=MagicMock(return_value=0)),
        ]
    )

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/emails/stats",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["unread"] == 0
    assert data["validated"] == 0
    assert data["refused"] == 0


# -- Tests: POST /emails/sync --


@pytest.mark.asyncio
async def test_sync_emails():
    """POST /api/v1/emails/sync triggers sync and returns results."""
    mock_session, override_db = _patch_db()

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/v1/emails/sync",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "synced" in data
    assert "details" in data


@pytest.mark.asyncio
async def test_sync_emails_no_providers():
    """POST /api/v1/emails/sync returns success with 0 when no providers."""
    mock_session, override_db = _patch_db()

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/v1/emails/sync",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["synced"] == 0


# -- Tests: GET /emails/{id} --


@pytest.mark.asyncio
async def test_get_email_detail():
    """GET /api/v1/emails/{id} returns email detail."""
    mock_session, override_db = _patch_db()
    email = _make_email_obj()

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = email

    mock_session.execute = AsyncMock(return_value=result_mock)

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            f"/api/v1/emails/{EMAIL_ID}",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(EMAIL_ID)
    assert data["subject"] == "Re: Dossier Dupont"
    assert data["body"] == "Bonjour, merci pour votre email."


@pytest.mark.asyncio
async def test_get_email_detail_not_found():
    """GET /api/v1/emails/{id} returns 404 for unknown email."""
    mock_session, override_db = _patch_db()

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None

    mock_session.execute = AsyncMock(return_value=result_mock)

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            f"/api/v1/emails/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 404


# -- Tests: cross-tenant isolation --


@pytest.mark.asyncio
async def test_cross_tenant_emails_isolated():
    """Tenant B cannot see Tenant A emails."""
    mock_session, override_db = _patch_db()

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = []

    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock

    mock_session.execute = AsyncMock(return_value=result_mock)

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/emails",
            headers={"Authorization": f"Bearer {TOKEN_B}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 200
    assert resp.json()["emails"] == []
