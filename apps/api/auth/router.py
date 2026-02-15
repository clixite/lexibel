"""Auth router — login, refresh, and /me endpoints.

POST /api/v1/auth/login   — email + password → JWT pair
POST /api/v1/auth/refresh — refresh token → new access token
GET  /api/v1/auth/me      — current user profile from JWT
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from apps.api.auth.jwt import (
    TokenError,
    create_access_token,
    create_refresh_token,
    verify_token,
)
from apps.api.auth.passwords import verify_password
from apps.api.auth.schemas import (
    AccessTokenResponse,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    UserProfile,
)
from apps.api.dependencies import get_current_user

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# ── Stub user store (replaced by DB queries in LXB-006+) ──
# This allows login to work before the full user CRUD is built.
_STUB_USERS: dict[str, dict] = {}


def register_stub_user(
    email: str,
    hashed_password: str,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    role: str = "junior",
) -> None:
    """Register a user in the stub store (for testing / bootstrap)."""
    _STUB_USERS[email] = {
        "user_id": user_id,
        "tenant_id": tenant_id,
        "email": email,
        "hashed_password": hashed_password,
        "role": role,
    }


# ── Endpoints ──


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest) -> TokenResponse:
    """Authenticate with email + password, receive JWT pair."""
    user = _STUB_USERS.get(body.email)
    if user is None or not verify_password(body.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        user_id=user["user_id"],
        tenant_id=user["tenant_id"],
        role=user["role"],
        email=user["email"],
    )
    refresh_token = create_refresh_token(
        user_id=user["user_id"],
        tenant_id=user["tenant_id"],
    )

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(body: RefreshRequest) -> AccessTokenResponse:
    """Exchange a valid refresh token for a new access token."""
    try:
        claims = verify_token(body.refresh_token, expected_type="refresh")
    except TokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = uuid.UUID(claims["sub"])
    tenant_id = uuid.UUID(claims["tid"])

    # Look up user to get current role and email
    user = None
    for u in _STUB_USERS.values():
        if u["user_id"] == user_id:
            user = u
            break

    role = user["role"] if user else "junior"
    email = user["email"] if user else ""

    access_token = create_access_token(
        user_id=user_id,
        tenant_id=tenant_id,
        role=role,
        email=email,
    )

    return AccessTokenResponse(access_token=access_token)


@router.get("/me", response_model=UserProfile)
async def me(current_user: dict = Depends(get_current_user)) -> UserProfile:
    """Return the authenticated user's profile from JWT claims."""
    return UserProfile(
        user_id=current_user["user_id"],
        tenant_id=current_user["tenant_id"],
        email=current_user["email"],
        role=current_user["role"],
    )
