"""Auth router — login, refresh, and /me endpoints.

POST /api/v1/auth/login   — email + password → JWT pair (or MFA challenge)
POST /api/v1/auth/refresh — refresh token → new access token
GET  /api/v1/auth/me      — current user profile from JWT
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from apps.api.auth.jwt import (
    TokenError,
    create_access_token,
    create_mfa_token,
    create_refresh_token,
    verify_token,
)
from apps.api.auth.passwords import verify_password
from apps.api.auth.schemas import (
    AccessTokenResponse,
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    UserProfile,
)
from apps.api.dependencies import get_current_user
from packages.db.models.user import User
from packages.db.session import async_session_factory

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


async def _get_user_by_email(email: str) -> User | None:
    """Look up an active user by email (bypasses RLS for login)."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(User).where(User.email == email, User.is_active.is_(True))
        )
        return result.scalar_one_or_none()


async def _get_user_by_id(user_id: uuid.UUID) -> User | None:
    """Look up an active user by ID (bypasses RLS for refresh)."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(User).where(User.id == user_id, User.is_active.is_(True))
        )
        return result.scalar_one_or_none()


# ── Endpoints ──


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest) -> LoginResponse:
    """Authenticate with email + password.

    If MFA is enabled on the user, returns mfa_required=true with a
    short-lived mfa_token. The client must then call /mfa/challenge
    with the TOTP code to complete authentication.
    """
    user = await _get_user_by_email(body.email)
    if user is None or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # If MFA is enabled, return MFA challenge instead of full tokens
    if user.mfa_enabled and user.mfa_secret:
        mfa_token = create_mfa_token(
            user_id=user.id,
            tenant_id=user.tenant_id,
            email=user.email,
        )
        return LoginResponse(mfa_required=True, mfa_token=mfa_token)

    # No MFA — issue full JWT pair
    access_token = create_access_token(
        user_id=user.id,
        tenant_id=user.tenant_id,
        role=user.role,
        email=user.email,
    )
    refresh_token = create_refresh_token(
        user_id=user.id,
        tenant_id=user.tenant_id,
    )

    return LoginResponse(access_token=access_token, refresh_token=refresh_token)


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
    user = await _get_user_by_id(user_id)

    role = user.role if user else "junior"
    email = user.email if user else ""

    access_token = create_access_token(
        user_id=user_id,
        tenant_id=uuid.UUID(claims["tid"]),
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
