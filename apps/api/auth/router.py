"""Auth router — login, refresh, logout, password reset, and /me endpoints.

POST /api/v1/auth/login           — email + password → JWT pair (or MFA challenge)
POST /api/v1/auth/refresh         — refresh token → new access token
POST /api/v1/auth/logout          — revoke current token via Redis blacklist
GET  /api/v1/auth/me              — current user profile from JWT
POST /api/v1/auth/forgot-password — request a password reset token
POST /api/v1/auth/reset-password  — reset password using token
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select

from apps.api.auth.jwt import (
    TokenError,
    blacklist_token,
    consume_reset_token,
    create_access_token,
    create_mfa_token,
    create_refresh_token,
    create_reset_token,
    verify_token,
)
from apps.api.auth.passwords import hash_password, verify_password
from apps.api.auth.schemas import (
    AccessTokenResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    ResetPasswordRequest,
    ResetPasswordResponse,
    UserProfile,
)
from apps.api.dependencies import get_current_user
from packages.db.models.user import User
from packages.db.session import async_session_factory

logger = logging.getLogger(__name__)

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

    # Constant-time: always run bcrypt even if user doesn't exist to prevent
    # timing-based user enumeration attacks.
    _dummy_hash = "$2b$12$000000000000000000000000000000000000000000000000000000"
    password_hash = (
        user.hashed_password if (user and user.hashed_password) else _dummy_hash
    )
    password_valid = verify_password(body.password, password_hash)

    if user is None or not user.hashed_password or not password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account deactivated",
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

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or deactivated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        user_id=user_id,
        tenant_id=uuid.UUID(claims["tid"]),
        role=user.role,
        email=user.email,
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


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    _user: dict = Depends(get_current_user),
) -> None:
    """Revoke the current access token by adding its jti to Redis blacklist.

    The token is blacklisted for its remaining TTL so it auto-expires.
    Frontend should also clear locally stored tokens.
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        await blacklist_token(token)


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(body: ForgotPasswordRequest) -> ForgotPasswordResponse:
    """Request a password reset token.

    Always returns success to prevent email enumeration.
    If the email exists, a reset token is generated. In production,
    this token should be sent via email. For now, it's logged.
    """
    user = await _get_user_by_email(body.email)

    if user and user.hashed_password:
        token = create_reset_token(user_id=user.id, email=user.email)
        # In production: send email with reset link containing this token
        # For now, log the token for development/testing
        logger.info(
            "Password reset token generated for %s: %s",
            body.email,
            token,
        )

    # Always return same response to prevent email enumeration
    return ForgotPasswordResponse(
        message="If an account with that email exists, a reset link has been sent."
    )


@router.post("/reset-password", response_model=ResetPasswordResponse)
async def reset_password(body: ResetPasswordRequest) -> ResetPasswordResponse:
    """Reset password using a valid reset token."""
    if len(body.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters",
        )

    try:
        claims = verify_token(body.token, expected_type="reset")
    except TokenError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    # Enforce single-use
    jti = claims.get("jti")
    if jti:
        is_first_use = await consume_reset_token(jti)
        if not is_first_use:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token already used",
            )

    user_id = uuid.UUID(claims["sub"])

    async with async_session_factory() as session:
        async with session.begin():
            result = await session.execute(
                select(User).where(User.id == user_id, User.is_active.is_(True))
            )
            user = result.scalar_one_or_none()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User not found or account deactivated",
                )
            user.hashed_password = hash_password(body.new_password)

    return ResetPasswordResponse(message="Password has been reset successfully.")
