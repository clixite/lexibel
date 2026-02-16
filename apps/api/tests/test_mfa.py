"""LXB-011: Tests for MFA TOTP — setup, verify, login challenge."""

import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pyotp
import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.auth.jwt import create_access_token, verify_token
from apps.api.auth.mfa import generate_provisioning_uri, generate_secret, verify_totp
from apps.api.auth.passwords import hash_password
from apps.api.main import app

# ── Test data ──

TEST_USER_ID = uuid.uuid4()
TEST_TENANT_ID = uuid.uuid4()
TEST_EMAIL = "mfa-user@alpha.be"
TEST_PASSWORD = "MfaStr0ng!Pass"
TEST_ROLE = "partner"

MFA_USER_ID = uuid.uuid4()
MFA_EMAIL = "mfa-enabled@alpha.be"
MFA_SECRET = generate_secret()

_HASHED_PASSWORD = hash_password(TEST_PASSWORD)


def _make_mock_user(
    user_id=TEST_USER_ID,
    email=TEST_EMAIL,
    mfa_enabled=False,
    mfa_secret=None,
):
    """Create a mock User object."""
    obj = MagicMock()
    obj.id = user_id
    obj.tenant_id = TEST_TENANT_ID
    obj.email = email
    obj.full_name = "Test User"
    obj.role = TEST_ROLE
    obj.hashed_password = _HASHED_PASSWORD
    obj.mfa_enabled = mfa_enabled
    obj.mfa_secret = mfa_secret
    obj.is_active = True
    return obj


def _fresh_users() -> dict:
    """Create a fresh set of mock users (avoids cross-test mutation)."""
    return {
        TEST_EMAIL: _make_mock_user(),
        MFA_EMAIL: _make_mock_user(
            user_id=MFA_USER_ID,
            email=MFA_EMAIL,
            mfa_enabled=True,
            mfa_secret=MFA_SECRET,
        ),
    }


class _MockMfaSessionFactory:
    """Mock async_session_factory for MFA tests."""

    def __init__(self, users: dict):
        self._users = users

    def __call__(self):
        session = AsyncMock()
        users = self._users

        @asynccontextmanager
        async def _begin():
            yield

        session.begin = _begin

        async def _execute(query):
            result = MagicMock()
            # Try to match user by ID from the query string
            query_str = str(query)
            for user in users.values():
                if str(user.id) in query_str:
                    result.scalar_one_or_none.return_value = user
                    return result
            # Default: return MFA user (most tests need MFA capabilities)
            result.scalar_one_or_none.return_value = users.get(MFA_EMAIL)
            return result

        session.execute = _execute
        return self._wrap(session)

    @asynccontextmanager
    async def _wrap(self, session):
        yield session


@pytest.fixture(autouse=True)
def _mock_db():
    """Mock DB lookups for auth and MFA routers (fresh users each test)."""
    users = _fresh_users()
    with (
        patch(
            "apps.api.auth.router._get_user_by_email",
            new_callable=AsyncMock,
            side_effect=lambda email: users.get(email),
        ),
        patch(
            "apps.api.auth.router._get_user_by_id",
            new_callable=AsyncMock,
            side_effect=lambda uid: next(
                (u for u in users.values() if u.id == uid), None
            ),
        ),
        patch(
            "apps.api.auth.mfa_router.async_session_factory",
            new=_MockMfaSessionFactory(users),
        ),
    ):
        yield


# ── TOTP core function tests ──


class TestTotpFunctions:
    def test_generate_secret_returns_base32(self):
        secret = generate_secret()
        assert len(secret) == 32
        assert secret.isalnum()

    def test_provisioning_uri_contains_issuer(self):
        secret = generate_secret()
        uri = generate_provisioning_uri("test@example.com", secret)
        assert uri.startswith("otpauth://totp/")
        assert "LexiBel" in uri
        assert "test%40example.com" in uri or "test@example.com" in uri

    def test_verify_correct_code(self):
        secret = generate_secret()
        totp = pyotp.TOTP(secret)
        code = totp.now()
        assert verify_totp(secret, code) is True

    def test_verify_wrong_code(self):
        secret = generate_secret()
        assert verify_totp(secret, "000000") is False

    def test_verify_invalid_format(self):
        secret = generate_secret()
        assert verify_totp(secret, "abcdef") is False


# ── MFA setup endpoint ──


@pytest.mark.asyncio
async def test_mfa_setup_returns_secret_and_uri():
    """POST /mfa/setup with valid auth returns secret + provisioning URI."""
    access_token = create_access_token(
        TEST_USER_ID, TEST_TENANT_ID, TEST_ROLE, TEST_EMAIL
    )
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/v1/auth/mfa/setup",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "secret" in data
    assert len(data["secret"]) == 32
    assert "provisioning_uri" in data
    assert "otpauth://totp/" in data["provisioning_uri"]
    assert "LexiBel" in data["provisioning_uri"]


@pytest.mark.asyncio
async def test_mfa_setup_requires_auth():
    """POST /mfa/setup without auth returns 401."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/api/v1/auth/mfa/setup")
    assert resp.status_code == 401


# ── Login with MFA ──


@pytest.mark.asyncio
async def test_login_mfa_user_returns_mfa_required():
    """Login with MFA-enabled user returns mfa_required=true + mfa_token."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": MFA_EMAIL, "password": TEST_PASSWORD},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["mfa_required"] is True
    assert data["mfa_token"] is not None
    assert data["access_token"] is None


@pytest.mark.asyncio
async def test_login_non_mfa_user_returns_tokens():
    """Login with non-MFA user returns access_token + refresh_token."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["mfa_required"] is False
    assert data["access_token"] is not None
    assert data["refresh_token"] is not None


# ── MFA challenge ──


@pytest.mark.asyncio
async def test_mfa_challenge_completes_login():
    """POST /mfa/challenge with valid mfa_token + code returns full JWT pair."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Step 1: Login (gets mfa_token)
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": MFA_EMAIL, "password": TEST_PASSWORD},
        )
        mfa_token = login_resp.json()["mfa_token"]

        # Step 2: Generate valid TOTP code
        totp = pyotp.TOTP(MFA_SECRET)
        code = totp.now()

        # Step 3: Complete MFA challenge
        resp = await client.post(
            "/api/v1/auth/mfa/challenge",
            json={"mfa_token": mfa_token, "code": code},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["access_token"] is not None
    assert data["refresh_token"] is not None

    # Verify the access token is valid
    claims = verify_token(data["access_token"])
    assert claims["sub"] == str(MFA_USER_ID)
    assert claims["tid"] == str(TEST_TENANT_ID)
    assert claims["role"] == TEST_ROLE


@pytest.mark.asyncio
async def test_mfa_challenge_rejects_wrong_code():
    """POST /mfa/challenge with wrong TOTP code returns 401."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": MFA_EMAIL, "password": TEST_PASSWORD},
        )
        mfa_token = login_resp.json()["mfa_token"]

        resp = await client.post(
            "/api/v1/auth/mfa/challenge",
            json={"mfa_token": mfa_token, "code": "000000"},
        )
    assert resp.status_code == 401
    assert "Invalid TOTP code" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_mfa_challenge_rejects_invalid_token():
    """POST /mfa/challenge with invalid mfa_token returns 401."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/v1/auth/mfa/challenge",
            json={"mfa_token": "invalid.jwt.token", "code": "123456"},
        )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_mfa_challenge_rejects_access_token_as_mfa_token():
    """POST /mfa/challenge with an access token (wrong type) returns 401."""
    access_token = create_access_token(
        MFA_USER_ID, TEST_TENANT_ID, TEST_ROLE, MFA_EMAIL
    )
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/v1/auth/mfa/challenge",
            json={"mfa_token": access_token, "code": "123456"},
        )
    assert resp.status_code == 401
