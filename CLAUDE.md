# LexiBel — L'Ecosysteme Juridique Intelligent

## Stack
- Backend: FastAPI 0.109+ (Python 3.11), PostgreSQL 16 + RLS, Redis, Qdrant, MinIO, Neo4j
- Frontend: Next.js 14.2, next-auth v5 beta, TailwindCSS, Recharts, D3
- Infra: Docker Compose, GitHub Actions CI/CD, Nginx, Certbot SSL

## Conventions
- ALL tables have tenant_id + RLS policies. No exceptions.
- Append-only tables: interaction_events, third_party_entries (REVOKE UPDATE/DELETE)
- bcrypt==4.0.1 pinned (passlib compat)
- Linting: ruff check + ruff format (zero errors policy)
- Tests: pytest with --timeout=300, cross-tenant isolation tests mandatory
- API prefix: /api/v1/, JWT auth (HS256), 30min access + 7d refresh tokens
- All frontend pages: "use client" with useSession()
- API_URL_INTERNAL env var for server-side auth calls (not NEXT_PUBLIC_)

## Key Commands
- Lint: python -m ruff check apps/api/ packages/ apps/workers/
- Format: python -m ruff format apps/api/ packages/ apps/workers/
- Test: python -m pytest apps/api/tests/ packages/db/tests/ -v --timeout=300
- Build web: cd apps/web && pnpm build
- Deploy: ssh root@76.13.46.55 "cd /opt/lexibel && git pull && docker compose build --no-cache api web && docker compose up -d"

## Architecture
- 19 routers registered in apps/api/main.py
- 7 middleware layers (tenant, audit, RBAC, rate limit, compression, security headers, CORS)
- Dashboard: apps/web/app/dashboard/ with Sidebar component
- Models: packages/db/models/ with Alembic migrations

## Production
- Server: 76.13.46.55 (Ubuntu 25.10)
- Domain: lexibel.clixite.cloud (SSL via certbot)
- Docker: 7 containers (postgres, redis, qdrant, minio, api, worker, web)
- Web env needs: NEXTAUTH_SECRET, NEXTAUTH_URL, AUTH_TRUST_HOST, API_URL_INTERNAL

## Sprint Status
- Sprints 0-12 COMPLETE (LXB-001 to LXB-070)
- 420 tests passing, ruff clean
- CI/CD: GitHub Actions (backend + frontend + security jobs)
