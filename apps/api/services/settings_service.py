"""Service for managing tenant settings stored in DB.

Settings are stored in the tenant_settings table. Sensitive values
(API keys, secrets) are encrypted at rest using Fernet (AES-128-CBC).
Falls back to os.getenv() when a key is not found in the DB.
"""

import logging
import os
import re
import uuid

from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.models.tenant_setting import TenantSetting

logger = logging.getLogger(__name__)

# Encryption key — SETTINGS_ENCRYPTION_KEY env var is required in production.
# A random key is generated as fallback for dev/testing only.
_RAW_KEY = os.getenv("SETTINGS_ENCRYPTION_KEY", "")
if _RAW_KEY:
    _FERNET_KEY = _RAW_KEY.encode() if isinstance(_RAW_KEY, str) else _RAW_KEY
else:
    _FERNET_KEY = Fernet.generate_key()
    logger.warning(
        "SETTINGS_ENCRYPTION_KEY not set — using ephemeral key. "
        "Encrypted settings will be lost on restart."
    )
_fernet = Fernet(_FERNET_KEY)

# Keys whose values should be auto-encrypted
_SENSITIVE_PATTERNS = re.compile(
    r"(SECRET|API_KEY|PASSWORD|ENCRYPTION_KEY|TOKEN|PRIVATE_KEY)", re.IGNORECASE
)


def is_sensitive_key(key: str) -> bool:
    """Return True if the key name indicates a sensitive value."""
    return bool(_SENSITIVE_PATTERNS.search(key))


def mask_value(value: str) -> str:
    """Mask a sensitive value for display: show first 6 chars + ***."""
    if not value or len(value) <= 6:
        return "***"
    return value[:6] + "***"


# ── CRUD ──────────────────────────────────────────────────────────────


async def get_setting(
    session: AsyncSession, tenant_id: uuid.UUID, key: str
) -> str | None:
    """Get a single setting value, decrypting if needed.

    Falls back to os.getenv(key) if not found in DB.
    """
    result = await session.execute(
        select(TenantSetting).where(
            TenantSetting.tenant_id == tenant_id,
            TenantSetting.key == key,
        )
    )
    setting = result.scalar_one_or_none()
    if not setting:
        return os.getenv(key)
    if setting.is_encrypted:
        try:
            return _fernet.decrypt(setting.value.encode()).decode()
        except Exception:
            logger.warning("Failed to decrypt setting %s for tenant %s", key, tenant_id)
            return None
    return setting.value


async def get_settings_by_category(
    session: AsyncSession, tenant_id: uuid.UUID, category: str
) -> dict[str, str]:
    """Get all settings for a category as a {key: decrypted_value} dict."""
    result = await session.execute(
        select(TenantSetting).where(
            TenantSetting.tenant_id == tenant_id,
            TenantSetting.category == category,
        )
    )
    settings: dict[str, str] = {}
    for s in result.scalars().all():
        if s.is_encrypted:
            try:
                settings[s.key] = _fernet.decrypt(s.value.encode()).decode()
            except Exception:
                settings[s.key] = ""
        else:
            settings[s.key] = s.value
    return settings


async def get_all_settings(
    session: AsyncSession, tenant_id: uuid.UUID
) -> list[dict]:
    """Get all settings for a tenant, grouped by category.

    Encrypted values are masked for display.
    """
    result = await session.execute(
        select(TenantSetting)
        .where(TenantSetting.tenant_id == tenant_id)
        .order_by(TenantSetting.category, TenantSetting.key)
    )
    settings = []
    for s in result.scalars().all():
        display_value = mask_value(s.value) if s.is_encrypted else s.value
        settings.append(
            {
                "id": str(s.id),
                "category": s.category,
                "key": s.key,
                "value": display_value,
                "is_encrypted": s.is_encrypted,
                "label": s.label,
                "description": s.description,
                "is_required": s.is_required,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            }
        )
    return settings


async def upsert_setting(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    key: str,
    value: str,
    category: str,
    is_encrypted: bool | None = None,
    label: str = "",
    description: str = "",
    is_required: bool = False,
    updated_by: uuid.UUID | None = None,
) -> TenantSetting:
    """Create or update a setting. Auto-encrypts sensitive keys."""
    # Auto-detect encryption if not specified
    if is_encrypted is None:
        is_encrypted = is_sensitive_key(key)

    stored_value = _fernet.encrypt(value.encode()).decode() if is_encrypted else value

    result = await session.execute(
        select(TenantSetting).where(
            TenantSetting.tenant_id == tenant_id,
            TenantSetting.key == key,
        )
    )
    setting = result.scalar_one_or_none()

    if setting:
        setting.value = stored_value
        setting.is_encrypted = is_encrypted
        setting.category = category
        if label:
            setting.label = label
        if description:
            setting.description = description
        setting.updated_by = updated_by
    else:
        setting = TenantSetting(
            tenant_id=tenant_id,
            key=key,
            value=stored_value,
            is_encrypted=is_encrypted,
            category=category,
            label=label,
            description=description,
            is_required=is_required,
            updated_by=updated_by,
        )
        session.add(setting)

    await session.flush()
    return setting


async def delete_setting(
    session: AsyncSession, tenant_id: uuid.UUID, key: str
) -> bool:
    """Delete a setting. Returns True if found and deleted."""
    result = await session.execute(
        select(TenantSetting).where(
            TenantSetting.tenant_id == tenant_id,
            TenantSetting.key == key,
        )
    )
    setting = result.scalar_one_or_none()
    if setting:
        await session.delete(setting)
        return True
    return False


# ── Connection testers ────────────────────────────────────────────────


async def test_connection(category: str, settings: dict[str, str]) -> dict:
    """Test if credentials for a category actually work."""
    testers = {
        "google": _test_google,
        "microsoft": _test_microsoft,
        "ringover": _test_ringover,
        "plaud": _test_plaud,
        "llm": _test_llm,
    }
    tester = testers.get(category)
    if not tester:
        return {"success": False, "error": f"Catégorie inconnue: {category}"}
    return await tester(settings)


async def _test_google(settings: dict) -> dict:
    client_id = settings.get("GOOGLE_CLIENT_ID", "")
    if not client_id:
        return {"success": False, "error": "Client ID manquant"}
    if not client_id.endswith(".apps.googleusercontent.com"):
        return {
            "success": False,
            "error": "Format Client ID invalide (doit finir par .apps.googleusercontent.com)",
        }
    return {
        "success": True,
        "message": "Format Client ID valide. La connexion sera testée lors du premier login OAuth.",
    }


async def _test_microsoft(settings: dict) -> dict:
    import httpx

    client_id = settings.get("MICROSOFT_CLIENT_ID", "")
    if not client_id:
        return {"success": False, "error": "Client ID manquant"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                "https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration"
            )
            if r.status_code == 200:
                return {
                    "success": True,
                    "message": "Endpoint Microsoft accessible. Credentials validées au premier login.",
                }
    except Exception as e:
        return {"success": False, "error": str(e)}
    return {"success": False, "error": "Impossible de joindre Microsoft"}


async def _test_ringover(settings: dict) -> dict:
    import httpx

    api_key = settings.get("RINGOVER_API_KEY", "")
    if not api_key:
        return {"success": False, "error": "Clé API manquante"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                "https://public-api.ringover.com/v2/calls",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            if r.status_code == 200:
                return {"success": True, "message": "Connexion Ringover OK"}
            elif r.status_code == 401:
                return {"success": False, "error": "Clé API invalide"}
            return {"success": False, "error": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _test_plaud(settings: dict) -> dict:
    api_key = settings.get("PLAUD_API_KEY", "")
    if not api_key:
        return {"success": False, "error": "Clé API manquante"}
    return {
        "success": True,
        "message": "Clé Plaud enregistrée. Webhook actif sur /api/v1/webhooks/plaud",
    }


async def _test_llm(settings: dict) -> dict:
    import httpx

    providers = {
        "ANTHROPIC_API_KEY": ("Anthropic Claude", "https://api.anthropic.com/v1/messages"),
        "OPENAI_API_KEY": ("OpenAI GPT", "https://api.openai.com/v1/models"),
        "MISTRAL_API_KEY": ("Mistral AI", "https://api.mistral.ai/v1/models"),
        "GEMINI_API_KEY": ("Google Gemini", "https://generativelanguage.googleapis.com/v1beta/models"),
    }
    results = []
    async with httpx.AsyncClient(timeout=10) as client:
        for env_key, (name, url) in providers.items():
            api_key = settings.get(env_key, "")
            if not api_key:
                continue
            try:
                headers: dict[str, str] = {}
                test_url = url
                if "anthropic" in url:
                    headers = {
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                    }
                elif "openai" in url or "mistral" in url:
                    headers = {"Authorization": f"Bearer {api_key}"}
                elif "google" in url:
                    test_url = f"{url}?key={api_key}"
                r = await client.get(test_url, headers=headers)
                if r.status_code in (200, 201):
                    results.append({"provider": name, "success": True})
                else:
                    results.append(
                        {"provider": name, "success": False, "error": f"HTTP {r.status_code}"}
                    )
            except Exception as e:
                results.append({"provider": name, "success": False, "error": str(e)})

    if not results:
        return {"success": False, "error": "Aucune clé API LLM configurée"}
    any_success = any(r["success"] for r in results)
    return {"success": any_success, "providers": results}
