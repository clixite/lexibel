"""SSE (Server-Sent Events) service — real-time tenant-scoped notifications.

SSEManager maintains per-tenant channels. Clients subscribe via
GET /api/v1/events/stream and receive events scoped to their tenant.

Events: new_inbox_item, case_updated, time_entry_created, invoice_created,
        document_uploaded, etc.
"""

import asyncio
import json
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import AsyncGenerator


class SSEManager:
    """Manages Server-Sent Events channels per tenant."""

    def __init__(self) -> None:
        self._channels: dict[uuid.UUID, list[asyncio.Queue]] = defaultdict(list)

    async def subscribe(self, tenant_id: uuid.UUID) -> AsyncGenerator[str, None]:
        """Subscribe to events for a tenant.

        Yields SSE-formatted strings: "data: {...}\\n\\n"
        """
        queue: asyncio.Queue = asyncio.Queue()
        self._channels[tenant_id].append(queue)

        try:
            # Send initial connection event
            yield _format_sse(
                "connected",
                {
                    "tenant_id": str(tenant_id),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

            while True:
                # Wait for events with timeout to send keepalive
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield event
                except asyncio.TimeoutError:
                    # Send keepalive comment to prevent connection timeout
                    yield ": keepalive\n\n"
        finally:
            # Clean up on disconnect
            self._channels[tenant_id].remove(queue)
            if not self._channels[tenant_id]:
                del self._channels[tenant_id]

    async def publish(
        self,
        tenant_id: uuid.UUID,
        event_type: str,
        data: dict,
    ) -> int:
        """Publish an event to all subscribers of a tenant.

        Returns the number of subscribers who received the event.
        """
        if tenant_id not in self._channels:
            return 0

        message = _format_sse(event_type, data)
        delivered = 0

        for queue in self._channels[tenant_id]:
            try:
                queue.put_nowait(message)
                delivered += 1
            except asyncio.QueueFull:
                pass  # Skip slow consumers

        return delivered

    def subscriber_count(self, tenant_id: uuid.UUID) -> int:
        """Get the number of active subscribers for a tenant."""
        return len(self._channels.get(tenant_id, []))

    def total_subscribers(self) -> int:
        """Get the total number of active subscribers across all tenants."""
        return sum(len(queues) for queues in self._channels.values())


def _format_sse(event_type: str, data: dict) -> str:
    """Format an SSE message string."""
    payload = json.dumps(data, default=str)
    return f"event: {event_type}\ndata: {payload}\n\n"


# Global SSE manager instance
sse_manager = SSEManager()
