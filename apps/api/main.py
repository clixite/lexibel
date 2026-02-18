"""LexiBel API — FastAPI Application Factory"""

import logging
import os
from contextlib import asynccontextmanager

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
from apps.api.routers.bootstrap import router as bootstrap_router, ensure_admin_user, seed_demo_data
from apps.api.routers.search import router as search_router
from apps.api.routers.ai import router as ai_router
from apps.api.routers.migration import router as migration_router
from apps.api.routers.dpa import router as dpa_router
from apps.api.routers.outlook import router as outlook_router
from apps.api.routers.ml import router as ml_router
from apps.api.routers.graph import router as graph_router
from apps.api.routers.agents import router as agents_router
from apps.api.routers.admin import router as admin_router
from apps.api.routers.admin_settings import router as admin_settings_router
from apps.api.routers.mobile import router as mobile_router
from apps.api.routers.ringover import router as ringover_router
from apps.api.routers.legal_rag import router as legal_rag_router
from apps.api.routers.calendar import router as calendar_router
from apps.api.routers.emails import router as emails_router
from apps.api.routers.calls import router as calls_router
from apps.api.routers.transcriptions import router as transcriptions_router
from apps.api.routers.dashboard import router as dashboard_router
from apps.api.routers.oauth import router as oauth_router
from apps.api.routers.cloud_documents import router as cloud_documents_router
from apps.api.routers.llm import router as llm_router

# Optional routers (defensive imports)
try:
    from apps.api.routes.sentinel import router as sentinel_router
    SENTINEL_AVAILABLE = True
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"Sentinel router not available: {e}")
    sentinel_router = None
    SENTINEL_AVAILABLE = False

from apps.api.services.metrics import metrics_endpoint

logger = logging.getLogger(__name__)


def _get_cors_origins() -> list[str]:
    """Build CORS origins from CORS_ORIGINS env var + defaults."""
    defaults = ["http://localhost:3000", "https://lexibel.clixite.cloud"]
    extra = os.getenv("CORS_ORIGINS", "")
    if extra:
        defaults.extend(o.strip() for o in extra.split(",") if o.strip())
    return list(set(defaults))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    # Run Alembic migrations on startup
    try:
        from alembic.config import Config
        from alembic import command

        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("Alembic migrations applied successfully")
    except Exception as e:
        logger.warning("Alembic migration skipped: %s", e)

    # Bootstrap admin user
    try:
        await ensure_admin_user()
    except Exception as e:
        logger.warning("Admin bootstrap skipped: %s", e)

    # Seed demo data if DB is empty
    try:
        await seed_demo_data()
    except Exception as e:
        logger.warning("Demo data seeding skipped: %s", e)

    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="LexiBel API",
        description="AI-Native Legal Practice Management for Belgian Bar",
        version="0.1.0",
        docs_url="/api/v1/docs",
        openapi_url="/api/v1/openapi.json",
        lifespan=lifespan,
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
        allow_origins=_get_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Note: RBAC is enforced via @require_role() decorators (apps/api/middleware/rbac.py),
    # not as ASGI middleware, since it operates at the route level.

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
    app.include_router(admin_settings_router)
    app.include_router(mobile_router)
    app.include_router(ringover_router)
    app.include_router(legal_rag_router)
    app.include_router(calendar_router)
    app.include_router(emails_router)
    app.include_router(calls_router)
    app.include_router(transcriptions_router)
    app.include_router(dashboard_router)
    app.include_router(oauth_router)
    app.include_router(cloud_documents_router)
    app.include_router(llm_router)

    # Optional routers
    if SENTINEL_AVAILABLE and sentinel_router:
        app.include_router(sentinel_router, prefix="/api/sentinel", tags=["sentinel"])

    # ── Health check ──
    @app.get("/api/v1/health")
    async def health():
        return {"status": "ok", "service": "lexibel-api", "version": "0.1.0"}

    # ── Metrics endpoint ──
    @app.get("/metrics")
    async def metrics():
        """Prometheus metrics."""
        return await metrics_endpoint()

    return app


app = create_app()
