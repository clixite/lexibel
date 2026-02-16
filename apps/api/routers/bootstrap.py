"""Bootstrap router — seed the default tenant and admin user in PostgreSQL.

POST /api/v1/bootstrap/admin — creates the default super_admin user.
Idempotent: returns success whether the user is newly created or already exists.
"""

import logging
import uuid

from fastapi import APIRouter, status
from sqlalchemy import select

from apps.api.auth.passwords import hash_password
from packages.db.models.tenant import Tenant
from packages.db.models.user import User
from packages.db.session import async_session_factory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/bootstrap", tags=["bootstrap"])

DEFAULT_TENANT_ID = uuid.UUID("00000000-0000-4000-a000-000000000001")
DEFAULT_USER_ID = uuid.UUID("00000000-0000-4000-a000-000000000010")
DEFAULT_EMAIL = "nicolas@clixite.be"
DEFAULT_PASSWORD = "LexiBel2026!"
DEFAULT_ROLE = "super_admin"


async def ensure_admin_user() -> None:
    """Create the default tenant and admin user in PostgreSQL if they don't exist."""
    async with async_session_factory() as session:
        async with session.begin():
            # Check if admin user already exists
            result = await session.execute(
                select(User).where(User.id == DEFAULT_USER_ID)
            )
            if result.scalar_one_or_none() is not None:
                logger.info("Admin user already exists, skipping bootstrap")
                return

            # Ensure the default tenant exists
            result = await session.execute(
                select(Tenant).where(Tenant.id == DEFAULT_TENANT_ID)
            )
            if result.scalar_one_or_none() is None:
                tenant = Tenant(
                    id=DEFAULT_TENANT_ID,
                    name="Clixite",
                    slug="clixite",
                    plan="enterprise",
                    locale="fr-BE",
                    config={},
                    status="active",
                )
                session.add(tenant)
                await session.flush()
                logger.info("Created default tenant: Clixite")

            # Create the admin user
            admin = User(
                id=DEFAULT_USER_ID,
                tenant_id=DEFAULT_TENANT_ID,
                email=DEFAULT_EMAIL,
                full_name="Nicolas Simon",
                role=DEFAULT_ROLE,
                hashed_password=hash_password(DEFAULT_PASSWORD),
                auth_provider="local",
                mfa_enabled=False,
                is_active=True,
            )
            session.add(admin)
            logger.info("Created admin user: %s", DEFAULT_EMAIL)


@router.post("/admin", status_code=status.HTTP_201_CREATED)
async def bootstrap_admin() -> dict:
    """Create the default admin user. Idempotent — safe to call multiple times."""
    await ensure_admin_user()
    return {
        "message": "Admin user created",
        "email": DEFAULT_EMAIL,
        "tenant": "Clixite",
        "tenant_id": str(DEFAULT_TENANT_ID),
        "role": DEFAULT_ROLE,
    }
