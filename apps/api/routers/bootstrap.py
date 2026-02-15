"""Bootstrap router — seed the first admin user.

POST /api/v1/bootstrap/admin — creates the default super_admin user.
Only works when no users exist yet (empty stub store).
"""
import uuid

from fastapi import APIRouter, HTTPException, status

from apps.api.auth.passwords import hash_password
from apps.api.auth.router import _STUB_USERS, register_stub_user

router = APIRouter(prefix="/api/v1/bootstrap", tags=["bootstrap"])

_DEFAULT_TENANT_ID = uuid.UUID("00000000-0000-4000-a000-000000000001")
_DEFAULT_USER_ID = uuid.UUID("00000000-0000-4000-a000-000000000010")


@router.post("/admin", status_code=status.HTTP_201_CREATED)
async def bootstrap_admin() -> dict:
    """Create the default admin user. Fails if any users already exist."""
    if _STUB_USERS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Users already exist. Bootstrap is disabled.",
        )

    register_stub_user(
        email="nicolas@clixite.be",
        hashed_password=hash_password("LexiBel2026!"),
        user_id=_DEFAULT_USER_ID,
        tenant_id=_DEFAULT_TENANT_ID,
        role="super_admin",
    )

    return {
        "message": "Admin user created",
        "email": "nicolas@clixite.be",
        "tenant": "Clixite",
        "tenant_id": str(_DEFAULT_TENANT_ID),
        "role": "super_admin",
    }
