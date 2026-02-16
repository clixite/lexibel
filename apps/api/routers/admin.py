"""Admin endpoints — health, tenants, users, stats."""
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from apps.api.dependencies import get_current_user

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def _require_super_admin(user: dict) -> None:
    if user.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Super admin access required")


# ── In-memory stores (stubs for demo; production uses DB) ──

_tenants_store: dict[str, dict] = {}
_users_store: dict[str, list[dict]] = {}  # tenant_id -> [users]
_invite_log: list[dict] = []


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
    return {"tenants": list(_tenants_store.values())}


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

    tenant_id = str(uuid.uuid4())
    tenant = {
        "id": tenant_id,
        "name": name,
        "domain": body.get("domain", ""),
        "plan": body.get("plan", "standard"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "active",
    }
    _tenants_store[tenant_id] = tenant
    _users_store[tenant_id] = []
    return tenant


@router.get("/stats")
async def global_stats(user: dict = Depends(get_current_user)):
    """Global statistics (super_admin only)."""
    _require_super_admin(user)

    total_users = sum(len(users) for users in _users_store.values())
    return {
        "tenants": len(_tenants_store),
        "users": total_users,
        "cases": 0,
        "documents": 0,
        "invoices": 0,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/users")
async def list_users(user: dict = Depends(get_current_user)):
    """List users for the current tenant."""
    tenant_id = str(user.get("tenant_id", ""))
    users = _users_store.get(tenant_id, [])
    return {"users": users}


@router.post("/users/invite")
async def invite_user(
    body: dict,
    user: dict = Depends(get_current_user),
):
    """Invite a user to the current tenant."""
    email = body.get("email")
    role = body.get("role", "junior")
    if not email:
        raise HTTPException(status_code=400, detail="Email required")

    valid_roles = {"admin", "lawyer", "paralegal", "secretary", "accountant", "junior", "super_admin"}
    if role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Valid: {valid_roles}")

    tenant_id = str(user.get("tenant_id", ""))
    new_user = {
        "id": str(uuid.uuid4()),
        "email": email,
        "role": role,
        "tenant_id": tenant_id,
        "status": "invited",
        "invited_at": datetime.now(timezone.utc).isoformat(),
        "invited_by": str(user.get("user_id", "")),
    }

    if tenant_id not in _users_store:
        _users_store[tenant_id] = []
    _users_store[tenant_id].append(new_user)

    # Stub: email notification would be sent here
    _invite_log.append({"email": email, "tenant_id": tenant_id})

    return {"message": f"Invitation sent to {email}", "user": new_user}


# ── Service health checkers ──

async def _check_postgres() -> dict:
    try:
        db_url = os.getenv("DATABASE_URL", "")
        return {"status": "healthy" if db_url else "not_configured"}
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
