"""LexiBel API — FastAPI Application Factory"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware

from apps.api.middleware.tenant import TenantMiddleware
from apps.api.middleware.audit import AuditMiddleware
from apps.api.middleware.rate_limit import RateLimitMiddleware
from apps.api.middleware.security_headers import SecurityHeadersMiddleware
from apps.api.middleware.compression import CompressionMiddleware
from apps.api.auth.router import router as auth_router
from apps.api.auth.mfa_router import mfa_router
from apps.api.routers.cases import router as cases_router
from apps.api.routers.contacts import router as contacts_router
from apps.api.routers.timeline import router as timeline_router
from apps.api.routers.documents import router as documents_router
from apps.api.routers.inbox import router as inbox_router
from apps.api.routers.time_entries import router as time_entries_router
from apps.api.routers.invoices import router as invoices_router
from apps.api.routers.third_party import router as third_party_router
from apps.api.webhooks.ringover import router as ringover_webhook_router
from apps.api.webhooks.plaud import router as plaud_webhook_router
from apps.api.routers.integrations import router as integrations_router
from apps.api.routers.events import router as events_router
from apps.api.routers.bootstrap import router as bootstrap_router, ensure_admin_user
from apps.api.routers.search import router as search_router
from apps.api.routers.ai import router as ai_router
from apps.api.routers.migration import router as migration_router
from apps.api.routers.dpa import router as dpa_router
from apps.api.routers.outlook import router as outlook_router
from apps.api.routers.ml import router as ml_router
from apps.api.routers.graph import router as graph_router
from apps.api.routers.agents import router as agents_router
from apps.api.routers.admin import router as admin_router
from apps.api.routers.mobile import router as mobile_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="LexiBel API",
        description="AI-Native Legal Practice Management for Belgian Bar",
        version="0.1.0",
        docs_url="/api/v1/docs",
        openapi_url="/api/v1/openapi.json",
    )

    # ── Middleware stack (outermost → innermost) ──
    # Registration order is reversed: last added = outermost.

    # 7. Audit (innermost — runs last, captures status code + latency)
    app.add_middleware(AuditMiddleware)

    # 6. ETag / Compression support
    app.add_middleware(CompressionMiddleware)

    # 5. Rate limiting (per-user, per-role)
    app.add_middleware(RateLimitMiddleware)

    # 4. Tenant (extracts tenant_id from JWT claims or X-Tenant-ID header)
    app.add_middleware(TenantMiddleware)

    # 3. Security headers (X-Content-Type-Options, CSP, HSTS, X-Request-ID)
    app.add_middleware(SecurityHeadersMiddleware)

    # 2. GZip compression (for mobile optimization)
    app.add_middleware(GZipMiddleware, minimum_size=500)

    # 1. CORS (outermost)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ──
    app.include_router(auth_router)
    app.include_router(mfa_router)
    app.include_router(cases_router)
    app.include_router(contacts_router)
    app.include_router(timeline_router)
    app.include_router(documents_router)
    app.include_router(inbox_router)
    app.include_router(time_entries_router)
    app.include_router(invoices_router)
    app.include_router(third_party_router)
    app.include_router(ringover_webhook_router)
    app.include_router(plaud_webhook_router)
    app.include_router(integrations_router)
    app.include_router(events_router)
    app.include_router(bootstrap_router)
    app.include_router(search_router)
    app.include_router(ai_router)
    app.include_router(migration_router)
    app.include_router(dpa_router)
    app.include_router(outlook_router)
    app.include_router(ml_router)
    app.include_router(graph_router)
    app.include_router(agents_router)
    app.include_router(admin_router)
    app.include_router(mobile_router)

    # ── Startup ──
    @app.on_event("startup")
    async def startup():
        ensure_admin_user()

    # ── Health check ──
    @app.get("/api/v1/health")
    async def health():
        return {"status": "ok", "service": "lexibel-api", "version": "0.1.0"}

    return app


app = create_app()
