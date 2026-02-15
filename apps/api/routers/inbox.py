"""Inbox router — human-in-the-loop queue for unvalidated items.

GET    /api/v1/inbox                     — list inbox items (paginated)
POST   /api/v1/inbox/{id}/validate       — validate → create InteractionEvent
POST   /api/v1/inbox/{id}/refuse         — refuse item
POST   /api/v1/inbox/{id}/create-case    — create case from inbox item
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_current_user, get_db_session
from apps.api.schemas.inbox import (
    InboxItemResponse,
    InboxListResponse,
    InboxValidateRequest,
)
from apps.api.services import inbox_service

router = APIRouter(prefix="/api/v1/inbox", tags=["inbox"])


class CreateCaseFromInboxRequest(BaseModel):
    reference: str = Field(..., max_length=50)
    title: str = Field(..., max_length=500)
    matter_type: str = Field(..., max_length=100)
    responsible_user_id: uuid.UUID


@router.get("", response_model=InboxListResponse)
async def list_inbox(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    session: AsyncSession = Depends(get_db_session),
) -> InboxListResponse:
    items, total = await inbox_service.list_inbox(
        session, page=page, per_page=per_page, status=status_filter
    )
    return InboxListResponse(
        items=[InboxItemResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.post("/{item_id}/validate", response_model=InboxItemResponse)
async def validate_inbox_item(
    item_id: uuid.UUID,
    body: InboxValidateRequest,
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> InboxItemResponse:
    item, event = await inbox_service.validate_inbox_item(
        session,
        item_id,
        case_id=body.case_id,
        event_type=body.event_type,
        title=body.title,
        body=body.body,
        validated_by=user["user_id"],
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Inbox item not found")
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Item already {item.status}",
        )
    return InboxItemResponse.model_validate(item)


@router.post("/{item_id}/refuse", response_model=InboxItemResponse)
async def refuse_inbox_item(
    item_id: uuid.UUID,
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> InboxItemResponse:
    item = await inbox_service.refuse_inbox_item(
        session, item_id, validated_by=user["user_id"]
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Inbox item not found")
    return InboxItemResponse.model_validate(item)


@router.post("/{item_id}/create-case", response_model=InboxItemResponse)
async def create_case_from_inbox(
    item_id: uuid.UUID,
    body: CreateCaseFromInboxRequest,
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> InboxItemResponse:
    item, case, event = await inbox_service.create_case_from_inbox(
        session,
        item_id,
        reference=body.reference,
        title=body.title,
        matter_type=body.matter_type,
        responsible_user_id=body.responsible_user_id,
        validated_by=user["user_id"],
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Inbox item not found")
    if case is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Item already {item.status}",
        )
    return InboxItemResponse.model_validate(item)
