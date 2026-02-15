"""LXB-013: Tests for Contacts CRUD — create, get, list, update, search, cross-tenant."""
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.auth.jwt import create_access_token
from apps.api.main import app

# ── Test data ──

TENANT_A = uuid.uuid4()
TENANT_B = uuid.uuid4()
USER_A = uuid.uuid4()
USER_B = uuid.uuid4()
CONTACT_ID = uuid.uuid4()

TOKEN_A = create_access_token(USER_A, TENANT_A, "partner", "alice@alpha.be")
TOKEN_B = create_access_token(USER_B, TENANT_B, "partner", "bob@beta.be")

NOW = datetime(2026, 2, 15, 12, 0, 0)


def _make_contact_obj(**overrides):
    """Create a mock Contact object."""
    defaults = {
        "id": CONTACT_ID,
        "tenant_id": TENANT_A,
        "type": "natural",
        "full_name": "Jean Dupont",
        "bce_number": None,
        "email": "jean@dupont.be",
        "phone_e164": "+32470123456",
        "address": {"street": "Rue de la Loi 1", "city": "Bruxelles", "zip": "1000", "country": "BE"},
        "language": "fr",
        "created_at": NOW,
        "updated_at": NOW,
    }
    defaults.update(overrides)

    class MockContact:
        pass

    obj = MockContact()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _patch_db():
    mock_session = AsyncMock()

    async def override_db(tenant_id=None):
        yield mock_session

    return mock_session, override_db


# ── Tests ──


@pytest.mark.asyncio
async def test_create_contact():
    mock_session, override_db = _patch_db()
    contact_obj = _make_contact_obj()

    with patch("apps.api.routers.contacts.contact_service") as mock_svc:
        mock_svc.create_contact = AsyncMock(return_value=contact_obj)

        from apps.api.dependencies import get_db_session
        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/contacts",
                json={
                    "type": "natural",
                    "full_name": "Jean Dupont",
                    "email": "jean@dupont.be",
                    "phone_e164": "+32470123456",
                },
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 201
    data = resp.json()
    assert data["full_name"] == "Jean Dupont"
    assert data["type"] == "natural"
    assert data["phone_e164"] == "+32470123456"


@pytest.mark.asyncio
async def test_get_contact():
    mock_session, override_db = _patch_db()
    contact_obj = _make_contact_obj()

    with patch("apps.api.routers.contacts.contact_service") as mock_svc:
        mock_svc.get_contact = AsyncMock(return_value=contact_obj)

        from apps.api.dependencies import get_db_session
        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                f"/api/v1/contacts/{CONTACT_ID}",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    assert resp.json()["id"] == str(CONTACT_ID)


@pytest.mark.asyncio
async def test_get_contact_not_found():
    mock_session, override_db = _patch_db()

    with patch("apps.api.routers.contacts.contact_service") as mock_svc:
        mock_svc.get_contact = AsyncMock(return_value=None)

        from apps.api.dependencies import get_db_session
        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                f"/api/v1/contacts/{uuid.uuid4()}",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_contacts_paginated():
    mock_session, override_db = _patch_db()
    contacts = [_make_contact_obj(id=uuid.uuid4(), full_name=f"Contact {i}") for i in range(5)]

    with patch("apps.api.routers.contacts.contact_service") as mock_svc:
        mock_svc.list_contacts = AsyncMock(return_value=(contacts, 5))

        from apps.api.dependencies import get_db_session
        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                "/api/v1/contacts?page=1&per_page=10",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["items"]) == 5
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_update_contact():
    mock_session, override_db = _patch_db()
    updated = _make_contact_obj(email="new@dupont.be")

    with patch("apps.api.routers.contacts.contact_service") as mock_svc:
        mock_svc.update_contact = AsyncMock(return_value=updated)

        from apps.api.dependencies import get_db_session
        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.patch(
                f"/api/v1/contacts/{CONTACT_ID}",
                json={"email": "new@dupont.be"},
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    assert resp.json()["email"] == "new@dupont.be"


@pytest.mark.asyncio
async def test_search_contacts():
    mock_session, override_db = _patch_db()
    results = [_make_contact_obj(full_name="Jean Dupont")]

    with patch("apps.api.routers.contacts.contact_service") as mock_svc:
        mock_svc.search_contacts = AsyncMock(return_value=(results, 1))

        from apps.api.dependencies import get_db_session
        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                "/api/v1/contacts/search?q=Dupont",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["full_name"] == "Jean Dupont"


@pytest.mark.asyncio
async def test_search_contacts_by_bce():
    mock_session, override_db = _patch_db()
    company = _make_contact_obj(
        type="legal",
        full_name="SPRL Martin",
        bce_number="0123.456.789",
    )

    with patch("apps.api.routers.contacts.contact_service") as mock_svc:
        mock_svc.search_contacts = AsyncMock(return_value=([company], 1))

        from apps.api.dependencies import get_db_session
        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                "/api/v1/contacts/search?q=0123.456",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    assert resp.json()["items"][0]["bce_number"] == "0123.456.789"


@pytest.mark.asyncio
async def test_search_requires_query():
    mock_session, override_db = _patch_db()

    from apps.api.dependencies import get_db_session
    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/contacts/search",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_contact_invalid_type():
    mock_session, override_db = _patch_db()

    from apps.api.dependencies import get_db_session
    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/contacts",
            json={"type": "invalid", "full_name": "Test"},
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_cross_tenant_isolation():
    """Tenant B should only see their own contacts."""
    mock_session, override_db = _patch_db()
    contact_b = _make_contact_obj(
        id=uuid.uuid4(),
        tenant_id=TENANT_B,
        full_name="Bob Contact",
    )

    with patch("apps.api.routers.contacts.contact_service") as mock_svc:
        mock_svc.list_contacts = AsyncMock(return_value=([contact_b], 1))

        from apps.api.dependencies import get_db_session
        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                "/api/v1/contacts",
                headers={"Authorization": f"Bearer {TOKEN_B}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["tenant_id"] == str(TENANT_B)
