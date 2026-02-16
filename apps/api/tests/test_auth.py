"""LXB-009: Tests for JWT authentication — login, refresh, /me, token validation."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt

from apps.api.auth.jwt import (
    ALGORITHM,
    SECRET_KEY,
    TokenError,
    create_access_token,
    create_refresh_token,
    verify_token,
)
from apps.api.auth.passwords import hash_password, verify_password
from apps.api.main import app

# ── Test data ──

TEST_USER_ID = uuid.uuid4()
TEST_TENANT_ID = uuid.uuid4()
TEST_EMAIL = "avocat@alpha.be"
TEST_PASSWORD = "Str0ng!P@ssw0rd"
TEST_ROLE = "partner"


def _make_mock_user(**overrides):
    """Create a mock User object for auth tests."""
    defaults = {
        "id": TEST_USER_ID,
        "tenant_id": TEST_TENANT_ID,
        "email": TEST_EMAIL,
        "full_name": "Test Avocat",
        "role": TEST_ROLE,
        "hashed_password": hash_password(TEST_PASSWORD),
        "mfa_enabled": False,
        "mfa_secret": None,
        "is_active": True,
    }
    defaults.update(overrides)

    class MockUser:
        pass

    obj = MockUser()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


_MOCK_USER = _make_mock_user()


@pytest.fixture(autouse=True)
def _mock_db_lookups():
    """Mock the DB lookup functions in auth router."""
    with (
        patch(
            "apps.api.auth.router._get_user_by_email",
            new_callable=AsyncMock,
            side_effect=lambda email: _MOCK_USER if email == TEST_EMAIL else None,
        ),
        patch(
            "apps.api.auth.router._get_user_by_id",
            new_callable=AsyncMock,
            side_effect=lambda uid: _MOCK_USER if uid == TEST_USER_ID else None,
        ),
    ):
        yield


# ── Password hashing ──


class TestPasswords:
    def test_hash_and_verify(self):
        hashed = hash_password("mysecret")
        assert hashed != "mysecret"
        assert verify_password("mysecret", hashed)

    def test_wrong_password_fails(self):
        hashed = hash_password("correct")
        assert not verify_password("wrong", hashed)

    def test_different_hashes(self):
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2  # bcrypt uses random salt


# ── JWT token creation and verification ──


class TestJWT:
    def test_create_access_token_contains_claims(self):
        token = create_access_token(TEST_USER_ID, TEST_TENANT_ID, TEST_ROLE, TEST_EMAIL)
        claims = verify_token(token, expected_type="access")
        assert claims["sub"] == str(TEST_USER_ID)
        assert claims["tid"] == str(TEST_TENANT_ID)
        assert claims["role"] == TEST_ROLE
        assert claims["email"] == TEST_EMAIL
        assert claims["type"] == "access"

    def test_create_refresh_token_minimal_claims(self):
        token = create_refresh_token(TEST_USER_ID, TEST_TENANT_ID)
        claims = verify_token(token, expected_type="refresh")
        assert claims["sub"] == str(TEST_USER_ID)
        assert claims["tid"] == str(TEST_TENANT_ID)
        assert claims["type"] == "refresh"
        assert "role" not in claims

    def test_access_token_rejected_as_refresh(self):
        token = create_access_token(TEST_USER_ID, TEST_TENANT_ID, TEST_ROLE, TEST_EMAIL)
        with pytest.raises(TokenError, match="Wrong token type"):
            verify_token(token, expected_type="refresh")

    def test_refresh_token_rejected_as_access(self):
        token = create_refresh_token(TEST_USER_ID, TEST_TENANT_ID)
        with pytest.raises(TokenError, match="Wrong token type"):
            verify_token(token, expected_type="access")

    def test_expired_token_rejected(self):
        payload = {
            "sub": str(TEST_USER_ID),
            "tid": str(TEST_TENANT_ID),
            "role": TEST_ROLE,
            "email": TEST_EMAIL,
            "type": "access",
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        with pytest.raises(TokenError, match="Invalid token"):
            verify_token(token)

    def test_invalid_signature_rejected(self):
        token = create_access_token(TEST_USER_ID, TEST_TENANT_ID, TEST_ROLE, TEST_EMAIL)
        # Tamper with the token
        tampered = token[:-4] + "XXXX"
        with pytest.raises(TokenError, match="Invalid token"):
            verify_token(tampered)

    def test_garbage_token_rejected(self):
        with pytest.raises(TokenError):
            verify_token("not.a.jwt")


# ── Auth endpoints ──


@pytest.mark.asyncio
async def test_login_success():
    """POST /auth/login with valid credentials returns JWT pair."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

    # Verify the access token is valid
    claims = verify_token(data["access_token"])
    assert claims["sub"] == str(TEST_USER_ID)
    assert claims["tid"] == str(TEST_TENANT_ID)
    assert claims["role"] == TEST_ROLE


@pytest.mark.asyncio
async def test_login_wrong_password():
    """POST /auth/login with wrong password returns 401."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": TEST_EMAIL, "password": "wrongpassword"},
        )
    assert resp.status_code == 401
    assert "Invalid email or password" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_login_unknown_email():
    """POST /auth/login with unknown email returns 401."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "unknown@nowhere.be", "password": "anything"},
        )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_success():
    """POST /auth/refresh with valid refresh token returns new access token."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Login first
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        )
        refresh_token = login_resp.json()["refresh_token"]

        # Refresh
        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_refresh_with_access_token_fails():
    """POST /auth/refresh with an access token (wrong type) returns 401."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        )
        access_token = login_resp.json()["access_token"]

        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": access_token},
        )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_with_valid_jwt():
    """GET /auth/me with valid Bearer token returns user profile."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        )
        access_token = login_resp.json()["access_token"]

        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == str(TEST_USER_ID)
    assert data["tenant_id"] == str(TEST_TENANT_ID)
    assert data["email"] == TEST_EMAIL
    assert data["role"] == TEST_ROLE


@pytest.mark.asyncio
async def test_me_without_token():
    """GET /auth/me without Authorization header returns 401."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_with_jwt():
    """A protected route should accept JWT and extract tenant_id."""
    access_token = create_access_token(
        TEST_USER_ID, TEST_TENANT_ID, TEST_ROLE, TEST_EMAIL
    )
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_expired_jwt_rejected():
    """An expired JWT should be rejected with 401."""
    payload = {
        "sub": str(TEST_USER_ID),
        "tid": str(TEST_TENANT_ID),
        "role": TEST_ROLE,
        "email": TEST_EMAIL,
        "type": "access",
        "iat": datetime.now(timezone.utc) - timedelta(hours=2),
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
    }
    expired_token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
    assert resp.status_code == 401
