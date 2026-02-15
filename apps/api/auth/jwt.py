"""JWT token creation and verification.

Access tokens (30 min) carry user identity + tenant + role.
Refresh tokens (7 days) carry only user identity for rotation.
Algorithm: HS256 with SECRET_KEY from environment.
"""
import os
import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-change-me-in-production")
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
REFRESH_TOKEN_EXPIRE_DAYS: int = 7


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
        "iat": now,
        "exp": now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
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
