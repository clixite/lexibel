# LexiBel

AI-native Practice Management System for Belgian law firms. Multi-tenant, GDPR-compliant, Peppol-ready.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14 (App Router), Shadcn UI, TailwindCSS, Zustand |
| Backend | FastAPI, SQLAlchemy 2.0 async, Pydantic v2 |
| Workers | Celery + Redis |
| Data | PostgreSQL 16 (RLS), Redis, Qdrant (vectors), Neo4j (graph), MinIO (objects) |
| LLM | vLLM (Multi-LoRA), Azure OpenAI fallback, LangGraph agents |
| Infra | Docker Compose, GitHub Actions CI/CD, Nginx, Certbot SSL |

## Key Conventions

- **RLS everywhere**: Every table has `tenant_id`. All queries filtered by tenant via JWT middleware.
- **Append-only**: `interaction_events`, `audit_logs`, `third_party_entries` — INSERT only, never UPDATE/DELETE.
- **bcrypt==4.0.1**: Pinned in requirements.txt. bcrypt 5.x breaks passlib on Python 3.14.
- **Linting**: `ruff check` + `ruff format`. Zero tolerance — CI fails on any error.
- **Tests**: pytest with `X-Tenant-ID`/`X-User-ID`/`X-User-Role` headers for auth (not mocks).
- **Schemas**: Pydantic v2 BaseModel for all API input/output. Type hints required on all functions.
- **Frontend**: All dashboard pages use `"use client"`. Functional components only.
- **Commits**: `LXB-XXX: description` format. Reference Implementation Playbook tickets.

## Useful Commands

```bash
# Lint
ruff check apps/api/ packages/ apps/workers/
ruff format --check apps/api/ packages/ apps/workers/

# Test (420 tests, ~12 min)
pytest apps/api/tests/ -v --timeout=300

# Dev environment
docker compose up -d          # PostgreSQL, Redis, Qdrant, MinIO, Neo4j
uvicorn apps.api.main:app --reload --port 8000
cd apps/web && pnpm dev       # Next.js on :3000
```

## API Structure (25 routers in `apps/api/main.py`)

```
auth, mfa, cases, contacts, timeline, documents, inbox,
time_entries, invoices, third_party, ringover_webhook, plaud_webhook,
integrations, events, bootstrap, search, ai, migration,
dpa, outlook, ml, graph, agents, admin, mobile
```

**Middleware stack** (outermost → innermost): CORS → GZip → SecurityHeaders → Tenant → RateLimit → Compression/ETag → Audit

## Frontend Structure

Sidebar navigation (role-gated): Dashboard, Dossiers, Contacts, Timeline, Facturation, Inbox, Recherche, Graphe, Hub IA, Migration, Admin (super_admin only)

```
apps/web/app/dashboard/
├── page.tsx              # Main dashboard
├── cases/page.tsx        # Dossiers
├── contacts/page.tsx     # Contacts
├── timeline/page.tsx     # Timeline
├── billing/page.tsx      # Facturation + TimeEntryApproval
├── inbox/page.tsx        # Inbox
├── migration/page.tsx    # Data migration
├── graph/page.tsx        # Knowledge graph (React Flow)
├── ai/page.tsx           # AI Hub
├── ai/due-diligence/     # Due diligence agent
├── ai/emotional-radar/   # Emotional radar agent
└── admin/page.tsx        # Admin panel (super_admin)
```

## Deployment

- **Server**: 76.13.46.55
- **Domain**: lexibel.clixite.cloud
- **Reverse proxy**: Nginx → API (:8000), Web (:3000)
- **SSL**: Certbot (Let's Encrypt)
- **CI/CD**: GitHub Actions → GHCR → SSH deploy
- **Prod compose**: `infra/docker/docker-compose.prod.yml` (2 API replicas, resource limits, health checks)

## Database

- Dev: `postgresql+asyncpg://lexibel:lexibel_dev_2026@localhost:5432/lexibel`
- Prod: `DATABASE_URL` env var
- Migrations: Alembic (`packages/db/migrations/`)

## Reference Docs (in `docs/`)

- `02_LexiBel_Architecture.docx` — Architecture, security model, AI/ML
- `03_LexiBel_Backend_Guide.docx` — Data model, 40+ endpoints, services
- `04_LexiBel_Frontend_Guide.docx` — UI components, design system
- `05_LexiBel_Implementation_Playbook.docx` — 89 tickets (LXB-001 to LXB-070 complete)
- `06_LexiBel_PRD.docx` — Full product requirements
