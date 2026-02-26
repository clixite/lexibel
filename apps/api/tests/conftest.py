"""Shared test fixtures for LexiBel API tests.

Provides reusable fixtures for authentication, DB session mocking,
and common test data. All tests use httpx.AsyncClient with ASGITransport.
"""

import uuid
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.auth.jwt import create_access_token
from apps.api.dependencies import get_current_tenant, get_current_user, get_db_session
from apps.api.main import app

# ── Shared test identifiers ──

TENANT_A = uuid.UUID("aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa")
TENANT_B = uuid.UUID("bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb")
USER_A = uuid.UUID("11111111-1111-4111-a111-111111111111")
USER_B = uuid.UUID("22222222-2222-4222-a222-222222222222")
ADMIN_USER = uuid.UUID("33333333-3333-4333-a333-333333333333")


# ── Token helpers ──


def make_token(
    user_id=USER_A, tenant_id=TENANT_A, role="partner", email="test@alpha.be"
):
    """Create a JWT access token for testing."""
    return create_access_token(user_id, tenant_id, role, email)


def make_admin_token(tenant_id=TENANT_A):
    """Create an admin JWT access token for testing."""
    return create_access_token(ADMIN_USER, tenant_id, "super_admin", "admin@alpha.be")


TOKEN_A = make_token()
TOKEN_B = make_token(USER_B, TENANT_B, email="test@beta.be")
ADMIN_TOKEN = make_admin_token()


# ── Mock object factories ──


def make_mock_obj(**attrs):
    """Create a generic mock object with given attributes."""

    class MockObj:
        pass

    obj = MockObj()
    for k, v in attrs.items():
        setattr(obj, k, v)
    return obj


# ── DB session mock ──


def mock_db_session():
    """Create a mock async DB session and its dependency override.

    Returns (mock_session, override_fn) tuple.
    Usage:
        session, override = mock_db_session()
        app.dependency_overrides[get_db_session] = override
    """
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)

    async def override(tenant_id=None):
        yield session

    return session, override


# ── Fixtures ──


@pytest.fixture
def client_a():
    """Authenticated AsyncClient for Tenant A."""
    return {
        "headers": {"Authorization": f"Bearer {TOKEN_A}"},
    }


@pytest.fixture
def client_b():
    """Authenticated AsyncClient for Tenant B."""
    return {
        "headers": {"Authorization": f"Bearer {TOKEN_B}"},
    }


@pytest.fixture
def admin_headers():
    """Admin auth headers."""
    return {"Authorization": f"Bearer {ADMIN_TOKEN}"}


@pytest.fixture
def db_session():
    """Mock DB session with dependency override. Auto-cleans overrides."""
    session, override = mock_db_session()
    app.dependency_overrides[get_db_session] = override
    yield session
    app.dependency_overrides.pop(get_db_session, None)


@pytest.fixture
def override_current_user():
    """Override get_current_user dependency. Auto-cleans."""

    def _override(
        user_id=USER_A, tenant_id=TENANT_A, role="partner", email="test@alpha.be"
    ):
        async def dep():
            return {
                "user_id": user_id,
                "tenant_id": tenant_id,
                "role": role,
                "email": email,
            }

        app.dependency_overrides[get_current_user] = dep
        return dep

    yield _override
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def override_current_tenant():
    """Override get_current_tenant dependency. Auto-cleans."""

    def _override(tenant_id=TENANT_A):
        async def dep():
            return tenant_id

        app.dependency_overrides[get_current_tenant] = dep
        return dep

    yield _override
    app.dependency_overrides.pop(get_current_tenant, None)


@pytest.fixture(autouse=True)
def _cleanup_overrides():
    """Ensure dependency overrides are cleaned after every test."""
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def async_client():
    """Reusable async HTTP client for the FastAPI app."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
