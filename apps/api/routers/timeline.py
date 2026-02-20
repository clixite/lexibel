"""Timeline router — case timeline and event management.

GET    /api/v1/cases/{case_id}/timeline  — paginated timeline for a case
POST   /api/v1/cases/{case_id}/events    — create event on a case
GET    /api/v1/events/{id}               — get event with evidence links
"""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_current_tenant, get_current_user, get_db_session
from apps.api.schemas.timeline import (
    EvidenceLinkResponse,
    InteractionEventCreate,
    InteractionEventResponse,
    TimelineResponse,
)
from apps.api.services import timeline_service

router = APIRouter(prefix="/api/v1", tags=["timeline"])


@router.get("/cases/{case_id}/timeline", response_model=TimelineResponse)
async def get_timeline(
    case_id: uuid.UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    source: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    session: AsyncSession = Depends(get_db_session),
) -> TimelineResponse:
    items, total = await timeline_service.list_by_case(
        session,
        case_id,
        page=page,
        per_page=per_page,
        source=source,
        event_type=event_type,
        date_from=date_from,
        date_to=date_to,
    )
    return TimelineResponse(
        items=[InteractionEventResponse.model_validate(e) for e in items],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.post(
    "/cases/{case_id}/events",
    response_model=InteractionEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_event(
    case_id: uuid.UUID,
    body: InteractionEventCreate,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> InteractionEventResponse:
    event = await timeline_service.create_event(
        session,
        tenant_id,
        case_id=case_id,
        source=body.source,
        event_type=body.event_type,
        title=body.title,
        body=body.body,
        occurred_at=body.occurred_at,
        metadata=body.metadata,
        created_by=user["user_id"],
    )
    return InteractionEventResponse.model_validate(event)


@router.patch("/events/{event_id}", response_model=InteractionEventResponse)
async def update_event(
    event_id: uuid.UUID,
    body: InteractionEventCreate,
    session: AsyncSession = Depends(get_db_session),
) -> InteractionEventResponse:
    """Update an existing event."""
    event = await timeline_service.update_event(
        session,
        event_id,
        title=body.title,
        body=body.body,
        event_type=body.event_type,
        metadata=body.metadata,
    )
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return InteractionEventResponse.model_validate(event)


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """Delete an event."""
    deleted = await timeline_service.delete_event(session, event_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Event not found")
    await session.commit()


@router.get("/events/{event_id}", response_model=InteractionEventResponse)
async def get_event(
    event_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> InteractionEventResponse:
    event, links = await timeline_service.get_event_with_evidence(session, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    resp = InteractionEventResponse.model_validate(event)
    resp.evidence_links = [EvidenceLinkResponse.model_validate(link) for link in links]
    return resp
