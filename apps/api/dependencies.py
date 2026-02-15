"""FastAPI dependencies — tenant, user, and DB session injection.

These are used with Depends() in route handlers to get the current
tenant, user, and an RLS-scoped database session.

User and tenant are extracted from JWT claims (set by TenantMiddleware
on request.state). Falls back to X-Tenant-ID/X-User-ID headers for dev.
"""
import uuid
from collections.abc import AsyncGenerator

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from packages.db.session import async_session_factory


async def get_current_tenant(request: Request) -> uuid.UUID:
    """Extract tenant_id from request state (set by TenantMiddleware from JWT or header)."""
    tenant_id: uuid.UUID | None = getattr(request.state, "tenant_id", None)
    if tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant context required",
        )
    return tenant_id


async def get_current_user(request: Request) -> dict:
    """Extract user info from request state (set by TenantMiddleware from JWT claims).

    Returns a dict with user_id, email, role, tenant_id.
    """
    user_id: uuid.UUID | None = getattr(request.state, "user_id", None)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    tenant_id: uuid.UUID | None = getattr(request.state, "tenant_id", None)
    role: str = getattr(request.state, "user_role", None) or "junior"
    email: str = getattr(request.state, "user_email", "") or ""

    return {
        "user_id": user_id,
        "email": email,
        "role": role,
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
