"""SSE events router — real-time event streaming.

GET /api/v1/events/stream — Server-Sent Events endpoint (requires auth)
"""
import uuid

from fastapi import APIRouter, Depends
from starlette.responses import StreamingResponse

from apps.api.dependencies import get_current_tenant
from apps.api.services.sse_service import sse_manager

router = APIRouter(prefix="/api/v1/events", tags=["events"])


@router.get("/stream")
async def event_stream(
    tenant_id: uuid.UUID = Depends(get_current_tenant),
) -> StreamingResponse:
    """Stream tenant-scoped events via Server-Sent Events.

    Requires JWT authentication. Events are scoped to the caller's tenant.
    Sends keepalive comments every 30 seconds to prevent timeouts.
    """
    return StreamingResponse(
        sse_manager.subscribe(tenant_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
