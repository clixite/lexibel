"""LexiBel API — FastAPI Application Factory"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.middleware.tenant import TenantMiddleware
from apps.api.middleware.audit import AuditMiddleware
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

    # 5. Audit (innermost — runs last, captures status code + latency)
    app.add_middleware(AuditMiddleware)

    # 4. Tenant (extracts tenant_id from JWT claims or X-Tenant-ID header)
    app.add_middleware(TenantMiddleware)

    # 3. Auth — JWT validation is handled inside TenantMiddleware
    #    (token is decoded there to extract tenant_id + user claims)

    # 2. RateLimit stub (future: slowapi or similar)
    # app.add_middleware(RateLimitMiddleware)

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
