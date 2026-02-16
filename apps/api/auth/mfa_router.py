"""MFA router — TOTP setup, verification, and login challenge.

POST /api/v1/auth/mfa/setup     — generate secret + provisioning URI (requires auth)
POST /api/v1/auth/mfa/verify    — verify TOTP code and activate MFA on user
POST /api/v1/auth/mfa/challenge — verify TOTP during login when MFA is enabled
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from apps.api.auth.jwt import (
    TokenError,
    create_access_token,
    create_refresh_token,
    verify_token,
)
from apps.api.auth.mfa import generate_provisioning_uri, generate_secret, verify_totp
from apps.api.auth.router import _STUB_USERS
from apps.api.dependencies import get_current_user

mfa_router = APIRouter(prefix="/api/v1/auth/mfa", tags=["mfa"])


# ── Schemas ──


class MfaSetupResponse(BaseModel):
    secret: str
    provisioning_uri: str


class MfaVerifyRequest(BaseModel):
    code: str


class MfaVerifyResponse(BaseModel):
    mfa_enabled: bool


class MfaChallengeRequest(BaseModel):
    mfa_token: str
    code: str


class MfaChallengeResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# ── Endpoints ──


@mfa_router.post("/setup", response_model=MfaSetupResponse)
async def mfa_setup(
    current_user: dict = Depends(get_current_user),
) -> MfaSetupResponse:
    """Generate a TOTP secret and provisioning URI for QR code scanning.

    Requires authentication. The secret is stored on the user record
    but MFA is not activated until /verify confirms a valid code.
    """
    secret = generate_secret()
    email = current_user["email"]
    uri = generate_provisioning_uri(email, secret)

    # Store the pending secret on the stub user
    user = _STUB_USERS.get(email)
    if user:
        user["mfa_secret"] = secret

    return MfaSetupResponse(secret=secret, provisioning_uri=uri)


@mfa_router.post("/verify", response_model=MfaVerifyResponse)
async def mfa_verify(
    body: MfaVerifyRequest,
    current_user: dict = Depends(get_current_user),
) -> MfaVerifyResponse:
    """Verify a TOTP code and activate MFA on the user's account.

    Must be called after /setup. The user scans the QR code with their
    authenticator app, then submits the 6-digit code here.
    """
    email = current_user["email"]
    user = _STUB_USERS.get(email)

    if not user or not user.get("mfa_secret"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA setup not initiated. Call /mfa/setup first.",
        )

    if not verify_totp(user["mfa_secret"], body.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid TOTP code",
        )

    # Activate MFA
    user["mfa_enabled"] = True

    return MfaVerifyResponse(mfa_enabled=True)


@mfa_router.post("/challenge", response_model=MfaChallengeResponse)
async def mfa_challenge(body: MfaChallengeRequest) -> MfaChallengeResponse:
    """Complete login by verifying TOTP code after password authentication.

    Called when login returns mfa_required=true. The mfa_token is a
    short-lived JWT (type=mfa) that proves the user passed password auth.
    """
    # Verify the MFA token
    try:
        claims = verify_token(body.mfa_token, expected_type="mfa")
    except TokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired MFA token",
        )

    user_id = uuid.UUID(claims["sub"])
    tenant_id = uuid.UUID(claims["tid"])
    email = claims.get("email", "")

    # Look up user to get MFA secret
    user = None
    for u in _STUB_USERS.values():
        if u["user_id"] == user_id:
            user = u
            break

    if not user or not user.get("mfa_secret"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA not configured for this user",
        )

    if not verify_totp(user["mfa_secret"], body.code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid TOTP code",
        )

    # MFA passed — issue full JWT pair
    access_token = create_access_token(
        user_id=user_id,
        tenant_id=tenant_id,
        role=user["role"],
        email=email,
    )
    refresh_token = create_refresh_token(
        user_id=user_id,
        tenant_id=tenant_id,
    )

    return MfaChallengeResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )
