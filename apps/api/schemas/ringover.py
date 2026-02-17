"""Pydantic schemas for Ringover webhook integration."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class RingoverCallEvent(BaseModel):
    """Ringover webhook call event payload.

    Received from Ringover when a call event occurs.
    """

    call_id: str = Field(..., description="Unique call identifier from Ringover")
    tenant_id: str = Field(..., description="Ringover tenant/account ID")
    call_type: str = Field(
        ...,
        pattern="^(answered|missed|voicemail)$",
        description="Call outcome type",
    )
    caller_number: str = Field(..., description="Caller phone number")
    callee_number: str = Field(..., description="Callee phone number")
    direction: str = Field(
        "inbound",
        pattern="^(inbound|outbound)$",
        description="Call direction",
    )
    duration_seconds: int = Field(0, ge=0, description="Call duration in seconds")
    started_at: str = Field(..., description="ISO 8601 timestamp when call started")
    ended_at: Optional[str] = Field(None, description="ISO 8601 timestamp when call ended")
    recording_url: Optional[str] = Field(None, description="URL to call recording (if available)")
    user_id: Optional[str] = Field(None, description="Ringover user ID who handled the call")
    metadata: dict = Field(default_factory=dict, description="Additional Ringover metadata")


class RingoverWebhookResponse(BaseModel):
    """Response returned to Ringover after webhook processing."""

    status: str = Field(..., description="Processing status: accepted | duplicate | error")
    call_id: str = Field(..., description="Ringover call ID")
    event_created: bool = Field(False, description="Whether an InteractionEvent was created")
    contact_matched: bool = Field(False, description="Whether a contact was matched")
    case_linked: bool = Field(False, description="Whether the call was linked to a case")
    duplicate: bool = Field(False, description="Whether this was a duplicate webhook")
    matched_contact_id: Optional[uuid.UUID] = Field(
        None,
        description="ID of matched contact (if found)",
    )
    linked_case_id: Optional[uuid.UUID] = Field(
        None,
        description="ID of linked case (if found)",
    )


class CallEventDetail(BaseModel):
    """Detailed call event information for frontend display."""

    id: uuid.UUID
    case_id: Optional[uuid.UUID]
    contact_id: Optional[uuid.UUID]
    contact_name: Optional[str]
    direction: str
    call_type: str
    duration_formatted: str
    phone_number: str
    occurred_at: datetime
    has_recording: bool
    has_transcript: bool
    has_summary: bool
    sentiment: Optional[str]  # positive | neutral | negative
    recording_url: Optional[str]
    transcript: Optional[str]
    ai_summary: Optional[str]
    tasks_count: int


class CallStreamingUpdate(BaseModel):
    """Real-time SSE event for ongoing call updates.

    Sent via Server-Sent Events to update frontend in real-time.
    """

    event_type: str = Field(..., description="call_started | call_ended | call_updated")
    call_id: str
    tenant_id: uuid.UUID
    event_id: Optional[uuid.UUID] = Field(None, description="InteractionEvent ID (once created)")
    contact_name: Optional[str]
    phone_number: str
    direction: str
    status: str = Field(..., description="ringing | in_progress | ended | missed")
    duration_seconds: int = 0


class CallTranscriptChunk(BaseModel):
    """Streaming transcript chunk for real-time call transcription.

    Enables live transcription display during active calls.
    """

    call_id: str
    chunk_index: int
    speaker: str = Field(..., description="agent | client | unknown")
    text: str
    timestamp_ms: int = Field(..., description="Milliseconds from call start")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Transcription confidence")
