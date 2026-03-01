"""JWT token creation and verification.

Access tokens (30 min) carry user identity + tenant + role.
Refresh tokens (7 days) carry only user identity for rotation.
MFA tokens (5 min) are issued after password auth when MFA is enabled.
Algorithm: HS256 with SECRET_KEY from environment.

Token revocation via Redis blacklist (jti-based).
"""

import logging
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from apps.api.services.redis_client import get_redis

_logger = logging.getLogger(__name__)

_ENV = os.getenv("ENVIRONMENT", "development").lower()
SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-change-me-in-production")

if (
    _ENV in ("production", "prod")
    and SECRET_KEY == "dev-secret-change-me-in-production"
):
    raise RuntimeError(
        "FATAL: SECRET_KEY is set to the default value in production. "
        "Set a secure random SECRET_KEY environment variable."
    )

ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
REFRESH_TOKEN_EXPIRE_DAYS: int = 7
MFA_TOKEN_EXPIRE_MINUTES: int = 5


class TokenError(Exception):
    """Raised when a token is invalid, expired, or malformed."""


def create_access_token(
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    role: str,
    email: str,
) -> str:
    """Create a short-lived access token with full claims."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "tid": str(tenant_id),
        "role": role,
        "email": email,
        "type": "access",
        "jti": secrets.token_urlsafe(16),
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: uuid.UUID, tenant_id: uuid.UUID) -> str:
    """Create a long-lived refresh token with minimal claims."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "tid": str(tenant_id),
        "type": "refresh",
        "jti": secrets.token_urlsafe(16),
        "iat": now,
        "exp": now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_mfa_token(
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    email: str,
) -> str:
    """Create a short-lived MFA token (5 min) after password auth.

    Includes a jti for single-use enforcement via Redis.
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "tid": str(tenant_id),
        "email": email,
        "type": "mfa",
        "jti": secrets.token_urlsafe(16),
        "iat": now,
        "exp": now + timedelta(minutes=MFA_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str, expected_type: str = "access") -> dict:
    """Decode and validate a JWT token.

    Returns the decoded claims dict on success.
    Raises TokenError on any failure (expired, invalid, wrong type).
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as e:
        raise TokenError(f"Invalid token: {e}") from e

    if payload.get("type") != expected_type:
        raise TokenError(
            f"Wrong token type: expected '{expected_type}', got '{payload.get('type')}'"
        )

    return payload


def extract_claims(token: str) -> dict:
    """Extract claims from an access token without raising on expiry.

    Useful for logging/debugging. For auth, use verify_token().
    """
    try:
        return jwt.decode(
            token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False}
        )
    except JWTError as e:
        raise TokenError(f"Cannot decode token: {e}") from e


# ── Token Revocation (Redis-backed blacklist) ──


async def blacklist_token(token: str) -> None:
    """Add a token's jti to the Redis blacklist.

    TTL matches remaining token lifetime so entries auto-expire.
    """
    redis = await get_redis()
    if redis is None:
        _logger.warning("Redis unavailable — token revocation is best-effort only")
        return
    try:
        claims = jwt.decode(
            token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False}
        )
        jti = claims.get("jti")
        if not jti:
            return  # Legacy token without jti, nothing to blacklist
        exp = claims.get("exp", 0)
        ttl = max(int(exp - datetime.now(timezone.utc).timestamp()), 60)
        await redis.set(f"blacklist:{jti}", "1", ex=ttl)
    except Exception as e:
        _logger.warning("Failed to blacklist token: %s", e)


async def is_token_blacklisted(claims: dict) -> bool:
    """Check if a token's jti is in the blacklist."""
    jti = claims.get("jti")
    if not jti:
        return False  # Legacy token without jti — not blacklisted
    redis = await get_redis()
    if redis is None:
        return False  # No Redis → fail-open (availability over security)
    try:
        return await redis.exists(f"blacklist:{jti}") > 0
    except Exception as e:
        _logger.warning("Redis blacklist check failed: %s", e)
        return False


async def consume_mfa_token(jti: str) -> bool:
    """Mark an MFA token as consumed (single-use).

    Returns True if this is the first use. False if already consumed.
    Falls back to True (allow) if Redis is unavailable.
    """
    redis = await get_redis()
    if redis is None:
        return True  # Fail-open if Redis unavailable
    try:
        result = await redis.set(
            f"mfa_used:{jti}", "1", nx=True, ex=MFA_TOKEN_EXPIRE_MINUTES * 60
        )
        return bool(result)  # True = first use (set succeeded)
    except Exception as e:
        _logger.warning("Redis MFA consumption check failed: %s", e)
        return True  # Fail-open
