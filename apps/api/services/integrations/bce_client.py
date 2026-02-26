"""BCE/KBO Client — Banque-Carrefour des Entreprises lookup.

Queries the Belgian Crossroads Bank for Enterprises (BCE/KBO)
to retrieve company information from a BCE number.

Features:
- Circuit breaker protection (BCE API is notoriously unreliable)
- Redis cache with 24h TTL (CISO mandate: no long-term storage of BCE data)
- Graceful fallback returning cached/partial data when API is down
- Structured response with Belgian legal entity fields

API: https://kbopub.economie.fgov.be/kbopub/zoeknummerform.html
Public data endpoint: Open Data via CBE JSON API

Security notes (CISO):
- BCE data is public but we don't persist raw responses in PostgreSQL
- Cache in Redis with TTL only
- No PII stored (BCE = public company registry)
"""

import json
import logging
import os
from dataclasses import asdict, dataclass

import httpx

from apps.api.services.integrations.circuit_breaker import (
    CircuitBreakerConfig,
    get_circuit_breaker,
)

logger = logging.getLogger(__name__)

BCE_API_BASE = os.getenv("BCE_API_URL", "https://kbopub.economie.fgov.be/kbopub/api/v1")
BCE_CACHE_TTL = 86400  # 24 hours — CISO mandate
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


@dataclass
class BCECompanyInfo:
    """Structured BCE company lookup result."""

    bce_number: str
    denomination: str | None = None
    legal_form: str | None = None
    legal_form_code: str | None = None
    status: str | None = None  # active | stopped | closing
    address_street: str | None = None
    address_zip: str | None = None
    address_city: str | None = None
    address_country: str = "BE"
    start_date: str | None = None
    vat_number: str | None = None
    nace_codes: list[str] | None = None
    source: str = "api"  # api | cache | fallback

    def to_dict(self) -> dict:
        return asdict(self)


# ── Belgian legal form mapping ──

LEGAL_FORMS = {
    "014": "SA",
    "015": "SRL",
    "017": "SC",
    "019": "SNC",
    "020": "SCS",
    "023": "ASBL",
    "024": "AISBL",
    "025": "Fondation",
    "027": "GIE",
    "030": "SE",
    "610": "Profession libérale",
    "612": "Personne physique",
}


async def _get_redis():
    """Get Redis connection for BCE cache."""
    try:
        import redis.asyncio as aioredis

        return aioredis.from_url(REDIS_URL, decode_responses=True, socket_timeout=3.0)
    except (ImportError, Exception):
        return None


async def _cache_get(bce_number: str) -> BCECompanyInfo | None:
    """Try to get BCE data from Redis cache."""
    redis = await _get_redis()
    if redis is None:
        return None

    try:
        cached = await redis.get(f"bce:{bce_number}")
        if cached:
            data = json.loads(cached)
            data["source"] = "cache"
            return BCECompanyInfo(**data)
    except Exception:
        pass
    finally:
        await redis.close()
    return None


async def _cache_set(bce_number: str, info: BCECompanyInfo) -> None:
    """Store BCE data in Redis cache with TTL."""
    redis = await _get_redis()
    if redis is None:
        return

    try:
        data = info.to_dict()
        data.pop("source", None)
        await redis.setex(f"bce:{bce_number}", BCE_CACHE_TTL, json.dumps(data))
    except Exception as e:
        logger.warning("BCE cache write failed: %s", e)
    finally:
        await redis.close()


async def _fetch_bce_api(bce_number: str) -> BCECompanyInfo:
    """Fetch company data from the BCE/KBO public API."""
    # Normalize BCE number: remove dots/spaces
    clean = bce_number.replace(".", "").replace(" ", "")

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{BCE_API_BASE}/enterprise/{clean}",
            headers={"Accept": "application/json"},
        )

        if response.status_code == 404:
            raise ValueError(f"BCE number {bce_number} not found")

        if response.status_code != 200:
            raise ConnectionError(
                f"BCE API returned {response.status_code}: {response.text[:200]}"
            )

        data = response.json()

    # Parse response (adapt to actual BCE API structure)
    denominations = data.get("denominations", [])
    denomination = None
    for d in denominations:
        if d.get("language") == "FR":
            denomination = d.get("denomination")
            break
    if not denomination and denominations:
        denomination = denominations[0].get("denomination")

    addresses = data.get("addresses", [])
    address = addresses[0] if addresses else {}

    legal_form_code = data.get("legalForm", {}).get("code", "")
    legal_form = LEGAL_FORMS.get(
        legal_form_code, data.get("legalForm", {}).get("description")
    )

    activities = data.get("activities", [])
    nace_codes = [a.get("naceCode") for a in activities if a.get("naceCode")]

    return BCECompanyInfo(
        bce_number=bce_number,
        denomination=denomination,
        legal_form=legal_form,
        legal_form_code=legal_form_code,
        status=data.get("status", {}).get("description"),
        address_street=address.get("street"),
        address_zip=address.get("zipcode"),
        address_city=address.get("city"),
        start_date=data.get("startDate"),
        vat_number=f"BE{clean}" if data.get("vatLiable") else None,
        nace_codes=nace_codes,
        source="api",
    )


async def _fallback_lookup(bce_number: str) -> BCECompanyInfo:
    """Fallback when BCE API is down — return cached or minimal data."""
    cached = await _cache_get(bce_number)
    if cached:
        cached.source = "fallback_cache"
        return cached

    # Absolute minimal fallback
    return BCECompanyInfo(
        bce_number=bce_number,
        denomination=None,
        status="unknown",
        source="fallback_empty",
    )


# ── Public API ──

_breaker = get_circuit_breaker(
    "bce_api",
    CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=60.0,
        half_open_max_calls=1,
        success_threshold=1,
    ),
)


async def lookup_bce(bce_number: str) -> BCECompanyInfo:
    """Look up a company by BCE/KBO number.

    Flow:
    1. Check Redis cache
    2. If miss → call BCE API through circuit breaker
    3. If API down → fallback to cache/empty
    4. Cache successful API responses

    Args:
        bce_number: Belgian company number (format: 0xxx.xxx.xxx)

    Returns:
        BCECompanyInfo with company data and source indicator
    """
    # Try cache first
    cached = await _cache_get(bce_number)
    if cached:
        return cached

    # Call API through circuit breaker
    info = await _breaker.call(
        _fetch_bce_api,
        bce_number,
        fallback=lambda bn: _fallback_lookup(bn),
    )

    # Cache successful API results
    if info.source == "api":
        await _cache_set(bce_number, info)

    return info


async def get_bce_status() -> dict:
    """Get BCE integration health status."""
    return {
        "service": "BCE/KBO",
        "circuit_breaker": _breaker.get_status(),
        "cache_ttl_seconds": BCE_CACHE_TTL,
        "api_base": BCE_API_BASE,
    }
