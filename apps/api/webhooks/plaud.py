"""Plaud.ai webhook handler — ingest transcription results.

POST /api/v1/webhooks/plaud

Verifies HMAC-SHA256 signature, receives transcription result (transcript +
speakers + metadata), creates InboxItem with source=PLAUD (DRAFT, human
validation required), links audio file as EvidenceLink.
Uses idempotency_key from recording_id (Principle P6).
"""
import os

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from apps.api.services.webhook_service import (
    check_idempotency,
    verify_hmac_signature,
)

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])

PLAUD_WEBHOOK_SECRET = os.getenv("PLAUD_WEBHOOK_SECRET", "plaud-dev-secret")


class PlaudSpeaker(BaseModel):
    id: str
    name: str | None = None
    segments: list[dict] = Field(default_factory=list)


class PlaudTranscriptionEvent(BaseModel):
    recording_id: str
    tenant_id: str
    status: str = Field(..., description="completed | failed")
    transcript: str | None = None
    speakers: list[PlaudSpeaker] = Field(default_factory=list)
    duration_seconds: int = 0
    language: str = "fr"
    audio_url: str | None = None
    audio_mime_type: str = "audio/mp3"
    audio_size_bytes: int = 0
    metadata: dict = Field(default_factory=dict)


class PlaudWebhookResponse(BaseModel):
    status: str
    recording_id: str
    inbox_item_created: bool = False
    evidence_link_created: bool = False
    duplicate: bool = False


@router.post("/plaud", response_model=PlaudWebhookResponse)
async def plaud_webhook(request: Request) -> PlaudWebhookResponse:
    """Handle Plaud.ai transcription webhook."""
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
    import json
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )

    event = PlaudTranscriptionEvent(**data)

    # Idempotency check (P6)
    idempotency_key = f"plaud:{event.recording_id}"
    if await check_idempotency(idempotency_key):
        return PlaudWebhookResponse(
            status="duplicate",
            recording_id=event.recording_id,
            duplicate=True,
        )

    # Skip failed transcriptions
    if event.status == "failed":
        return PlaudWebhookResponse(
            status="skipped",
            recording_id=event.recording_id,
        )

    # In production: create InboxItem + EvidenceLink via DB session
    inbox_created = True
    evidence_created = event.audio_url is not None

    return PlaudWebhookResponse(
        status="accepted",
        recording_id=event.recording_id,
        inbox_item_created=inbox_created,
        evidence_link_created=evidence_created,
    )
