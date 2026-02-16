"""Tests for admin endpoints: health, tenants, users, stats, role-based access."""
import uuid

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.routers.admin import _tenants_store, _users_store


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
        "X-User-Role": "lawyer",
        "X-User-Email": "lawyer@lexibel.be",
    }


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def clean_stores():
    _tenants_store.clear()
    _users_store.clear()
    yield
    _tenants_store.clear()
    _users_store.clear()


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
        expected_services = {"api", "database", "redis", "qdrant", "minio", "vllm", "neo4j"}
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
            json={"name": "Cabinet Dupont", "domain": "dupont.be", "plan": "professional"},
            headers=_admin_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Cabinet Dupont"
        assert data["plan"] == "professional"
        assert data["status"] == "active"

    def test_create_and_list_tenants(self, client):
        client.post(
            "/api/v1/admin/tenants",
            json={"name": "Tenant A"},
            headers=_admin_headers(),
        )
        client.post(
            "/api/v1/admin/tenants",
            json={"name": "Tenant B"},
            headers=_admin_headers(),
        )
        resp = client.get("/api/v1/admin/tenants", headers=_admin_headers())
        assert len(resp.json()["tenants"]) == 2

    def test_create_tenant_missing_name(self, client):
        resp = client.post(
            "/api/v1/admin/tenants",
            json={"domain": "test.be"},
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
            json={"email": "newuser@cabinet.be", "role": "lawyer"},
            headers=_admin_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "newuser@cabinet.be" in data["message"]
        assert data["user"]["role"] == "lawyer"
        assert data["user"]["status"] == "invited"

    def test_invite_user_appears_in_list(self, client):
        client.post(
            "/api/v1/admin/users/invite",
            json={"email": "test@cabinet.be", "role": "paralegal"},
            headers=_admin_headers(),
        )
        resp = client.get("/api/v1/admin/users", headers=_admin_headers())
        users = resp.json()["users"]
        assert len(users) == 1
        assert users[0]["email"] == "test@cabinet.be"

    def test_invite_missing_email(self, client):
        resp = client.post(
            "/api/v1/admin/users/invite",
            json={"role": "lawyer"},
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
