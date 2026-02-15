"""LexiBel API — FastAPI Application Factory"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.middleware.tenant import TenantMiddleware
from apps.api.middleware.audit import AuditMiddleware


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

    # 4. Tenant (extracts tenant_id from header, future: JWT)
    app.add_middleware(TenantMiddleware)

    # 3. Auth stub (LXB-009 will add JWT validation here)
    # app.add_middleware(AuthMiddleware)

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

    # ── Routes ──

    @app.get("/api/v1/health")
    async def health():
        return {"status": "ok", "service": "lexibel-api", "version": "0.1.0"}

    return app


app = create_app()
