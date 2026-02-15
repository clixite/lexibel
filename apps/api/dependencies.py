"""FastAPI dependencies — tenant, user, and DB session injection.

These are used with Depends() in route handlers to get the current
tenant, user, and an RLS-scoped database session.
"""
import uuid
from collections.abc import AsyncGenerator

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from packages.db.session import async_session_factory


async def get_current_tenant(request: Request) -> uuid.UUID:
    """Extract tenant_id from request state (set by TenantMiddleware)."""
    tenant_id: uuid.UUID | None = getattr(request.state, "tenant_id", None)
    if tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant context required",
        )
    return tenant_id


async def get_current_user(request: Request) -> dict:
    """Extract user info from request state.

    Returns a dict with user_id, email, role, tenant_id.
    Until LXB-009 (JWT auth), reads from X-User-ID / X-User-Role headers.
    """
    user_id_raw = request.headers.get("X-User-ID")
    user_role = request.headers.get("X-User-Role", "junior")
    user_email = request.headers.get("X-User-Email", "")

    if not user_id_raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-User-ID header (JWT auth in LXB-009)",
        )

    try:
        user_id = uuid.UUID(user_id_raw)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid X-User-ID: must be a valid UUID",
        )

    tenant_id: uuid.UUID | None = getattr(request.state, "tenant_id", None)

    # Store in request.state for downstream middleware (audit)
    request.state.user_id = user_id
    request.state.user_role = user_role

    return {
        "user_id": user_id,
        "email": user_email,
        "role": user_role,
        "tenant_id": tenant_id,
    }


async def get_db_session(
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> AsyncGenerator[AsyncSession, None]:
    """Yield an RLS-scoped AsyncSession for the current tenant.

    The session sets SET LOCAL app.current_tenant_id so all queries
    are automatically filtered by the tenant's RLS policy.
    """
    async with async_session_factory() as session:
        async with session.begin():
            await session.execute(
                text("SET LOCAL app.current_tenant_id = :tid"),
                {"tid": str(tenant_id)},
            )
            yield session
