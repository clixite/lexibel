"""Calendar router — Convenience wrapper for calendar events."""

from fastapi import APIRouter, Depends, Query

from apps.api.dependencies import get_current_user

router = APIRouter(prefix="/api/v1/calendar", tags=["calendar"])


@router.get("/events")
async def get_calendar_events(
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    limit: int = Query(50, le=200),
    current_user: dict = Depends(get_current_user),
):
    """Get calendar events.

    Returns empty list for now. Outlook integration provides calendar sync.
    Frontend should use /api/v1/outlook/emails for full functionality.
    """
    return {"events": [], "total": 0}
