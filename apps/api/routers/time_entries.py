"""Time entries router — CRUD + approval workflow.

GET    /api/v1/time-entries            — list (filters: case, user, date, status)
POST   /api/v1/time-entries            — create
PATCH  /api/v1/time-entries/{id}       — update (draft only)
POST   /api/v1/time-entries/{id}/submit  — submit for approval
POST   /api/v1/time-entries/{id}/approve — approve (partner)
"""
import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_current_tenant, get_current_user, get_db_session
from apps.api.schemas.billing import (
    TimeEntryCreate,
    TimeEntryListResponse,
    TimeEntryResponse,
    TimeEntryUpdate,
)
from apps.api.services import time_service

router = APIRouter(prefix="/api/v1/time-entries", tags=["time-entries"])


@router.get("", response_model=TimeEntryListResponse)
async def list_time_entries(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    case_id: Optional[uuid.UUID] = Query(None),
    user_id: Optional[uuid.UUID] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    session: AsyncSession = Depends(get_db_session),
) -> TimeEntryListResponse:
    items, total = await time_service.list_time_entries(
        session,
        page=page,
        per_page=per_page,
        case_id=case_id,
        user_id=user_id,
        status=status_filter,
        date_from=date_from,
        date_to=date_to,
    )
    return TimeEntryListResponse(
        items=[TimeEntryResponse.model_validate(e) for e in items],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.post("", response_model=TimeEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_time_entry(
    body: TimeEntryCreate,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> TimeEntryResponse:
    entry = await time_service.create_time_entry(
        session,
        tenant_id,
        user["user_id"],
        case_id=body.case_id,
        description=body.description,
        duration_minutes=body.duration_minutes,
        entry_date=body.date,
        billable=body.billable,
        rounding_rule=body.rounding_rule,
        source=body.source,
        hourly_rate_cents=body.hourly_rate_cents,
    )
    return TimeEntryResponse.model_validate(entry)


@router.patch("/{entry_id}", response_model=TimeEntryResponse)
async def update_time_entry(
    entry_id: uuid.UUID,
    body: TimeEntryUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> TimeEntryResponse:
    update_data = body.model_dump(exclude_unset=True)
    entry = await time_service.update_time_entry(session, entry_id, **update_data)
    if entry is None:
        raise HTTPException(status_code=404, detail="Time entry not found")
    if entry.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only draft entries can be updated",
        )
    return TimeEntryResponse.model_validate(entry)


@router.post("/{entry_id}/submit", response_model=TimeEntryResponse)
async def submit_time_entry(
    entry_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> TimeEntryResponse:
    entry = await time_service.submit_time_entry(session, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Time entry not found")
    if entry.status != "submitted":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot submit entry in {entry.status} status",
        )
    return TimeEntryResponse.model_validate(entry)


@router.post("/{entry_id}/approve", response_model=TimeEntryResponse)
async def approve_time_entry(
    entry_id: uuid.UUID,
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> TimeEntryResponse:
    entry = await time_service.approve_time_entry(
        session, entry_id, approved_by=user["user_id"]
    )
    if entry is None:
        raise HTTPException(status_code=404, detail="Time entry not found")
    if entry.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot approve entry in {entry.status} status",
        )
    return TimeEntryResponse.model_validate(entry)
