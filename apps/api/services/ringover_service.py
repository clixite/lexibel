"""Ringover service — AI-powered call processing and auto-matching.

Handles:
- Contact matching by phone (E.164)
- Auto-linking to active cases
- Recording download and storage
- AI-powered call transcription and summary
- Sentiment analysis
- Auto-task generation from calls
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.models.case import Case
from packages.db.models.case_contact import CaseContact
from packages.db.models.contact import Contact
from packages.db.models.interaction_event import InteractionEvent
from apps.api.services.webhook_service import parse_e164


async def match_contact_by_phone(
    session: AsyncSession,
    phone: str,
) -> Contact | None:
    """Match a contact by phone number (E.164 exact match).

    RLS ensures tenant isolation.
    """
    normalized = parse_e164(phone)
    if normalized is None:
        return None

    result = await session.execute(
        select(Contact).where(Contact.phone_e164 == normalized)
    )
    return result.scalar_one_or_none()


async def find_active_cases_for_contact(
    session: AsyncSession,
    contact_id: uuid.UUID,
    limit: int = 5,
) -> list[Case]:
    """Find active cases linked to a contact.

    Returns cases ordered by most recently updated (opened_at desc).
    Useful for auto-linking incoming calls to the most relevant case.
    """
    result = await session.execute(
        select(Case)
        .join(CaseContact, Case.id == CaseContact.case_id)
        .where(
            and_(
                CaseContact.contact_id == contact_id,
                Case.status.in_(["open", "in_progress"]),
            )
        )
        .order_by(Case.opened_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def create_call_event(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    call_id: str,
    direction: str,
    caller_number: str,
    callee_number: str,
    duration_seconds: int,
    call_type: str,
    started_at: datetime,
    ended_at: Optional[datetime] = None,
    recording_url: Optional[str] = None,
    contact_id: Optional[uuid.UUID] = None,
    case_id: Optional[uuid.UUID] = None,
) -> InteractionEvent:
    """Create an InteractionEvent for a Ringover call.

    Stores call metadata including:
    - Call direction (inbound/outbound)
    - Duration
    - Recording URL (if available)
    - Contact and case linkage
    - Call type (answered/missed/voicemail)
    """
    # Build event title based on call context
    direction_label = "📞 Appel entrant" if direction == "inbound" else "📞 Appel sortant"

    if call_type == "missed":
        direction_label = "📵 Appel manqué"
    elif call_type == "voicemail":
        direction_label = "🎙️ Message vocal"

    phone = caller_number if direction == "inbound" else callee_number
    title = f"{direction_label} - {phone}"

    # Build body with call details
    duration_min = duration_seconds // 60
    duration_sec = duration_seconds % 60

    body_parts = []
    if call_type == "answered":
        body_parts.append(f"Durée: {duration_min}m {duration_sec}s")

    if recording_url:
        body_parts.append("Enregistrement disponible")

    body = " | ".join(body_parts) if body_parts else "Appel non répondu"

    # Metadata for advanced features
    metadata = {
        "call_id": call_id,
        "direction": direction,
        "caller_number": caller_number,
        "callee_number": callee_number,
        "duration_seconds": duration_seconds,
        "call_type": call_type,
        "recording_url": recording_url,
        "started_at": started_at.isoformat(),
        "ended_at": ended_at.isoformat() if ended_at else None,
        "contact_id": str(contact_id) if contact_id else None,
        # AI processing flags (updated later by background tasks)
        "transcript_status": "pending" if recording_url else "unavailable",
        "summary_status": "pending" if recording_url else "unavailable",
        "sentiment_score": None,  # -1 to 1 (negative to positive)
        "tasks_generated": False,
    }

    event = InteractionEvent(
        tenant_id=tenant_id,
        case_id=case_id,
        source="RINGOVER",
        event_type="CALL",
        title=title,
        body=body,
        occurred_at=started_at,
        metadata_=metadata,
        created_by=None,  # Webhook-created, no user
    )

    session.add(event)
    await session.flush()
    await session.refresh(event)

    return event


async def process_call_ai_features(
    session: AsyncSession,
    event: InteractionEvent,
    recording_url: str,
) -> dict:
    """Background task: AI-powered call processing.

    Features:
    1. Transcription using Whisper API
    2. Summarization using Claude
    3. Sentiment analysis
    4. Auto-task generation

    Returns updated metadata dict.
    """
    # TODO: Implement in BRAIN 2 (AI Agent)
    # This is a placeholder for the AI processing pipeline

    metadata = event.metadata_ or {}

    # Step 1: Download recording
    # recording_path = await download_recording(recording_url)

    # Step 2: Transcribe with Whisper
    # transcript = await transcribe_audio(recording_path)
    # metadata["transcript"] = transcript
    # metadata["transcript_status"] = "completed"

    # Step 3: Generate summary with Claude
    # summary = await llm_gateway.summarize_call(transcript)
    # metadata["ai_summary"] = summary
    # metadata["summary_status"] = "completed"

    # Step 4: Sentiment analysis
    # sentiment = await analyze_sentiment(transcript)
    # metadata["sentiment_score"] = sentiment.score
    # metadata["sentiment_label"] = sentiment.label  # negative/neutral/positive

    # Step 5: Extract action items
    # tasks = await extract_tasks(transcript)
    # if tasks:
    #     for task in tasks:
    #         await create_task_from_ai(session, event.case_id, task)
    #     metadata["tasks_generated"] = True

    return metadata


def format_call_duration(seconds: int) -> str:
    """Format call duration for display.

    Examples:
        45 -> "45s"
        90 -> "1m 30s"
        3600 -> "1h 0m"
    """
    if seconds < 60:
        return f"{seconds}s"

    minutes = seconds // 60
    remaining_seconds = seconds % 60

    if minutes < 60:
        return f"{minutes}m {remaining_seconds}s"

    hours = minutes // 60
    remaining_minutes = minutes % 60
    return f"{hours}h {remaining_minutes}m"


def extract_call_insights(metadata: dict) -> dict:
    """Extract key insights from call metadata for frontend display.

    Returns:
        - duration_formatted: "2m 34s"
        - has_recording: bool
        - has_transcript: bool
        - has_summary: bool
        - sentiment: "positive" | "neutral" | "negative" | None
        - tasks_count: int
    """
    duration = metadata.get("duration_seconds", 0)

    return {
        "duration_formatted": format_call_duration(duration),
        "has_recording": bool(metadata.get("recording_url")),
        "has_transcript": metadata.get("transcript_status") == "completed",
        "has_summary": metadata.get("summary_status") == "completed",
        "sentiment": _get_sentiment_label(metadata.get("sentiment_score")),
        "tasks_count": len(metadata.get("extracted_tasks", [])),
    }


def _get_sentiment_label(score: float | None) -> str | None:
    """Convert sentiment score to label.

    -1 to -0.3: negative
    -0.3 to 0.3: neutral
    0.3 to 1: positive
    """
    if score is None:
        return None

    if score < -0.3:
        return "negative"
    elif score > 0.3:
        return "positive"
    else:
        return "neutral"
