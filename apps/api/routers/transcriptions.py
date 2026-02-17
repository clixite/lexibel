"""Transcriptions router — Manage audio transcriptions.

Provides endpoints for listing and retrieving transcriptions from
multiple sources (Plaud, Ringover, manual uploads).
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.api.dependencies import get_current_user, get_db_session
from packages.db.models import Transcription

router = APIRouter(prefix="/api/v1/transcriptions", tags=["transcriptions"])


@router.get("")
async def get_transcriptions(
    case_id: str | None = Query(None, description="Filter by case ID"),
    source: str | None = Query(
        None, description="Filter by source (plaud, ringover, manual)"
    ),
    status_filter: str | None = Query(
        None,
        alias="status",
        description="Filter by status (pending, processing, completed, failed)",
    ),
    limit: int = Query(50, le=200, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """List transcriptions from all sources (Plaud, Ringover, manual).

    Returns transcription records with metadata. Use the detail endpoint
    to retrieve segments.

    Args:
        case_id: Optional UUID to filter by case
        source: Optional source filter (plaud, ringover, manual)
        status_filter: Optional status filter
        limit: Maximum number of results (default 50, max 200)
        offset: Pagination offset
        current_user: Authenticated user from JWT
        db: Database session with RLS applied

    Returns:
        Dictionary with transcriptions list and total count
    """
    tenant_id = current_user["tenant_id"]

    # Build query
    query = (
        select(Transcription)
        .where(Transcription.tenant_id == tenant_id)
        .order_by(Transcription.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    # Apply filters
    if case_id:
        try:
            case_uuid = uuid.UUID(case_id)
            query = query.where(Transcription.case_id == case_uuid)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid case_id format",
            )

    if source:
        query = query.where(Transcription.source == source.lower())

    if status_filter:
        query = query.where(Transcription.status == status_filter.lower())

    # Execute query
    result = await db.execute(query)
    transcriptions = result.scalars().all()

    # Format response
    return {
        "transcriptions": [
            {
                "id": str(t.id),
                "case_id": str(t.case_id) if t.case_id else None,
                "source": t.source,
                "status": t.status,
                "language": t.language,
                "audio_url": t.audio_url,
                "audio_duration_seconds": t.audio_duration_seconds,
                "full_text": t.full_text[:500] if t.full_text else None,  # Preview
                "summary": t.summary,
                "sentiment_score": float(t.sentiment_score)
                if t.sentiment_score
                else None,
                "sentiment_label": t.sentiment_label,
                "extracted_tasks": t.extracted_tasks,
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                "created_at": t.created_at.isoformat(),
                "metadata": t.metadata,
            }
            for t in transcriptions
        ],
        "total": len(transcriptions),
        "limit": limit,
        "offset": offset,
    }


@router.get("/{transcription_id}")
async def get_transcription_detail(
    transcription_id: str,
    include_segments: bool = Query(True, description="Include transcription segments"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Get detailed transcription with optional segments.

    Args:
        transcription_id: UUID of the transcription
        include_segments: Whether to include timestamped segments
        current_user: Authenticated user from JWT
        db: Database session with RLS applied

    Returns:
        Detailed transcription with segments if requested

    Raises:
        HTTPException: 404 if transcription not found
    """
    tenant_id = current_user["tenant_id"]

    # Parse UUID
    try:
        trans_uuid = uuid.UUID(transcription_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid transcription_id format",
        )

    # Build query with optional eager loading
    query = select(Transcription).where(
        Transcription.id == trans_uuid,
        Transcription.tenant_id == tenant_id,
    )

    if include_segments:
        query = query.options(selectinload(Transcription.segments))

    result = await db.execute(query)
    transcription = result.scalar_one_or_none()

    if not transcription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcription not found",
        )

    # Format response
    response = {
        "id": str(transcription.id),
        "case_id": str(transcription.case_id) if transcription.case_id else None,
        "source": transcription.source,
        "status": transcription.status,
        "language": transcription.language,
        "audio_url": transcription.audio_url,
        "audio_duration_seconds": transcription.audio_duration_seconds,
        "full_text": transcription.full_text,
        "summary": transcription.summary,
        "sentiment_score": (
            float(transcription.sentiment_score)
            if transcription.sentiment_score
            else None
        ),
        "sentiment_label": transcription.sentiment_label,
        "extracted_tasks": transcription.extracted_tasks,
        "completed_at": (
            transcription.completed_at.isoformat()
            if transcription.completed_at
            else None
        ),
        "created_at": transcription.created_at.isoformat(),
        "metadata": transcription.metadata,
    }

    if include_segments:
        response["segments"] = [
            {
                "id": str(seg.id),
                "segment_index": seg.segment_index,
                "speaker": seg.speaker,
                "start_time": float(seg.start_time),
                "end_time": float(seg.end_time),
                "text": seg.text,
                "confidence": float(seg.confidence) if seg.confidence else None,
            }
            for seg in sorted(transcription.segments, key=lambda s: s.segment_index)
        ]
        response["segments_count"] = len(transcription.segments)

    return response
