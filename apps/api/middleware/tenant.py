"""Tenant middleware — extracts tenant_id from JWT or X-Tenant-ID header.

Priority: JWT 'tid' claim → X-Tenant-ID header (dev fallback).
Health, docs, and auth endpoints are excluded from tenant requirement.
"""

import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

from apps.api.auth.jwt import TokenError, verify_token

# Paths that do not require a tenant context.
_PUBLIC_PATHS = frozenset(
    {
        "/api/v1/health",
        "/api/v1/docs",
        "/api/v1/openapi.json",
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/auth/mfa/challenge",
        "/api/v1/webhooks/ringover",
        "/api/v1/webhooks/plaud",
        "/api/v1/bootstrap/admin",
    }
)


def _is_public(path: str) -> bool:
    return path in _PUBLIC_PATHS or path.startswith("/api/v1/docs")


def _extract_bearer_token(auth_header: str | None) -> str | None:
    """Extract token from 'Bearer <token>' header."""
    if not auth_header:
        return None
    parts = auth_header.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


class TenantMiddleware(BaseHTTPMiddleware):
    """Extract tenant_id from JWT claims or X-Tenant-ID header.

    On success, sets request.state.tenant_id, request.state.user_id,
    and request.state.user_role from JWT claims.
    Falls back to X-Tenant-ID header for development without JWT.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if _is_public(request.url.path):
            request.state.tenant_id = None
            request.state.user_id = None
            request.state.user_role = None
            return await call_next(request)

        # Try JWT first
        token = _extract_bearer_token(request.headers.get("Authorization"))
        if token:
            try:
                claims = verify_token(token, expected_type="access")
                request.state.tenant_id = uuid.UUID(claims["tid"])
                request.state.user_id = uuid.UUID(claims["sub"])
                request.state.user_role = claims.get("role")
                request.state.user_email = claims.get("email", "")
                return await call_next(request)
            except (TokenError, KeyError, ValueError):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid or expired access token"},
                )

        # Fallback: X-Tenant-ID header (dev/testing only)
        raw = request.headers.get("X-Tenant-ID")
        if raw:
            try:
                request.state.tenant_id = uuid.UUID(raw)
                # Dev headers for user context
                user_id_raw = request.headers.get("X-User-ID")
                request.state.user_id = uuid.UUID(user_id_raw) if user_id_raw else None
                request.state.user_role = request.headers.get("X-User-Role")
                request.state.user_email = request.headers.get("X-User-Email", "")
                return await call_next(request)
            except ValueError:
                return JSONResponse(
                    status_code=400,
                    content={"detail": "Invalid X-Tenant-ID: must be a valid UUID"},
                )

        return JSONResponse(
            status_code=401,
            content={"detail": "Missing Authorization header or X-Tenant-ID"},
        )
