"""MVP Integration smoke test — full CRUD flow with mocked DB.

Tests the complete flow: login -> create case -> create contact ->
link contact to case -> create time entry -> verify all responses.
"""

import uuid
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.auth.jwt import create_access_token
from apps.api.auth.passwords import hash_password
from apps.api.main import app

# ── Test data ──

TENANT_ID = uuid.uuid4()
USER_ID = uuid.uuid4()
EMAIL = "integration@lexibel.be"
PASSWORD = "IntTest2026!"
ROLE = "partner"
NOW = datetime(2026, 2, 16, 10, 0, 0)


def _make_mock_user():
    obj = MagicMock()
    obj.id = USER_ID
    obj.tenant_id = TENANT_ID
    obj.email = EMAIL
    obj.full_name = "Integration Tester"
    obj.role = ROLE
    obj.hashed_password = hash_password(PASSWORD)
    obj.mfa_enabled = False
    obj.mfa_secret = None
    obj.is_active = True
    return obj


_MOCK_USER = _make_mock_user()
TOKEN = create_access_token(USER_ID, TENANT_ID, ROLE, EMAIL)

# ── Mock DB session helper ──


def _patch_db():
    """Patch get_db_session to return a no-op async session."""
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    async def override_db(tenant_id=None):
        yield mock_session

    return mock_session, override_db


# ── Mock objects ──

CASE_ID = uuid.uuid4()
CONTACT_ID = uuid.uuid4()
TIME_ENTRY_ID = uuid.uuid4()


def _make_case():
    obj = MagicMock()
    obj.id = CASE_ID
    obj.tenant_id = TENANT_ID
    obj.reference = "2026/INT-001"
    obj.court_reference = None
    obj.title = "Integration Test Case"
    obj.matter_type = "civil"
    obj.status = "open"
    obj.jurisdiction = "Tribunal de Bruxelles"
    obj.responsible_user_id = USER_ID
    obj.opened_at = date(2026, 2, 16)
    obj.closed_at = None
    obj.metadata_ = {}
    obj.metadata = {}
    obj.created_at = NOW
    obj.updated_at = NOW
    return obj


def _make_contact():
    obj = MagicMock()
    obj.id = CONTACT_ID
    obj.tenant_id = TENANT_ID
    obj.type = "natural"
    obj.full_name = "Jean Dupont"
    obj.bce_number = None
    obj.email = "jean@dupont.be"
    obj.phone_e164 = "+32470123456"
    obj.address = {"street": "Rue de la Loi 1", "city": "Bruxelles", "zip": "1000"}
    obj.language = "fr"
    obj.metadata_ = {}
    obj.created_at = NOW
    obj.updated_at = NOW
    return obj


def _make_time_entry():
    obj = MagicMock()
    obj.id = TIME_ENTRY_ID
    obj.tenant_id = TENANT_ID
    obj.case_id = CASE_ID
    obj.user_id = USER_ID
    obj.description = "Initial consultation with client"
    obj.duration_minutes = 60
    obj.billable = True
    obj.date = date(2026, 2, 16)
    obj.rounding_rule = "6min"
    obj.source = "MANUAL"
    obj.status = "draft"
    obj.hourly_rate_cents = 15000
    obj.approved_by = None
    obj.created_at = NOW
    obj.updated_at = NOW
    return obj


# ── Tests ──


@pytest.fixture(autouse=True)
def _mock_auth():
    """Mock auth DB lookups for the integration test."""
    with (
        patch(
            "apps.api.auth.router._get_user_by_email",
            new_callable=AsyncMock,
            side_effect=lambda email: _MOCK_USER if email == EMAIL else None,
        ),
        patch(
            "apps.api.auth.router._get_user_by_id",
            new_callable=AsyncMock,
            side_effect=lambda uid: _MOCK_USER if uid == USER_ID else None,
        ),
    ):
        yield


@pytest.mark.asyncio
async def test_login_flow():
    """Step 1: Login with valid credentials."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": EMAIL, "password": PASSWORD},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["access_token"] is not None
    assert data["refresh_token"] is not None
    assert data["mfa_required"] is False


@pytest.mark.asyncio
async def test_create_case_flow():
    """Step 2: Create a case with JWT auth."""
    mock_session, override_db = _patch_db()
    case_obj = _make_case()

    with patch("apps.api.routers.cases.case_service") as mock_svc:
        mock_svc.create_case = AsyncMock(return_value=case_obj)

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/cases",
                json={
                    "reference": "2026/INT-001",
                    "title": "Integration Test Case",
                    "matter_type": "civil",
                    "responsible_user_id": str(USER_ID),
                },
                headers={"Authorization": f"Bearer {TOKEN}"},
            )
        app.dependency_overrides = {}

    assert resp.status_code == 201
    data = resp.json()
    assert data["reference"] == "2026/INT-001"
    assert data["title"] == "Integration Test Case"


@pytest.mark.asyncio
async def test_create_contact_flow():
    """Step 3: Create a contact."""
    mock_session, override_db = _patch_db()
    contact_obj = _make_contact()

    with patch("apps.api.routers.contacts.contact_service") as mock_svc:
        mock_svc.create_contact = AsyncMock(return_value=contact_obj)

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/contacts",
                json={
                    "type": "natural",
                    "full_name": "Jean Dupont",
                    "email": "jean@dupont.be",
                    "phone_e164": "+32470123456",
                    "language": "fr",
                },
                headers={"Authorization": f"Bearer {TOKEN}"},
            )
        app.dependency_overrides = {}

    assert resp.status_code == 201
    data = resp.json()
    assert data["full_name"] == "Jean Dupont"
    assert data["type"] == "natural"


@pytest.mark.asyncio
async def test_create_time_entry_flow():
    """Step 4: Create a time entry for the case."""
    mock_session, override_db = _patch_db()
    entry_obj = _make_time_entry()

    with patch("apps.api.routers.time_entries.time_service") as mock_svc:
        mock_svc.create_time_entry = AsyncMock(return_value=entry_obj)

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/time-entries",
                json={
                    "case_id": str(CASE_ID),
                    "description": "Initial consultation with client",
                    "duration_minutes": 60,
                    "billable": True,
                    "date": "2026-02-16",
                    "rounding_rule": "6min",
                    "source": "MANUAL",
                    "hourly_rate_cents": 15000,
                },
                headers={"Authorization": f"Bearer {TOKEN}"},
            )
        app.dependency_overrides = {}

    assert resp.status_code == 201
    data = resp.json()
    assert data["description"] == "Initial consultation with client"
    assert data["duration_minutes"] == 60
    assert data["case_id"] == str(CASE_ID)


@pytest.mark.asyncio
async def test_list_cases_flow():
    """Step 5: List cases and verify our case appears."""
    mock_session, override_db = _patch_db()
    case_obj = _make_case()

    with patch("apps.api.routers.cases.case_service") as mock_svc:
        mock_svc.list_cases = AsyncMock(return_value=([case_obj], 1))

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/v1/cases",
                headers={"Authorization": f"Bearer {TOKEN}"},
            )
        app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["reference"] == "2026/INT-001"


@pytest.mark.asyncio
async def test_full_mvp_flow():
    """End-to-end MVP flow: login -> create case -> create contact -> time entry."""
    mock_session, override_db = _patch_db()
    case_obj = _make_case()
    contact_obj = _make_contact()
    entry_obj = _make_time_entry()

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1. Login
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": EMAIL, "password": PASSWORD},
        )
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Create case
        with patch("apps.api.routers.cases.case_service") as mock_case_svc:
            mock_case_svc.create_case = AsyncMock(return_value=case_obj)
            case_resp = await client.post(
                "/api/v1/cases",
                json={
                    "reference": "2026/INT-001",
                    "title": "Integration Test Case",
                    "matter_type": "civil",
                    "responsible_user_id": str(USER_ID),
                },
                headers=headers,
            )
        assert case_resp.status_code == 201

        # 3. Create contact
        with patch("apps.api.routers.contacts.contact_service") as mock_contact_svc:
            mock_contact_svc.create_contact = AsyncMock(return_value=contact_obj)
            contact_resp = await client.post(
                "/api/v1/contacts",
                json={
                    "type": "natural",
                    "full_name": "Jean Dupont",
                    "email": "jean@dupont.be",
                    "language": "fr",
                },
                headers=headers,
            )
        assert contact_resp.status_code == 201

        # 4. Create time entry
        with patch("apps.api.routers.time_entries.time_service") as mock_time_svc:
            mock_time_svc.create_time_entry = AsyncMock(return_value=entry_obj)
            time_resp = await client.post(
                "/api/v1/time-entries",
                json={
                    "case_id": str(CASE_ID),
                    "description": "Initial consultation",
                    "duration_minutes": 60,
                    "billable": True,
                    "date": "2026-02-16",
                },
                headers=headers,
            )
        assert time_resp.status_code == 201

        # 5. Get /me to confirm JWT works
        me_resp = await client.get("/api/v1/auth/me", headers=headers)
        assert me_resp.status_code == 200
        assert me_resp.json()["email"] == EMAIL

    app.dependency_overrides = {}
