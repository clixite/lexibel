"""Admin endpoints — health, tenants, users, stats."""

import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.auth.passwords import hash_password
from apps.api.dependencies import get_current_user
from packages.db.models.case import Case
from packages.db.models.contact import Contact
from packages.db.models.invoice import Invoice
from packages.db.models.tenant import Tenant
from packages.db.models.user import User
from packages.db.session import async_session_factory

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def _require_super_admin(user: dict) -> None:
    if user.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Super admin access required")


async def _admin_session() -> AsyncSession:
    """Create a session without RLS for admin operations."""
    return async_session_factory()


@router.get("/health")
async def admin_health(user: dict = Depends(get_current_user)):
    """Aggregated service health check."""
    _require_super_admin(user)

    services = {
        "api": {"status": "healthy", "version": "0.1.0"},
        "database": await _check_postgres(),
        "redis": await _check_redis(),
        "qdrant": await _check_qdrant(),
        "minio": await _check_minio(),
        "vllm": await _check_vllm(),
        "neo4j": await _check_neo4j(),
    }

    all_healthy = all(s.get("status") == "healthy" for s in services.values())
    return {
        "status": "healthy" if all_healthy else "degraded",
        "services": services,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/tenants")
async def list_tenants(user: dict = Depends(get_current_user)):
    """List all tenants (super_admin only)."""
    _require_super_admin(user)
    async with async_session_factory() as session:
        result = await session.execute(
            select(Tenant).order_by(Tenant.created_at.desc())
        )
        tenants = result.scalars().all()
        return {
            "tenants": [
                {
                    "id": str(t.id),
                    "name": t.name,
                    "slug": t.slug,
                    "plan": t.plan,
                    "locale": t.locale,
                    "status": t.status,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                }
                for t in tenants
            ]
        }


@router.post("/tenants")
async def create_tenant(
    body: dict,
    user: dict = Depends(get_current_user),
):
    """Create a new tenant."""
    _require_super_admin(user)

    name = body.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="Tenant name required")

    slug = body.get("slug") or name.lower().replace(" ", "-")

    async with async_session_factory() as session:
        async with session.begin():
            # Check for duplicate slug
            result = await session.execute(select(Tenant).where(Tenant.slug == slug))
            if result.scalar_one_or_none() is not None:
                raise HTTPException(
                    status_code=409, detail=f"Tenant slug '{slug}' already exists"
                )

            tenant = Tenant(
                name=name,
                slug=slug,
                plan=body.get("plan", "solo"),
                locale=body.get("locale", "fr-BE"),
                config={},
                status="active",
            )
            session.add(tenant)
            await session.flush()
            await session.refresh(tenant)

            return {
                "id": str(tenant.id),
                "name": tenant.name,
                "slug": tenant.slug,
                "plan": tenant.plan,
                "status": tenant.status,
                "created_at": tenant.created_at.isoformat()
                if tenant.created_at
                else None,
            }


@router.get("/stats")
async def global_stats(user: dict = Depends(get_current_user)):
    """Global statistics (super_admin only)."""
    _require_super_admin(user)

    async with async_session_factory() as session:
        tenants_count = (
            await session.execute(select(func.count()).select_from(Tenant))
        ).scalar_one()
        users_count = (
            await session.execute(select(func.count()).select_from(User))
        ).scalar_one()
        cases_count = (
            await session.execute(select(func.count()).select_from(Case))
        ).scalar_one()
        contacts_count = (
            await session.execute(select(func.count()).select_from(Contact))
        ).scalar_one()
        invoices_count = (
            await session.execute(select(func.count()).select_from(Invoice))
        ).scalar_one()

    return {
        "tenants": tenants_count,
        "users": users_count,
        "cases": cases_count,
        "contacts": contacts_count,
        "invoices": invoices_count,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/users")
async def list_users(user: dict = Depends(get_current_user)):
    """List users for the current tenant."""
    tenant_id = user.get("tenant_id")

    async with async_session_factory() as session:
        result = await session.execute(
            select(User)
            .where(User.tenant_id == tenant_id)
            .order_by(User.created_at.desc())
        )
        users = result.scalars().all()
        return {
            "users": [
                {
                    "id": str(u.id),
                    "email": u.email,
                    "full_name": u.full_name,
                    "role": u.role,
                    "tenant_id": str(u.tenant_id),
                    "is_active": u.is_active,
                    "created_at": u.created_at.isoformat() if u.created_at else None,
                }
                for u in users
            ]
        }


@router.post("/users/invite")
async def invite_user(
    body: dict,
    user: dict = Depends(get_current_user),
):
    """Invite a user to the current tenant."""
    email = body.get("email")
    role = body.get("role", "junior")
    full_name = body.get("full_name", email.split("@")[0] if email else "")
    if not email:
        raise HTTPException(status_code=400, detail="Email required")

    valid_roles = {
        "admin",
        "partner",
        "associate",
        "junior",
        "secretary",
        "accountant",
        "super_admin",
    }
    if role not in valid_roles:
        raise HTTPException(
            status_code=400, detail=f"Invalid role. Valid: {valid_roles}"
        )

    tenant_id = user.get("tenant_id")

    async with async_session_factory() as session:
        async with session.begin():
            # Check for duplicate email in tenant
            result = await session.execute(
                select(User).where(User.tenant_id == tenant_id, User.email == email)
            )
            if result.scalar_one_or_none() is not None:
                raise HTTPException(
                    status_code=409,
                    detail=f"User with email '{email}' already exists in this tenant",
                )

            # Create user with a temporary password (they'll need to reset)
            temp_password = f"Temp{uuid.uuid4().hex[:8]}!"
            new_user = User(
                tenant_id=tenant_id,
                email=email,
                full_name=full_name,
                role=role,
                hashed_password=hash_password(temp_password),
                auth_provider="local",
                mfa_enabled=False,
                is_active=True,
            )
            session.add(new_user)
            await session.flush()
            await session.refresh(new_user)

            return {
                "message": f"User created: {email}",
                "user": {
                    "id": str(new_user.id),
                    "email": new_user.email,
                    "full_name": new_user.full_name,
                    "role": new_user.role,
                    "tenant_id": str(new_user.tenant_id),
                    "is_active": new_user.is_active,
                    "created_at": (
                        new_user.created_at.isoformat() if new_user.created_at else None
                    ),
                },
            }


# ── Service health checkers ──


async def _check_postgres() -> dict:
    try:
        from sqlalchemy import text

        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "healthy"}
    except Exception:
        return {"status": "unhealthy"}


async def _check_redis() -> dict:
    try:
        redis_url = os.getenv("REDIS_URL", "")
        if not redis_url:
            return {"status": "not_configured"}
        import redis as redis_lib

        r = redis_lib.from_url(redis_url, socket_timeout=2)
        r.ping()
        return {"status": "healthy"}
    except Exception:
        return {"status": "unavailable"}


async def _check_qdrant() -> dict:
    try:
        qdrant_url = os.getenv("QDRANT_URL", "")
        if not qdrant_url:
            return {"status": "not_configured"}
        import httpx

        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{qdrant_url}/collections")
            return {"status": "healthy" if resp.status_code == 200 else "unhealthy"}
    except Exception:
        return {"status": "unavailable"}


async def _check_minio() -> dict:
    try:
        endpoint = os.getenv("MINIO_ENDPOINT", "")
        return {"status": "healthy" if endpoint else "not_configured"}
    except Exception:
        return {"status": "unavailable"}


async def _check_vllm() -> dict:
    try:
        vllm_url = os.getenv("VLLM_BASE_URL", "")
        if not vllm_url:
            return {"status": "not_configured"}
        import httpx

        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{vllm_url}/models")
            return {"status": "healthy" if resp.status_code == 200 else "unhealthy"}
    except Exception:
        return {"status": "unavailable"}


async def _check_neo4j() -> dict:
    try:
        neo4j_uri = os.getenv("NEO4J_URI", "")
        return {"status": "healthy" if neo4j_uri else "not_configured"}
    except Exception:
        return {"status": "unavailable"}
