"""LexiBel API — FastAPI Application Factory"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.middleware.tenant import TenantMiddleware
from apps.api.middleware.audit import AuditMiddleware
from apps.api.auth.router import router as auth_router
from apps.api.auth.mfa_router import mfa_router
from apps.api.routers.cases import router as cases_router
from apps.api.routers.contacts import router as contacts_router


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

    # ── Health check ──
    @app.get("/api/v1/health")
    async def health():
        return {"status": "ok", "service": "lexibel-api", "version": "0.1.0"}

    return app


app = create_app()
