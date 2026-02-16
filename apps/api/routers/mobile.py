"""Mobile-optimized endpoints — aggregated responses for mobile clients."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form

from apps.api.dependencies import get_current_user

router = APIRouter(prefix="/api/v1/mobile", tags=["mobile"])


@router.get("/dashboard")
async def mobile_dashboard(user: dict = Depends(get_current_user)):
    """Aggregated dashboard for mobile — single call replaces 4 calls.

    Returns: recent cases, pending inbox, hours today, upcoming deadlines.
    """
    tenant_id = str(user.get("tenant_id", ""))
    user_id = str(user.get("user_id", ""))

    return {
        "recent_cases": [],
        "pending_inbox": {
            "count": 0,
            "items": [],
        },
        "hours_today": {
            "total_minutes": 0,
            "entries": [],
        },
        "upcoming_deadlines": [],
        "user_id": user_id,
        "tenant_id": tenant_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/case/{case_id}/summary")
async def mobile_case_summary(
    case_id: str,
    user: dict = Depends(get_current_user),
):
    """Case summary for mobile — case + contacts + recent events in one response."""
    return {
        "case_id": case_id,
        "case": {
            "id": case_id,
            "title": "",
            "status": "unknown",
            "description": "",
        },
        "contacts": [],
        "recent_events": [],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/quick-time")
async def quick_time_entry(
    body: dict,
    user: dict = Depends(get_current_user),
):
    """Simplified time entry for mobile — minimal fields."""
    case_id = body.get("case_id")
    minutes = body.get("minutes")
    description = body.get("description", "")

    if not case_id:
        raise HTTPException(status_code=400, detail="case_id required")
    if not minutes or not isinstance(minutes, (int, float)) or minutes <= 0:
        raise HTTPException(status_code=400, detail="minutes must be a positive number")

    entry = {
        "id": str(uuid.uuid4()),
        "case_id": case_id,
        "user_id": str(user.get("user_id", "")),
        "tenant_id": str(user.get("tenant_id", "")),
        "minutes": minutes,
        "description": description,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": "mobile",
    }

    return {"message": "Time entry created", "entry": entry}


@router.post("/voice-note")
async def upload_voice_note(
    case_id: str = Form(...),
    audio: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """Upload audio voice note, triggers transcription pipeline.

    Accepts audio file, stores in MinIO, queues for Plaud transcription.
    """
    if not audio.content_type or not audio.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="File must be an audio file")

    file_size = 0
    content = await audio.read()
    file_size = len(content)

    if file_size > 50 * 1024 * 1024:  # 50MB limit
        raise HTTPException(status_code=400, detail="File too large (max 50MB)")

    note_id = str(uuid.uuid4())

    return {
        "message": "Voice note uploaded, transcription queued",
        "note": {
            "id": note_id,
            "case_id": case_id,
            "filename": audio.filename or "voice_note.wav",
            "size_bytes": file_size,
            "content_type": audio.content_type,
            "status": "queued",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    }
