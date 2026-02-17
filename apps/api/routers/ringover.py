"""Ringover router — call history, recordings, and real-time features.

GET    /api/v1/ringover/calls              — list recent calls (paginated)
GET    /api/v1/ringover/calls/{event_id}   — get call details with AI insights
GET    /api/v1/ringover/recordings/{id}    — stream call recording (authenticated)
POST   /api/v1/ringover/calls/{id}/summary — regenerate AI summary
GET    /api/v1/ringover/stats              — call statistics (volume, duration, sentiment)
"""

import os
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_current_tenant, get_db_session
from apps.api.schemas.ringover import CallEventDetail
from apps.api.services import ringover_service
from apps.api.services.ringover_client import RingoverClient, RingoverAPIError
from packages.db.models.contact import Contact
from packages.db.models.interaction_event import InteractionEvent

router = APIRouter(prefix="/api/v1/ringover", tags=["ringover"])


class CallListResponse(BaseModel):
    """Paginated call history response."""

    items: list[CallEventDetail]
    total: int
    page: int
    per_page: int


class CallStats(BaseModel):
    """Call statistics for dashboard widgets."""

    total_calls: int
    answered_calls: int
    missed_calls: int
    voicemails: int
    total_duration_minutes: int
    avg_duration_minutes: float
    avg_sentiment_score: Optional[float]
    calls_with_recordings: int
    calls_with_transcripts: int


@router.get("/calls", response_model=CallListResponse)
async def list_calls(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    direction: Optional[str] = Query(None, pattern="^(inbound|outbound)$"),
    call_type: Optional[str] = Query(None, pattern="^(answered|missed|voicemail)$"),
    contact_id: Optional[uuid.UUID] = Query(None),
    case_id: Optional[uuid.UUID] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    session: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> CallListResponse:
    """List call history with filters and pagination.

    Fetches from Ringover API v2 if configured, then enriches with DB data.
    Falls back to DB-only if API unavailable.

    Supports filtering by:
    - Direction (inbound/outbound)
    - Call type (answered/missed/voicemail)
    - Contact
    - Case
    - Date range
    """
    items = []
    total = 0

    # Try Ringover API first
    if os.getenv("RINGOVER_API_KEY"):
        try:
            async with RingoverClient() as client:
                # Fetch from API
                api_response = await client.list_calls(
                    page=page,
                    per_page=per_page,
                    date_from=date_from,
                    date_to=date_to,
                    direction=direction,
                    call_type=call_type,
                )

                # Enrich API data with DB information
                for call in api_response.calls:
                    # Find matching InteractionEvent by call_id
                    event_query = select(InteractionEvent).where(
                        and_(
                            InteractionEvent.source == "RINGOVER",
                            InteractionEvent.metadata_["call_id"].astext == call.id,
                        )
                    )
                    event_result = await session.execute(event_query)
                    event = event_result.scalar_one_or_none()

                    # Get metadata from event or build from API data
                    metadata = event.metadata_ if event else {}
                    if not metadata:
                        metadata = {
                            "call_id": call.id,
                            "direction": call.direction,
                            "caller_number": call.caller_number,
                            "callee_number": call.callee_number,
                            "duration_seconds": call.duration_seconds,
                            "call_type": call.call_type,
                            "recording_url": None,
                            "started_at": call.started_at,
                            "ended_at": call.ended_at,
                        }

                    # Get contact details
                    contact_id_from_event = (
                        event.metadata_.get("contact_id") if event else None
                    )
                    contact = None
                    if contact_id_from_event:
                        contact_result = await session.execute(
                            select(Contact).where(
                                Contact.id == uuid.UUID(contact_id_from_event)
                            )
                        )
                        contact = contact_result.scalar_one_or_none()

                    # Extract insights
                    insights = ringover_service.extract_call_insights(metadata)

                    # Apply additional filters (contact_id, case_id) that aren't in API
                    if contact_id and (not contact or contact.id != contact_id):
                        continue
                    if case_id and (not event or event.case_id != case_id):
                        continue

                    items.append(
                        CallEventDetail(
                            id=event.id
                            if event
                            else uuid.uuid4(),  # Temp ID if not in DB
                            case_id=event.case_id if event else None,
                            contact_id=uuid.UUID(contact_id_from_event)
                            if contact_id_from_event
                            else None,
                            contact_name=contact.full_name if contact else None,
                            direction=call.direction,
                            call_type=call.call_type,
                            duration_formatted=ringover_service.format_call_duration(
                                call.duration_seconds
                            ),
                            phone_number=call.caller_number,
                            occurred_at=datetime.fromisoformat(
                                call.started_at.replace("Z", "+00:00")
                            ),
                            has_recording=call.recording_available,
                            has_transcript=metadata.get("transcript_status")
                            == "completed",
                            has_summary=metadata.get("summary_status") == "completed",
                            sentiment=ringover_service._get_sentiment_label(
                                metadata.get("sentiment_score")
                            ),
                            recording_url=metadata.get("recording_url"),
                            transcript=metadata.get("transcript"),
                            ai_summary=metadata.get("ai_summary"),
                            tasks_count=len(metadata.get("extracted_tasks", [])),
                        )
                    )

                total = api_response.total
                return CallListResponse(
                    items=items,
                    total=total,
                    page=page,
                    per_page=per_page,
                )

        except RingoverAPIError as e:
            # Log and fallback to DB
            print(f"Ringover API error, falling back to DB: {e}")

    # Fallback: DB-only query
    query = select(InteractionEvent).where(
        and_(
            InteractionEvent.source == "RINGOVER",
            InteractionEvent.event_type == "CALL",
        )
    )

    # Apply filters
    if direction:
        query = query.where(InteractionEvent.metadata_["direction"].astext == direction)

    if call_type:
        query = query.where(InteractionEvent.metadata_["call_type"].astext == call_type)

    if contact_id:
        query = query.where(
            InteractionEvent.metadata_["contact_id"].astext == str(contact_id)
        )

    if case_id:
        query = query.where(InteractionEvent.case_id == case_id)

    if date_from:
        query = query.where(InteractionEvent.occurred_at >= date_from)

    if date_to:
        query = query.where(InteractionEvent.occurred_at <= date_to)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar_one()

    # Paginate
    query = query.order_by(InteractionEvent.occurred_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await session.execute(query)
    events = list(result.scalars().all())

    # Convert to CallEventDetail
    items = []
    for event in events:
        metadata = event.metadata_ or {}

        # Get contact details
        contact_id_str = metadata.get("contact_id")
        contact = None
        if contact_id_str:
            contact_result = await session.execute(
                select(Contact).where(Contact.id == uuid.UUID(contact_id_str))
            )
            contact = contact_result.scalar_one_or_none()

        # Extract insights
        insights = ringover_service.extract_call_insights(metadata)

        items.append(
            CallEventDetail(
                id=event.id,
                case_id=event.case_id,
                contact_id=uuid.UUID(contact_id_str) if contact_id_str else None,
                contact_name=contact.full_name if contact else None,
                direction=metadata.get("direction", "inbound"),
                call_type=metadata.get("call_type", "answered"),
                duration_formatted=insights["duration_formatted"],
                phone_number=metadata.get("caller_number", ""),
                occurred_at=event.occurred_at,
                has_recording=insights["has_recording"],
                has_transcript=insights["has_transcript"],
                has_summary=insights["has_summary"],
                sentiment=insights["sentiment"],
                recording_url=metadata.get("recording_url"),
                transcript=metadata.get("transcript"),
                ai_summary=metadata.get("ai_summary"),
                tasks_count=insights["tasks_count"],
            )
        )

    return CallListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/calls/{event_id}", response_model=CallEventDetail)
async def get_call_details(
    event_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> CallEventDetail:
    """Get detailed call information including AI insights.

    Fetches fresh data from Ringover API if available, then enriches with DB data.

    Returns:
    - Call metadata (duration, direction, etc.)
    - Contact information
    - Case linkage
    - AI transcript (if available)
    - AI summary (if available)
    - Sentiment analysis
    - Extracted tasks
    """
    # Get local event first
    result = await session.execute(
        select(InteractionEvent).where(
            and_(
                InteractionEvent.id == event_id,
                InteractionEvent.source == "RINGOVER",
            )
        )
    )
    event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call event not found",
        )

    metadata = event.metadata_ or {}
    call_id = metadata.get("call_id")

    # Try to fetch fresh data from Ringover API
    if call_id and os.getenv("RINGOVER_API_KEY"):
        try:
            async with RingoverClient() as client:
                api_call = await client.get_call(call_id)

                # Update metadata with fresh API data
                metadata.update(
                    {
                        "direction": api_call.direction,
                        "caller_number": api_call.caller_number,
                        "callee_number": api_call.callee_number,
                        "duration_seconds": api_call.duration_seconds,
                        "call_type": api_call.call_type,
                        "started_at": api_call.started_at,
                        "ended_at": api_call.ended_at,
                    }
                )

                # Fetch recording URL if available
                if api_call.recording_available:
                    try:
                        recording = await client.get_recording(call_id)
                        metadata["recording_url"] = recording.url
                    except RingoverAPIError:
                        pass  # Recording fetch failed, keep existing URL

        except RingoverAPIError as e:
            # Log but continue with DB data
            print(f"Failed to fetch call details from Ringover API: {e}")

    # Get contact details
    contact_id_str = metadata.get("contact_id")
    contact = None
    if contact_id_str:
        contact_result = await session.execute(
            select(Contact).where(Contact.id == uuid.UUID(contact_id_str))
        )
        contact = contact_result.scalar_one_or_none()

    # Extract insights
    insights = ringover_service.extract_call_insights(metadata)

    return CallEventDetail(
        id=event.id,
        case_id=event.case_id,
        contact_id=uuid.UUID(contact_id_str) if contact_id_str else None,
        contact_name=contact.full_name if contact else None,
        direction=metadata.get("direction", "inbound"),
        call_type=metadata.get("call_type", "answered"),
        duration_formatted=insights["duration_formatted"],
        phone_number=metadata.get("caller_number", ""),
        occurred_at=event.occurred_at,
        has_recording=insights["has_recording"],
        has_transcript=insights["has_transcript"],
        has_summary=insights["has_summary"],
        sentiment=insights["sentiment"],
        recording_url=metadata.get("recording_url"),
        transcript=metadata.get("transcript"),
        ai_summary=metadata.get("ai_summary"),
        tasks_count=insights["tasks_count"],
    )


@router.get("/stats", response_model=CallStats)
async def get_call_stats(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    case_id: Optional[uuid.UUID] = Query(None, description="Filter by case"),
    session: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> CallStats:
    """Get call statistics for dashboard widgets.

    Calculates:
    - Total calls by type (answered/missed/voicemail)
    - Total and average duration
    - Average sentiment score
    - Recording/transcript availability
    """
    # Date range
    date_from = datetime.utcnow() - timedelta(days=days)

    # Base query
    query = select(InteractionEvent).where(
        and_(
            InteractionEvent.source == "RINGOVER",
            InteractionEvent.event_type == "CALL",
            InteractionEvent.occurred_at >= date_from,
        )
    )

    if case_id:
        query = query.where(InteractionEvent.case_id == case_id)

    result = await session.execute(query)
    events = list(result.scalars().all())

    # Compute stats
    total_calls = len(events)
    answered = sum(1 for e in events if e.metadata_.get("call_type") == "answered")
    missed = sum(1 for e in events if e.metadata_.get("call_type") == "missed")
    voicemails = sum(1 for e in events if e.metadata_.get("call_type") == "voicemail")

    total_duration = sum(e.metadata_.get("duration_seconds", 0) for e in events)
    avg_duration = (total_duration / total_calls) if total_calls > 0 else 0.0

    # Sentiment analysis
    sentiment_scores = [
        e.metadata_.get("sentiment_score")
        for e in events
        if e.metadata_.get("sentiment_score") is not None
    ]
    avg_sentiment = (
        sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else None
    )

    # Recording/transcript stats
    with_recordings = sum(1 for e in events if e.metadata_.get("recording_url"))
    with_transcripts = sum(
        1 for e in events if e.metadata_.get("transcript_status") == "completed"
    )

    return CallStats(
        total_calls=total_calls,
        answered_calls=answered,
        missed_calls=missed,
        voicemails=voicemails,
        total_duration_minutes=total_duration // 60,
        avg_duration_minutes=avg_duration / 60,
        avg_sentiment_score=avg_sentiment,
        calls_with_recordings=with_recordings,
        calls_with_transcripts=with_transcripts,
    )
