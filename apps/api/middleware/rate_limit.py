"""Rate limiting middleware — per-user rate limiting.

Default: 100 req/min. Configurable per role.
Uses in-memory store (production: Redis via REDIS_URL).
Returns 429 with Retry-After header when exceeded.
"""

import os
import time
from collections import defaultdict

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse


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

# In-memory rate limit store: {user_key: [timestamp, ...]}
_rate_store: dict[str, list[float]] = defaultdict(list)


def reset_rate_store() -> None:
    """Reset the rate limit store (for testing)."""
    _rate_store.clear()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-user rate limiting middleware.

    Identifies users by user_id from request.state (set by TenantMiddleware).
    Falls back to client IP for unauthenticated requests.
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

        # Check rate limit
        now = time.time()
        window_start = now - WINDOW_SECONDS

        # Clean old entries
        _rate_store[key] = [t for t in _rate_store[key] if t > window_start]

        if len(_rate_store[key]) >= limit:
            retry_after = int(WINDOW_SECONDS - (now - _rate_store[key][0]))
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

        _rate_store[key].append(now)

        response = await call_next(request)

        # Add rate limit headers
        remaining = limit - len(_rate_store[key])
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(remaining, 0))
        response.headers["X-RateLimit-Reset"] = str(int(window_start + WINDOW_SECONDS))

        return response
