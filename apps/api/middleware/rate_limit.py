"""Rate limiting middleware — per-user rate limiting.

Default: 100 req/min. Configurable per role.
Uses Redis sorted sets in production, in-memory fallback for dev/testing.
Returns 429 with Retry-After header when exceeded.
"""

import logging
import os
import time
from collections import defaultdict

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

from apps.api.services.redis_client import get_redis

logger = logging.getLogger(__name__)

# Rate limits per role (requests per minute)
ROLE_LIMITS: dict[str, int] = {
    "super_admin": 200,
    "admin": 150,
    "lawyer": 100,
    "paralegal": 100,
    "secretary": 80,
    "accountant": 80,
    "junior": 60,
}

DEFAULT_LIMIT = int(os.getenv("RATE_LIMIT_PER_MINUTE", "100"))
WINDOW_SECONDS = 60

# Paths excluded from rate limiting
_EXEMPT_PATHS = frozenset(
    {
        "/api/v1/health",
        "/api/v1/docs",
        "/api/v1/openapi.json",
    }
)

# In-memory rate limit store (fallback when Redis unavailable)
_rate_store: dict[str, list[float]] = defaultdict(list)


def reset_rate_store() -> None:
    """Reset the in-memory rate limit store (for testing)."""
    _rate_store.clear()


async def _check_redis_rate(
    key: str, limit: int, window: int
) -> tuple[bool, int, int] | None:
    """Check rate limit using Redis sorted sets.

    Returns (exceeded, remaining, retry_after) or None if Redis unavailable.
    """
    redis = await get_redis()
    if redis is None:
        return None
    try:
        now = time.time()
        redis_key = f"ratelimit:{key}"
        pipe = redis.pipeline()
        pipe.zremrangebyscore(redis_key, 0, now - window)
        pipe.zadd(redis_key, {str(now): now})
        pipe.zcard(redis_key)
        pipe.expire(redis_key, window)
        _, _, count, _ = await pipe.execute()

        if count > limit:
            retry_after = max(int(window - (now - (now - window))), 1)
            return (True, 0, retry_after)
        return (False, limit - count, 0)
    except Exception as e:
        logger.warning("Redis rate limit check failed, using in-memory: %s", e)
        return None


def _check_memory_rate(key: str, limit: int) -> tuple[bool, int, int]:
    """Check rate limit using in-memory store."""
    now = time.time()
    window_start = now - WINDOW_SECONDS

    _rate_store[key] = [t for t in _rate_store[key] if t > window_start]

    if len(_rate_store[key]) >= limit:
        retry_after = int(WINDOW_SECONDS - (now - _rate_store[key][0]))
        return (True, 0, max(retry_after, 1))

    _rate_store[key].append(now)
    remaining = limit - len(_rate_store[key])
    return (False, remaining, 0)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-user rate limiting middleware.

    Identifies users by user_id from request.state (set by TenantMiddleware).
    Falls back to client IP for unauthenticated requests.
    Uses Redis sorted sets in production, in-memory fallback for dev.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        # Identify user
        user_id = getattr(request.state, "user_id", None)
        role = getattr(request.state, "user_role", None) or "junior"

        if user_id:
            key = f"user:{user_id}"
        else:
            client_ip = request.client.host if request.client else "unknown"
            key = f"ip:{client_ip}"

        # Get limit for role
        limit = ROLE_LIMITS.get(role, DEFAULT_LIMIT)

        # Try Redis first, fall back to in-memory
        result = await _check_redis_rate(key, limit, WINDOW_SECONDS)
        if result is None:
            result = _check_memory_rate(key, limit)

        exceeded, remaining, retry_after = result

        if exceeded:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "limit": limit,
                    "window": WINDOW_SECONDS,
                    "retry_after": max(retry_after, 1),
                },
                headers={"Retry-After": str(max(retry_after, 1))},
            )

        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(remaining, 0))
        response.headers["X-RateLimit-Reset"] = str(int(time.time() + WINDOW_SECONDS))

        return response
