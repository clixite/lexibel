"""EventBus — lightweight event bus on Redis Streams.

Decouples the core from integration modules. The core emits domain events,
integration modules subscribe asynchronously.

Events:
- contact.created / contact.updated
- case.created / case.status_changed
- document.uploaded
- email.received / email.sent
- invoice.created / invoice.paid

Each event carries tenant_id for isolation. Consumers process
events in their own failure domain — a failing consumer never
blocks the core.

Architecture decision: Redis Streams over Kafka because:
1. Redis is already in the stack
2. Our event volume is <1000/min (law firm, not Twitter)
3. Consumer groups give us at-least-once delivery
4. Zero new infrastructure to deploy
"""

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
STREAM_PREFIX = "lexibel:events:"
CONSUMER_GROUP = "lexibel_workers"


class EventBus:
    """Publish/subscribe event bus backed by Redis Streams."""

    def __init__(self):
        self._redis = None

    async def _get_redis(self):
        if self._redis is None:
            try:
                import redis.asyncio as aioredis

                self._redis = aioredis.from_url(
                    REDIS_URL, decode_responses=True, socket_timeout=5.0
                )
            except ImportError:
                logger.warning("redis.asyncio not available — EventBus is no-op")
                return None
        return self._redis

    async def publish(
        self,
        event_type: str,
        tenant_id: str,
        payload: dict[str, Any],
        correlation_id: str | None = None,
    ) -> str | None:
        """Publish a domain event to the event bus.

        Args:
            event_type: Dotted event name (e.g. "contact.created")
            tenant_id: Tenant UUID string for isolation
            payload: Event data (must be JSON-serializable)
            correlation_id: Optional correlation ID for tracing

        Returns:
            Redis message ID or None if Redis unavailable
        """
        redis = await self._get_redis()
        if redis is None:
            logger.debug("EventBus: Redis unavailable, event [%s] dropped", event_type)
            return None

        stream = f"{STREAM_PREFIX}{event_type}"
        event_id = correlation_id or str(uuid.uuid4())

        message = {
            "event_id": event_id,
            "event_type": event_type,
            "tenant_id": tenant_id,
            "payload": json.dumps(payload, default=str),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            msg_id = await redis.xadd(stream, message, maxlen=10000)
            logger.debug(
                "EventBus: published [%s] tenant=%s id=%s",
                event_type,
                tenant_id,
                msg_id,
            )
            return msg_id
        except Exception as e:
            logger.error("EventBus: failed to publish [%s]: %s", event_type, e)
            return None

    async def ensure_consumer_group(self, event_type: str) -> None:
        """Create consumer group for an event stream if it doesn't exist."""
        redis = await self._get_redis()
        if redis is None:
            return

        stream = f"{STREAM_PREFIX}{event_type}"
        try:
            await redis.xgroup_create(stream, CONSUMER_GROUP, id="0", mkstream=True)
        except Exception:
            pass  # Group already exists

    async def consume(
        self,
        event_type: str,
        consumer_name: str,
        count: int = 10,
        block: int = 5000,
    ) -> list[dict]:
        """Consume events from a stream via consumer group.

        Args:
            event_type: Event type to consume
            consumer_name: Unique consumer name within the group
            count: Max events to read per call
            block: Block timeout in milliseconds

        Returns:
            List of parsed event dicts
        """
        redis = await self._get_redis()
        if redis is None:
            return []

        stream = f"{STREAM_PREFIX}{event_type}"
        await self.ensure_consumer_group(event_type)

        try:
            results = await redis.xreadgroup(
                CONSUMER_GROUP,
                consumer_name,
                {stream: ">"},
                count=count,
                block=block,
            )
        except Exception as e:
            logger.error("EventBus: consume error [%s]: %s", event_type, e)
            return []

        events = []
        for _stream_name, messages in results:
            for msg_id, data in messages:
                try:
                    event = {
                        "msg_id": msg_id,
                        "event_id": data.get("event_id"),
                        "event_type": data.get("event_type"),
                        "tenant_id": data.get("tenant_id"),
                        "payload": json.loads(data.get("payload", "{}")),
                        "timestamp": data.get("timestamp"),
                    }
                    events.append(event)
                except (json.JSONDecodeError, KeyError) as e:
                    logger.error("EventBus: malformed event %s: %s", msg_id, e)

        return events

    async def acknowledge(self, event_type: str, msg_id: str) -> None:
        """Acknowledge a consumed event."""
        redis = await self._get_redis()
        if redis is None:
            return

        stream = f"{STREAM_PREFIX}{event_type}"
        try:
            await redis.xack(stream, CONSUMER_GROUP, msg_id)
        except Exception as e:
            logger.error("EventBus: ack error [%s] %s: %s", event_type, msg_id, e)

    async def get_stream_info(self, event_type: str) -> dict:
        """Get stream info for monitoring."""
        redis = await self._get_redis()
        if redis is None:
            return {"error": "Redis unavailable"}

        stream = f"{STREAM_PREFIX}{event_type}"
        try:
            info = await redis.xinfo_stream(stream)
            return {
                "stream": stream,
                "length": info.get("length", 0),
                "first_entry": info.get("first-entry"),
                "last_entry": info.get("last-entry"),
            }
        except Exception:
            return {"stream": stream, "length": 0, "status": "not_created"}

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None


# ── Global singleton ──

_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Get or create the global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus
