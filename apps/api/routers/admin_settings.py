"""Admin settings endpoints — in-app configuration wizard.

Allows super_admin to manage tenant settings (API keys, OAuth credentials)
from the UI instead of editing .env files via SSH.

All endpoints require super_admin role.
Sensitive values are auto-encrypted and masked in responses.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_current_user, get_db_session
from apps.api.services import settings_service

router = APIRouter(prefix="/api/v1/admin/settings", tags=["admin-settings"])


def _require_super_admin(user: dict) -> None:
    if user.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Super admin access required")


# ── Request / Response models ──


class SettingItem(BaseModel):
    key: str
    value: str
    category: str
    label: str = ""
    description: str = ""
    is_required: bool = False


class SettingsBatchRequest(BaseModel):
    settings: list[SettingItem]


# ── Endpoints ──


@router.get("")
async def get_all_settings(
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """Get all settings for the current tenant, grouped by category.

    Encrypted values are masked (e.g. 'sk-ant-***').
    """
    _require_super_admin(user)
    tenant_id = user["tenant_id"] if isinstance(user["tenant_id"], uuid.UUID) else uuid.UUID(str(user["tenant_id"]))

    settings = await settings_service.get_all_settings(session, tenant_id)

    # Group by category
    grouped: dict[str, list] = {}
    for s in settings:
        grouped.setdefault(s["category"], []).append(s)

    return {"settings": grouped, "total": len(settings)}


@router.get("/{category}")
async def get_settings_by_category(
    category: str,
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """Get settings for a specific category."""
    _require_super_admin(user)
    tenant_id = user["tenant_id"] if isinstance(user["tenant_id"], uuid.UUID) else uuid.UUID(str(user["tenant_id"]))

    all_settings = await settings_service.get_all_settings(session, tenant_id)
    filtered = [s for s in all_settings if s["category"] == category]

    return {"category": category, "settings": filtered}


@router.put("")
async def upsert_settings(
    body: SettingsBatchRequest,
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """Batch upsert settings. Sensitive keys are auto-encrypted."""
    _require_super_admin(user)
    tenant_id = user["tenant_id"] if isinstance(user["tenant_id"], uuid.UUID) else uuid.UUID(str(user["tenant_id"]))
    user_id = user["user_id"] if isinstance(user["user_id"], uuid.UUID) else uuid.UUID(str(user["user_id"]))

    results = []
    for item in body.settings:
        setting = await settings_service.upsert_setting(
            session=session,
            tenant_id=tenant_id,
            key=item.key,
            value=item.value,
            category=item.category,
            label=item.label,
            description=item.description,
            is_required=item.is_required,
            updated_by=user_id,
        )
        results.append(
            {
                "key": item.key,
                "category": item.category,
                "status": "saved",
                "is_encrypted": setting.is_encrypted,
            }
        )

    await session.commit()
    return {"results": results, "saved": len(results)}


@router.post("/test/{category}")
async def test_connection(
    category: str,
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """Test credentials for a category by making real API calls."""
    _require_super_admin(user)
    tenant_id = user["tenant_id"] if isinstance(user["tenant_id"], uuid.UUID) else uuid.UUID(str(user["tenant_id"]))

    # Get decrypted settings for the category
    decrypted = await settings_service.get_settings_by_category(
        session, tenant_id, category
    )

    result = await settings_service.test_connection(category, decrypted)
    return result


@router.delete("/{key}")
async def delete_setting(
    key: str,
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """Delete a single setting by key."""
    _require_super_admin(user)
    tenant_id = user["tenant_id"] if isinstance(user["tenant_id"], uuid.UUID) else uuid.UUID(str(user["tenant_id"]))

    deleted = await settings_service.delete_setting(session, tenant_id, key)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")

    await session.commit()
    return {"status": "deleted", "key": key}
