"""Tenant middleware — extracts tenant_id and injects it into request state.

Currently reads from X-Tenant-ID header (LXB-009 will switch to JWT claims).
Health and docs endpoints are excluded from tenant requirement.
"""
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

# Paths that do not require a tenant context.
_PUBLIC_PATHS = frozenset({
    "/api/v1/health",
    "/api/v1/docs",
    "/api/v1/openapi.json",
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
})


def _is_public(path: str) -> bool:
    return path in _PUBLIC_PATHS or path.startswith("/api/v1/docs")


class TenantMiddleware(BaseHTTPMiddleware):
    """Extract tenant_id from X-Tenant-ID header and store in request.state."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if _is_public(request.url.path):
            request.state.tenant_id = None
            return await call_next(request)

        raw = request.headers.get("X-Tenant-ID")
        if not raw:
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing X-Tenant-ID header"},
            )

        try:
            tenant_id = uuid.UUID(raw)
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={"detail": "Invalid X-Tenant-ID: must be a valid UUID"},
            )

        request.state.tenant_id = tenant_id
        return await call_next(request)
