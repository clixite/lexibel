"""Integration health router — monitoring, BCE lookup, KYC check.

GET    /api/v1/integrations/health     — all circuit breaker statuses
GET    /api/v1/integrations/bce/{num}  — BCE/KBO company lookup
POST   /api/v1/integrations/kyc        — KYC risk assessment
GET    /api/v1/integrations/events     — event bus stream info
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from apps.api.dependencies import get_current_user
from apps.api.services.integrations.bce_client import get_bce_status, lookup_bce
from apps.api.services.integrations.circuit_breaker import get_all_breaker_statuses
from apps.api.services.integrations.event_bus import get_event_bus
from apps.api.services.integrations.kyc_service import perform_kyc_check

router = APIRouter(prefix="/api/v1/integrations", tags=["integrations-health"])


# ── Health & Monitoring ──


@router.get("/health")
async def integration_health(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Get health status of all external integrations.

    Returns circuit breaker states for BCE, DPA, Plaud, Ringover, etc.
    """
    breakers = get_all_breaker_statuses()
    bce = await get_bce_status()

    return {
        "status": "healthy",
        "circuit_breakers": breakers,
        "services": {
            "bce": bce,
        },
    }


@router.get("/events")
async def event_bus_info(
    event_type: str = Query("contact.created"),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Get event bus stream info for monitoring."""
    bus = get_event_bus()
    return await bus.get_stream_info(event_type)


# ── BCE Lookup ──


@router.get("/bce/{bce_number}")
async def bce_lookup(
    bce_number: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Look up a company in the Belgian BCE/KBO registry.

    Returns company info from cache or live API, with circuit breaker
    protection. Source field indicates where data came from:
    - api: fresh from BCE API
    - cache: from Redis cache (24h TTL)
    - fallback_cache: API down, serving stale cache
    - fallback_empty: API down, no cache available
    """
    try:
        info = await lookup_bce(bce_number)
        return info.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"BCE lookup failed: {e}")


# ── KYC Check ──


class KYCCheckRequest(BaseModel):
    contact_id: uuid.UUID
    contact_name: str = Field(..., max_length=255)
    contact_type: str = Field(..., pattern=r"^(natural|legal)$")
    bce_number: str | None = None
    address: dict | None = None
    nationality: str | None = Field(None, max_length=2)
    metadata: dict | None = None


@router.post("/kyc")
async def kyc_check(
    body: KYCCheckRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Perform KYC risk assessment on a contact.

    Checks:
    - PEP screening (name/title-based)
    - Geographic risk (FATF/EU high-risk jurisdictions)
    - BCE verification (legal entities)
    - NACE activity risk (high-risk sectors)

    Returns risk score (0-100), risk level, factors, and
    Belgian AML compliance recommendations.
    """
    result = await perform_kyc_check(
        contact_id=str(body.contact_id),
        contact_name=body.contact_name,
        contact_type=body.contact_type,
        bce_number=body.bce_number,
        address=body.address,
        nationality=body.nationality,
        metadata=body.metadata,
    )
    return result.to_dict()
