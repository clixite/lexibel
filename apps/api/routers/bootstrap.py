"""Bootstrap router — seed the default admin user.

POST /api/v1/bootstrap/admin — creates the default super_admin user.
Idempotent: returns success whether the user is newly created or already exists.
"""

import uuid

from fastapi import APIRouter, status

from apps.api.auth.passwords import hash_password
from apps.api.auth.router import _STUB_USERS, register_stub_user

router = APIRouter(prefix="/api/v1/bootstrap", tags=["bootstrap"])

DEFAULT_TENANT_ID = uuid.UUID("00000000-0000-4000-a000-000000000001")
DEFAULT_USER_ID = uuid.UUID("00000000-0000-4000-a000-000000000010")
DEFAULT_EMAIL = "nicolas@clixite.be"
DEFAULT_PASSWORD = "LexiBel2026!"
DEFAULT_ROLE = "super_admin"


def ensure_admin_user() -> None:
    """Register the default admin user if not already present."""
    if DEFAULT_EMAIL in _STUB_USERS:
        return
    register_stub_user(
        email=DEFAULT_EMAIL,
        hashed_password=hash_password(DEFAULT_PASSWORD),
        user_id=DEFAULT_USER_ID,
        tenant_id=DEFAULT_TENANT_ID,
        role=DEFAULT_ROLE,
    )


@router.post("/admin", status_code=status.HTTP_201_CREATED)
async def bootstrap_admin() -> dict:
    """Create the default admin user. Idempotent — safe to call multiple times."""
    ensure_admin_user()
    return {
        "message": "Admin user created",
        "email": DEFAULT_EMAIL,
        "tenant": "Clixite",
        "tenant_id": str(DEFAULT_TENANT_ID),
        "role": DEFAULT_ROLE,
    }
