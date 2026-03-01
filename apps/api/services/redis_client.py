"""Shared async Redis client singleton with graceful degradation.

Provides a single connection pool reused across rate limiting,
idempotency, token revocation, and MFA token consumption.
Returns None if REDIS_URL is not set (dev fallback to in-memory).
"""

import logging
import os

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

_redis_client: aioredis.Redis | None = None
_initialized: bool = False


async def get_redis() -> aioredis.Redis | None:
    """Get the shared async Redis client. Returns None if unavailable."""
    global _redis_client, _initialized
    if _initialized:
        return _redis_client
    _initialized = True
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        logger.warning("REDIS_URL not set; falling back to in-memory stores")
        return None
    try:
        _redis_client = aioredis.from_url(redis_url, decode_responses=True)
        await _redis_client.ping()
        logger.info("Redis connected: %s", redis_url.split("@")[-1])
        return _redis_client
    except Exception as e:
        logger.warning("Redis unavailable, falling back to in-memory: %s", e)
        _redis_client = None
        return None


async def close_redis() -> None:
    """Close Redis connection (call during app shutdown)."""
    global _redis_client, _initialized
    if _redis_client:
        await _redis_client.aclose()
    _redis_client = None
    _initialized = False


def reset_redis_for_testing() -> None:
    """Reset the module state (for test isolation)."""
    global _redis_client, _initialized
    _redis_client = None
    _initialized = False
