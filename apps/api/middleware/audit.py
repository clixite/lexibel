"""Audit middleware — logs every API request to audit_logs.

Records method, path, user_id, tenant_id, status code, and latency.
Runs AFTER the response so it captures the final status code.
Skips health/docs endpoints to avoid noise.
"""

import time
import uuid
import logging

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from packages.db.models.audit_log import AuditLog
from packages.db.session import get_tenant_session, get_superadmin_session

logger = logging.getLogger("lexibel.audit")

_SKIP_PATHS = frozenset(
    {
        "/api/v1/health",
        "/api/v1/docs",
        "/api/v1/openapi.json",
    }
)


class AuditMiddleware(BaseHTTPMiddleware):
    """Log every API request into audit_logs (append-only)."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.url.path in _SKIP_PATHS:
            return await call_next(request)

        start = time.monotonic()
        response = await call_next(request)
        latency_ms = round((time.monotonic() - start) * 1000, 2)

        # Fire-and-forget audit log — do not block the response.
        try:
            await self._write_log(request, response, latency_ms)
        except Exception:
            logger.exception("Failed to write audit log")

        return response

    async def _write_log(
        self,
        request: Request,
        response: Response,
        latency_ms: float,
    ) -> None:
        tenant_id: uuid.UUID | None = getattr(request.state, "tenant_id", None)
        user_id: uuid.UUID | None = getattr(request.state, "user_id", None)

        log_entry = AuditLog(
            tenant_id=tenant_id or uuid.UUID("00000000-0000-0000-0000-000000000000"),
            user_id=user_id,
            action=request.method,
            resource_type="api_request",
            resource_id=request.url.path,
            metadata_={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "latency_ms": latency_ms,
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            },
        )

        if tenant_id:
            async with get_tenant_session(tenant_id) as session:
                session.add(log_entry)
        else:
            async with get_superadmin_session() as session:
                session.add(log_entry)
