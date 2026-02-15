# LexiBel — Claude Code Context

## Project Overview
LexiBel is an AI-native Practice Management System (PMS) for Belgian law firms. It integrates artificial intelligence as its foundational substrate: every interaction (email, call, court filing, transcription) feeds a Case Brain that transforms unstructured data into sourced, auditable, actionable knowledge. Built for the Belgian Bar (OBFG + OVB) with native compliance for professional secrecy (Art. 458 Penal Code), Peppol e-invoicing, and GDPR.

## Architecture (6 Layers)
- **L1 Frontend**: Next.js 14 (App Router), Shadcn UI, TailwindCSS, Zustand, TipTap, React Flow
- **L2 Backend**: FastAPI (Python 3.11), SQLAlchemy 2.0 async, Pydantic v2
- **L3 Workers**: Celery + Redis (queues: default, indexing, migration, peppol)
- **L4 Data**: PostgreSQL 16 (RLS), Qdrant (vectors), Neo4j (graph), MinIO/S3 (objects), Redis (cache)
- **L5 LLM Gateway**: vLLM (Multi-LoRA), Azure OpenAI (Zero Retention fallback), LangGraph (agents)
- **L6 Infra**: Docker Compose (dev), Kubernetes (future), GitHub Actions CI/CD, Grafana/Prometheus/Loki

## Key Principles (NEVER violate)
1. **P1 Professional Secrecy by Design**: Every table has `tenant_id` + RLS. Test cross-tenant isolation in every PR. Zero tolerance for data leaks.
2. **P2 Event-Sourced Timeline**: `interaction_events` and `audit_logs` are INSERT-only (append-only). No UPDATE, no DELETE.
3. **P3 No Source No Claim**: AI responses must cite sources. LLM Gateway refuses if citation_coverage < threshold.
4. **P4 Human-in-the-Loop**: InboxItems are DRAFT until validated. Auto-attach only if confidence > tenant threshold.
5. **P5 Strict Multi-Tenant**: Pool (RLS) default, Silo option. BYOK per tenant.
6. **P6 Idempotence Everywhere**: All webhooks use idempotency_key. Replay 2x = 0 duplicates.
7. **P7 Peppol-Ready Natively**: UBL 2.1 / BIS Billing 3.0 from MVP.

## Monorepo Structure
```
lexibel/
├── apps/
│   ├── web/                   # Next.js 14 frontend
│   ├── api/                   # FastAPI backend
│   │   ├── main.py            # App factory
│   │   ├── routers/           # API route modules
│   │   ├── services/          # Business logic
│   │   ├── middleware/        # Auth, Tenant, RBAC, Audit
│   │   ├── schemas/           # Pydantic request/response models
│   │   └── tests/             # pytest tests
│   └── workers/               # Celery workers
│       ├── main.py            # Celery app
│       └── tasks/             # Task modules (ingestion, indexing, migration, peppol)
├── packages/
│   ├── shared-types/          # Pydantic models shared api<>workers
│   ├── db/                    # SQLAlchemy models + Alembic migrations
│   │   ├── models/            # SQLAlchemy model files
│   │   ├── migrations/        # Alembic versions
│   │   └── tests/             # Cross-tenant isolation tests
│   └── llm-gateway/           # LLM Gateway service
├── infra/
│   ├── docker/                # Dockerfiles (Dockerfile.api, Dockerfile.web)
│   └── nginx/                 # Nginx production config
├── docs/                      # 6 specification documents (READ THESE)
├── scripts/                   # Utility scripts
├── .github/workflows/         # CI/CD
├── CLAUDE.md                  # THIS FILE
├── docker-compose.yml         # Dev environment
├── docker-compose.prod.yml    # Production
└── turbo.json                 # Turborepo
```

## Coding Standards

### Python (Backend)
- **Linter**: ruff (replaces flake8 + isort + pyflakes)
- **Formatter**: ruff format (replaces black)
- **Type hints**: Required on all functions
- **Tests**: pytest + httpx (async) + factory-boy. Cross-tenant tests mandatory.
- **Async**: Use async/await everywhere (SQLAlchemy async sessions, httpx)
- **Models**: SQLAlchemy 2.0 declarative with mapped_column()
- **Schemas**: Pydantic v2 BaseModel for all API input/output
- **Errors**: Custom exception classes, never return raw 500s

### TypeScript (Frontend)
- **Strict mode**: tsconfig strict: true
- **Linter**: ESLint + Prettier
- **Components**: Functional components only, Shadcn UI primitives
- **State**: Zustand for global, TanStack Query for server state
- **Forms**: React Hook Form + Zod schemas
- **Styling**: TailwindCSS utility classes only (no CSS files)

### Commits
- Format: `LXB-XXX: short description`
- Reference ticket IDs from the Implementation Playbook (docs/05)
- One ticket = one commit (or small coherent set)

### Security
- Never hardcode secrets. Use environment variables (.env, never committed).
- All DB queries go through RLS (tenant_id from JWT middleware).
- PII fields encrypted with pgcrypto.
- Hash all files/payloads with SHA-256.

## Reference Documents (in docs/)
When implementing a feature, READ the relevant document first:
- **03_LexiBel_Backend_Guide.docx** — Data model (15+ tables), API (40+ endpoints), services, webhook flows
- **04_LexiBel_Frontend_Guide.docx** — UI components, pages, design system, API client patterns
- **05_LexiBel_Implementation_Playbook.docx** — 89 tickets with acceptance criteria (your sprint backlog)
- **02_LexiBel_Architecture.docx** — Architecture details, security model, AI/ML, integrations
- **06_LexiBel_PRD.docx** — Complete product requirements

## Current Sprint
**Sprint 0: Foundations (Weeks 1-2)**
Tickets: LXB-001 through LXB-011

Focus:
- LXB-001: Init monorepo (Turborepo + pnpm)
- LXB-002: Dockerfiles (web, api, workers)
- LXB-003: GitHub Actions CI pipeline
- LXB-005: PostgreSQL schema + RLS (tenants, users, audit_logs)
- LXB-006: SQLAlchemy models + Alembic
- LXB-007: Tenant middleware FastAPI
- LXB-008: RBAC middleware + permissions
- LXB-009: Auth OIDC backend (JWT)
- LXB-010: Auth frontend (next-auth v5)
- LXB-011: MFA (TOTP)

## Database Connection
- Dev: `postgresql+asyncpg://lexibel:lexibel_dev_2026@localhost:5432/lexibel`
- Test: Use pytest fixtures with transaction rollback
- Prod: Via environment variable DATABASE_URL

## API Base URL
- Dev: `http://localhost:8000/api/v1`
- Prod: `https://lexibel.clixite.cloud/api/v1`
