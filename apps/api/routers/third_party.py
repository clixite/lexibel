"""Third-party account router — append-only ledger per case.

GET    /api/v1/cases/{case_id}/third-party          — list entries
POST   /api/v1/cases/{case_id}/third-party          — create entry
GET    /api/v1/cases/{case_id}/third-party/balance   — get balance
"""
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_current_tenant, get_current_user, get_db_session
from apps.api.schemas.billing import (
    ThirdPartyBalanceResponse,
    ThirdPartyEntryCreate,
    ThirdPartyEntryResponse,
    ThirdPartyListResponse,
)
from apps.api.services import third_party_service

router = APIRouter(prefix="/api/v1/cases", tags=["third-party"])


@router.get("/{case_id}/third-party", response_model=ThirdPartyListResponse)
async def list_third_party_entries(
    case_id: uuid.UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
) -> ThirdPartyListResponse:
    items, total = await third_party_service.list_by_case(
        session, case_id, page=page, per_page=per_page
    )
    return ThirdPartyListResponse(
        items=[ThirdPartyEntryResponse.model_validate(e) for e in items],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.post(
    "/{case_id}/third-party",
    response_model=ThirdPartyEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_third_party_entry(
    case_id: uuid.UUID,
    body: ThirdPartyEntryCreate,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ThirdPartyEntryResponse:
    entry = await third_party_service.create_entry(
        session,
        tenant_id,
        case_id=case_id,
        entry_type=body.entry_type,
        amount_cents=body.amount_cents,
        description=body.description,
        reference=body.reference,
        entry_date=body.entry_date,
        created_by=user["user_id"],
    )
    return ThirdPartyEntryResponse.model_validate(entry)


@router.get("/{case_id}/third-party/balance", response_model=ThirdPartyBalanceResponse)
async def get_third_party_balance(
    case_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> ThirdPartyBalanceResponse:
    result = await third_party_service.calculate_balance(session, case_id)
    return ThirdPartyBalanceResponse(**result)
