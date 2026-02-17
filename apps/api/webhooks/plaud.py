"""Plaud.ai webhook handler — ingest transcription results.

POST /api/v1/webhooks/plaud

Verifies HMAC-SHA256 signature, receives transcription result (transcript +
speakers + segments), creates Transcription + TranscriptionSegments.
Optionally creates InteractionEvent if case_id is provided.
Uses idempotency_key from recording_id (Principle P6).
"""

import json
import logging
import os
import uuid
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from apps.api.services.webhook_service import (
    check_idempotency,
    verify_hmac_signature,
)
from packages.db.models import InteractionEvent, Transcription, TranscriptionSegment
from packages.db.session import async_session_factory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])

PLAUD_WEBHOOK_SECRET = os.getenv("PLAUD_WEBHOOK_SECRET", "plaud-dev-secret")


class PlaudSegment(BaseModel):
    """Individual transcription segment with timing and speaker."""

    segment_index: int
    speaker: str | None = None
    start_time: float
    end_time: float
    text: str
    confidence: float | None = None


class PlaudSpeaker(BaseModel):
    """Speaker identification metadata."""

    id: str
    name: str | None = None


class PlaudTranscriptionEvent(BaseModel):
    """Webhook payload from Plaud.ai."""

    transcription_id: str = Field(
        ..., description="Unique ID for this transcription (used for idempotency)"
    )
    tenant_id: str
    case_id: str | None = None
    audio_url: str | None = None
    text: str
    segments: list[PlaudSegment] = Field(default_factory=list)
    speakers: list[PlaudSpeaker] = Field(default_factory=list)
    duration: int = Field(0, description="Audio duration in seconds")
    language: str = "fr"
    metadata: dict = Field(default_factory=dict)


class PlaudWebhookResponse(BaseModel):
    """Response for webhook processing."""

    status: str
    transcription_id: str
    db_transcription_id: str | None = None
    interaction_event_created: bool = False
    segments_created: int = 0
    duplicate: bool = False


@router.post("/plaud", response_model=PlaudWebhookResponse)
async def plaud_webhook(request: Request) -> PlaudWebhookResponse:
    """Handle Plaud.ai transcription webhook.

    This endpoint:
    1. Verifies HMAC signature for security
    2. Checks idempotency to prevent duplicates
    3. Creates Transcription record with full_text and metadata
    4. Creates TranscriptionSegment records for each segment
    5. Optionally creates InteractionEvent if case_id is provided

    Args:
        request: FastAPI request containing webhook payload

    Returns:
        PlaudWebhookResponse with processing status

    Raises:
        HTTPException: If signature is invalid or payload is malformed
    """
    # Read raw body for HMAC verification
    body = await request.body()

    # Verify HMAC-SHA256 signature
    signature = request.headers.get("X-Plaud-Signature", "")
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Plaud-Signature header",
        )

    if not verify_hmac_signature(body, signature, PLAUD_WEBHOOK_SECRET):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    # Parse the event
    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON payload: {e}",
        )

    try:
        event = PlaudTranscriptionEvent(**data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid payload structure: {e}",
        )

    # Idempotency check (P6)
    idempotency_key = f"plaud:{event.transcription_id}"
    if await check_idempotency(idempotency_key):
        logger.info(f"Duplicate webhook received: {event.transcription_id}")
        return PlaudWebhookResponse(
            status="duplicate",
            transcription_id=event.transcription_id,
            duplicate=True,
        )

    # Process transcription in database
    try:
        async with async_session_factory() as db:
            async with db.begin():
                # Set tenant context for RLS
                from sqlalchemy import text

                await db.execute(
                    text(f"SET LOCAL app.current_tenant_id = '{event.tenant_id}'")
                )

                # Parse case_id if provided
                case_uuid = None
                if event.case_id:
                    try:
                        case_uuid = uuid.UUID(event.case_id)
                    except ValueError:
                        logger.warning(
                            f"Invalid case_id format: {event.case_id}, skipping case linkage"
                        )

                # Create Transcription record
                transcription = Transcription(
                    tenant_id=uuid.UUID(event.tenant_id),
                    case_id=case_uuid,
                    source="plaud",
                    audio_url=event.audio_url,
                    audio_duration_seconds=event.duration,
                    language=event.language,
                    status="completed",
                    full_text=event.text,
                    metadata=event.metadata or {},
                    completed_at=datetime.utcnow(),
                )
                db.add(transcription)
                await db.flush()  # Get transcription.id

                # Create TranscriptionSegment records
                segments_created = 0
                for seg in event.segments:
                    segment = TranscriptionSegment(
                        transcription_id=transcription.id,
                        segment_index=seg.segment_index,
                        start_time=Decimal(str(seg.start_time)),
                        end_time=Decimal(str(seg.end_time)),
                        text=seg.text,
                        speaker=seg.speaker,
                        confidence=Decimal(str(seg.confidence))
                        if seg.confidence
                        else None,
                    )
                    db.add(segment)
                    segments_created += 1

                # Create InteractionEvent if case_id provided
                interaction_created = False
                if case_uuid:
                    interaction = InteractionEvent(
                        tenant_id=uuid.UUID(event.tenant_id),
                        case_id=case_uuid,
                        source="PLAUD",
                        event_type="TRANSCRIPTION",
                        title=f"Plaud Transcription - {event.language.upper()}",
                        body=event.text[:1000],  # Truncate for summary
                        occurred_at=datetime.utcnow(),
                        metadata_={
                            "transcription_id": str(transcription.id),
                            "duration_seconds": event.duration,
                            "language": event.language,
                            "audio_url": event.audio_url,
                            "segments_count": len(event.segments),
                        },
                        created_by=None,  # Webhook = system event
                    )
                    db.add(interaction)
                    interaction_created = True

                await db.commit()

                logger.info(
                    f"Created Plaud transcription {transcription.id} with {segments_created} segments"
                )

                return PlaudWebhookResponse(
                    status="accepted",
                    transcription_id=event.transcription_id,
                    db_transcription_id=str(transcription.id),
                    interaction_event_created=interaction_created,
                    segments_created=segments_created,
                )

    except Exception as e:
        logger.error(f"Database error processing Plaud webhook: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process transcription: {str(e)}",
        )
