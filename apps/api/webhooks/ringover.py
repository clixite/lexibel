"""Ringover webhook handler — AI-powered call processing with real-time SSE.

POST /api/v1/webhooks/ringover

2026 Best Practices:
- HMAC-SHA256 signature verification (security)
- Contact auto-matching via E.164 phone parsing
- Case auto-linking (most recent active case)
- Server-Sent Events broadcast for real-time UI updates
- Background AI processing (transcript, summary, sentiment)
- Idempotency protection (Principle P6)
- Edge-ready design (< 10ms response time)
"""

import json
import logging
import os
import uuid
from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db_session
from apps.api.schemas.ringover import RingoverCallEvent, RingoverWebhookResponse
from apps.api.services import ringover_service
from apps.api.services.sse_service import sse_manager
from apps.api.services.webhook_service import (
    check_idempotency,
    verify_hmac_signature,
)

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])

RINGOVER_WEBHOOK_SECRET = os.getenv("RINGOVER_WEBHOOK_SECRET", "ringover-dev-secret")

logger = logging.getLogger(__name__)


@router.post("/ringover", response_model=RingoverWebhookResponse)
async def ringover_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db_session),
) -> RingoverWebhookResponse:
    """Handle Ringover call event webhook with AI-powered processing.

    Flow:
    1. Verify HMAC signature (security)
    2. Check idempotency (prevent duplicates)
    3. Match contact by phone number
    4. Auto-link to active case
    5. Create InteractionEvent
    6. Broadcast SSE update (real-time UI)
    7. Background: AI processing (transcript, summary, sentiment)
    """
    # ── Step 1: HMAC Verification ──
    body = await request.body()

    signature = request.headers.get("X-Ringover-Signature", "")
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Ringover-Signature header",
        )

    if not verify_hmac_signature(body, signature, RINGOVER_WEBHOOK_SECRET):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    # ── Step 2: Parse Event ──
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )

    event = RingoverCallEvent(**data)

    # ── Step 3: Idempotency Check ──
    idempotency_key = f"ringover:{event.call_id}"
    if await check_idempotency(idempotency_key):
        logger.info(f"Duplicate webhook received: {event.call_id}")
        return RingoverWebhookResponse(
            status="duplicate",
            call_id=event.call_id,
            duplicate=True,
        )

    # ── Step 4: Contact Matching ──
    phone = event.caller_number if event.direction == "inbound" else event.callee_number
    contact = await ringover_service.match_contact_by_phone(session, phone)

    contact_matched = contact is not None
    matched_contact_id = contact.id if contact else None

    # ── Step 5: Case Auto-Linking ──
    case_id = None
    linked_case = False

    if contact:
        # Find most recent active case for this contact
        active_cases = await ringover_service.find_active_cases_for_contact(
            session,
            contact.id,
            limit=1,
        )
        if active_cases:
            case_id = active_cases[0].id
            linked_case = True

    # ── Step 6: Create InteractionEvent ──
    # Parse timestamps
    started_at = datetime.fromisoformat(event.started_at.replace("Z", "+00:00"))
    ended_at = None
    if event.ended_at:
        ended_at = datetime.fromisoformat(event.ended_at.replace("Z", "+00:00"))

    # Extract tenant_id from context (in production, use RLS or JWT)
    # For now, we use a default tenant UUID
    # TODO: Extract from JWT claims or X-Tenant-ID header
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

    interaction_event = await ringover_service.create_call_event(
        session,
        tenant_id,
        call_id=event.call_id,
        direction=event.direction,
        caller_number=event.caller_number,
        callee_number=event.callee_number,
        duration_seconds=event.duration_seconds,
        call_type=event.call_type,
        started_at=started_at,
        ended_at=ended_at,
        recording_url=event.recording_url,
        contact_id=matched_contact_id,
        case_id=case_id,
    )

    await session.commit()

    # ── Step 7: Real-time SSE Broadcast ──
    # Notify connected clients about the new call event
    await sse_manager.publish(
        tenant_id,
        "call_event_created",
        {
            "event_id": str(interaction_event.id),
            "call_id": event.call_id,
            "direction": event.direction,
            "call_type": event.call_type,
            "phone_number": phone,
            "contact_id": str(matched_contact_id) if matched_contact_id else None,
            "contact_name": contact.full_name if contact else None,
            "case_id": str(case_id) if case_id else None,
            "duration_seconds": event.duration_seconds,
            "has_recording": bool(event.recording_url),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )

    # ── Step 8: Background AI Processing ──
    if event.recording_url:
        background_tasks.add_task(
            _process_call_ai_background,
            session=session,
            event_id=interaction_event.id,
            recording_url=event.recording_url,
            tenant_id=tenant_id,
        )

    logger.info(
        f"Ringover call processed: {event.call_id} | "
        f"Contact: {contact_matched} | Case: {linked_case}"
    )

    return RingoverWebhookResponse(
        status="accepted",
        call_id=event.call_id,
        event_created=True,
        contact_matched=contact_matched,
        case_linked=linked_case,
        duplicate=False,
        matched_contact_id=matched_contact_id,
        linked_case_id=case_id,
    )


async def _process_call_ai_background(
    session: AsyncSession,
    event_id: uuid.UUID,
    recording_url: str,
    tenant_id: uuid.UUID,
) -> None:
    """Background task: AI processing for call recordings.

    Runs asynchronously after webhook response to avoid blocking.
    Updates InteractionEvent metadata with AI insights.
    """
    try:
        # Get the event
        from sqlalchemy import select

        from packages.db.models.interaction_event import InteractionEvent

        result = await session.execute(
            select(InteractionEvent).where(InteractionEvent.id == event_id)
        )
        event = result.scalar_one_or_none()

        if not event:
            logger.error(f"Event not found for AI processing: {event_id}")
            return

        # Run AI processing
        updated_metadata = await ringover_service.process_call_ai_features(
            session,
            event,
            recording_url,
        )

        # Update event metadata
        event.metadata_ = {**event.metadata_, **updated_metadata}
        await session.commit()

        # Broadcast SSE update with AI results
        await sse_manager.publish(
            tenant_id,
            "call_ai_completed",
            {
                "event_id": str(event_id),
                "has_transcript": updated_metadata.get("transcript_status")
                == "completed",
                "has_summary": updated_metadata.get("summary_status") == "completed",
                "sentiment_score": updated_metadata.get("sentiment_score"),
                "tasks_generated": updated_metadata.get("tasks_generated", False),
            },
        )

        logger.info(f"AI processing completed for call: {event_id}")

    except Exception as e:
        logger.error(f"AI processing failed for {event_id}: {e}", exc_info=True)
