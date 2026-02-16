"""Tests for admin endpoints: health, tenants, users, stats, role-based access."""

import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app

TENANT_ID = str(uuid.uuid4())
USER_ID = str(uuid.uuid4())


def _admin_headers() -> dict:
    return {
        "X-Tenant-ID": TENANT_ID,
        "X-User-ID": USER_ID,
        "X-User-Role": "super_admin",
        "X-User-Email": "admin@lexibel.be",
    }


def _non_admin_headers() -> dict:
    return {
        "X-Tenant-ID": TENANT_ID,
        "X-User-ID": USER_ID,
        "X-User-Role": "junior",
        "X-User-Email": "lawyer@lexibel.be",
    }


# ── DB mock infrastructure ──

_mock_tenants: list[MagicMock] = []
_mock_users: list[MagicMock] = []


def _make_mock_tenant(name="Test Tenant", slug="test-tenant", plan="solo"):
    t = MagicMock()
    t.id = uuid.uuid4()
    t.name = name
    t.slug = slug
    t.plan = plan
    t.locale = "fr-BE"
    t.status = "active"
    t.config = {}
    t.created_at = datetime.now(timezone.utc)
    t.updated_at = datetime.now(timezone.utc)
    return t


def _make_mock_user(email="test@cabinet.be", role="junior", full_name="Test User"):
    u = MagicMock()
    u.id = uuid.uuid4()
    u.tenant_id = uuid.UUID(TENANT_ID)
    u.email = email
    u.full_name = full_name
    u.role = role
    u.is_active = True
    u.hashed_password = "hashed"
    u.auth_provider = "local"
    u.mfa_enabled = False
    u.created_at = datetime.now(timezone.utc)
    u.updated_at = datetime.now(timezone.utc)
    return u


def _make_mock_session():
    """Create a mock session that supports async context manager."""
    session = AsyncMock()

    @asynccontextmanager
    async def _begin():
        yield

    session.begin = _begin

    async def _execute(query, *args, **kwargs):
        result = MagicMock()
        query_str = str(query)

        # Handle COUNT queries
        if "count" in query_str.lower():
            result.scalar_one.return_value = len(_mock_tenants)
            return result

        # Handle SELECT queries
        if "tenants" in query_str.lower():
            scalars_mock = MagicMock()
            scalars_mock.all.return_value = list(_mock_tenants)
            result.scalars.return_value = scalars_mock
            result.scalar_one_or_none.return_value = None
            return result

        if "users" in query_str.lower():
            scalars_mock = MagicMock()
            scalars_mock.all.return_value = [
                u for u in _mock_users if str(u.tenant_id) == TENANT_ID
            ]
            result.scalars.return_value = scalars_mock
            result.scalar_one_or_none.return_value = None
            return result

        # Default
        result.scalar_one.return_value = 0
        result.scalar_one_or_none.return_value = None
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result.scalars.return_value = scalars_mock
        return result

    session.execute = _execute

    async def _flush():
        pass

    async def _refresh(obj):
        if not hasattr(obj, "created_at") or obj.created_at is None:
            obj.created_at = datetime.now(timezone.utc)
        if not hasattr(obj, "id") or obj.id is None:
            obj.id = uuid.uuid4()

    def _add(obj):
        if hasattr(obj, "slug"):
            _mock_tenants.append(obj)
        elif hasattr(obj, "email"):
            _mock_users.append(obj)

    session.flush = _flush
    session.refresh = _refresh
    session.add = _add
    return session


class _MockSessionFactory:
    """Mock async_session_factory that returns async context manager sessions."""

    def __call__(self):
        session = _make_mock_session()
        return self._wrap(session)

    @asynccontextmanager
    async def _wrap(self, session):
        yield session


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clean_and_mock():
    _mock_tenants.clear()
    _mock_users.clear()
    with patch(
        "apps.api.routers.admin.async_session_factory",
        new=_MockSessionFactory(),
    ):
        yield
    _mock_tenants.clear()
    _mock_users.clear()


# ── Health ──


class TestAdminHealth:
    def test_health_as_super_admin(self, client):
        resp = client.get("/api/v1/admin/health", headers=_admin_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("healthy", "degraded")
        assert "services" in data
        assert "api" in data["services"]

    def test_health_forbidden_for_non_admin(self, client):
        resp = client.get("/api/v1/admin/health", headers=_non_admin_headers())
        assert resp.status_code == 403

    def test_health_services_structure(self, client):
        resp = client.get("/api/v1/admin/health", headers=_admin_headers())
        data = resp.json()
        expected_services = {
            "api",
            "database",
            "redis",
            "qdrant",
            "minio",
            "vllm",
            "neo4j",
        }
        assert expected_services == set(data["services"].keys())


# ── Tenants ──


class TestAdminTenants:
    def test_list_tenants_empty(self, client):
        resp = client.get("/api/v1/admin/tenants", headers=_admin_headers())
        assert resp.status_code == 200
        assert resp.json()["tenants"] == []

    def test_create_tenant(self, client):
        resp = client.post(
            "/api/v1/admin/tenants",
            json={
                "name": "Cabinet Dupont",
                "slug": "cabinet-dupont",
                "plan": "solo",
            },
            headers=_admin_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Cabinet Dupont"
        assert data["status"] == "active"

    def test_create_and_list_tenants(self, client):
        client.post(
            "/api/v1/admin/tenants",
            json={"name": "Tenant A", "slug": "tenant-a"},
            headers=_admin_headers(),
        )
        client.post(
            "/api/v1/admin/tenants",
            json={"name": "Tenant B", "slug": "tenant-b"},
            headers=_admin_headers(),
        )
        resp = client.get("/api/v1/admin/tenants", headers=_admin_headers())
        assert len(resp.json()["tenants"]) == 2

    def test_create_tenant_missing_name(self, client):
        resp = client.post(
            "/api/v1/admin/tenants",
            json={"slug": "test"},
            headers=_admin_headers(),
        )
        assert resp.status_code == 400

    def test_tenants_forbidden_for_non_admin(self, client):
        resp = client.get("/api/v1/admin/tenants", headers=_non_admin_headers())
        assert resp.status_code == 403


# ── Users ──


class TestAdminUsers:
    def test_list_users_empty(self, client):
        resp = client.get("/api/v1/admin/users", headers=_admin_headers())
        assert resp.status_code == 200
        assert resp.json()["users"] == []

    def test_invite_user(self, client):
        resp = client.post(
            "/api/v1/admin/users/invite",
            json={"email": "newuser@cabinet.be", "role": "junior"},
            headers=_admin_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "newuser@cabinet.be" in data["message"]
        assert data["user"]["role"] == "junior"

    def test_invite_missing_email(self, client):
        resp = client.post(
            "/api/v1/admin/users/invite",
            json={"role": "junior"},
            headers=_admin_headers(),
        )
        assert resp.status_code == 400

    def test_invite_invalid_role(self, client):
        resp = client.post(
            "/api/v1/admin/users/invite",
            json={"email": "test@test.be", "role": "ceo"},
            headers=_admin_headers(),
        )
        assert resp.status_code == 400


# ── Stats ──


class TestAdminStats:
    def test_global_stats(self, client):
        resp = client.get("/api/v1/admin/stats", headers=_admin_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert "tenants" in data
        assert "users" in data
        assert "cases" in data

    def test_stats_forbidden_for_non_admin(self, client):
        resp = client.get("/api/v1/admin/stats", headers=_non_admin_headers())
        assert resp.status_code == 403
