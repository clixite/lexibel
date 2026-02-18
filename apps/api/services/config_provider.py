"""Unified config provider: DB settings first, then env vars.

Use this instead of os.getenv() in services that need tenant-scoped config.
"""

import os
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.services.settings_service import get_setting


async def get_config(
    session: AsyncSession, tenant_id: uuid.UUID, key: str
) -> str | None:
    """Get config value: DB first, then env var."""
    value = await get_setting(session, tenant_id, key)
    if value:
        return value
    return os.getenv(key)


async def get_configs(
    session: AsyncSession, tenant_id: uuid.UUID, keys: list[str]
) -> dict[str, str | None]:
    """Get multiple config values at once."""
    result: dict[str, str | None] = {}
    for key in keys:
        result[key] = await get_config(session, tenant_id, key)
    return result
