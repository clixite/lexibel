#!/bin/bash
# LexiBel Bootstrap Script
# Run this ONCE from an empty directory to initialize the full monorepo
# Usage: bash bootstrap.sh

set -e
echo "============================================"
echo "  LexiBel Monorepo Bootstrap"
echo "  AI-Native Legal PMS for Belgian Bar"
echo "============================================"
echo ""

# ── 1. Root configs ──
echo "[1/8] Creating root configuration files..."

cat > package.json << 'EOF'
{
  "name": "lexibel",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "turbo dev",
    "build": "turbo build",
    "test": "turbo test",
    "lint": "turbo lint"
  },
  "devDependencies": {
    "turbo": "^2.0.0"
  }
}
EOF

cat > turbo.json << 'EOF'
{
  "$schema": "https://turbo.build/schema.json",
  "globalDependencies": [".env"],
  "tasks": {
    "build": { "dependsOn": ["^build"], "outputs": [".next/**", "dist/**"] },
    "test": { "dependsOn": ["build"] },
    "lint": {},
    "dev": { "cache": false, "persistent": true }
  }
}
EOF

cat > pnpm-workspace.yaml << 'EOF'
packages:
  - "apps/*"
  - "packages/*"
EOF

cat > .env.example << 'EOF'
# LexiBel Environment Variables
# Copy to .env and fill in real values. NEVER commit .env.

# PostgreSQL
POSTGRES_PASSWORD=change_me_strong_password_32chars

# MinIO (S3-compatible)
MINIO_PASSWORD=change_me_strong_password_32chars

# JWT Signing Key (generate: openssl rand -hex 64)
SECRET_KEY=change_me_generate_with_openssl_rand_hex_64

# Environment
ENVIRONMENT=development
EOF

cat > .gitignore << 'EOF'
# Dependencies
node_modules/
__pycache__/
*.pyc
.venv/
venv/
.turbo/

# Build
.next/
dist/
*.egg-info/

# Environment
.env
.env.local
.env.production

# IDE
.vscode/settings.json
.idea/

# OS
.DS_Store
Thumbs.db

# Docker volumes (local)
postgres_data/
qdrant_data/
minio_data/

# Coverage
.coverage
htmlcov/
coverage.xml

# Secrets
*.pem
*.key
EOF

# ── 2. Directory structure ──
echo "[2/8] Creating directory structure..."
mkdir -p apps/api/{routers,services,middleware,schemas,tests}
mkdir -p apps/web
mkdir -p apps/workers/tasks
mkdir -p packages/db/{models,migrations/versions,tests,init}
mkdir -p packages/shared-types
mkdir -p packages/llm-gateway
mkdir -p infra/{docker,nginx}
mkdir -p scripts
mkdir -p docs
mkdir -p .github/workflows

# ── 3. Backend skeleton ──
echo "[3/8] Creating backend skeleton..."

cat > requirements.txt << 'EOF'
# Core
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
python-dotenv>=1.0.0
pydantic>=2.5.0
pydantic-settings>=2.1.0

# Database
sqlalchemy[asyncio]>=2.0.25
asyncpg>=0.29.0
alembic>=1.13.0
psycopg2-binary>=2.9.9

# Cache & Queue
redis>=5.0.0
celery[redis]>=5.3.0

# Auth
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
pyotp>=2.9.0

# Storage
boto3>=1.34.0

# Vector DB
qdrant-client>=1.7.0

# ML/NLP
httpx>=0.26.0
EOF

cat > requirements-dev.txt << 'EOF'
# Testing
pytest>=8.0.0
pytest-asyncio>=0.23.0
httpx>=0.26.0
factory-boy>=3.3.0
pytest-cov>=4.1.0

# Linting
ruff>=0.2.0

# Type checking
mypy>=1.8.0
EOF

cat > apps/api/__init__.py << 'EOF'
EOF

cat > apps/api/main.py << 'EOF'
"""LexiBel API — FastAPI Application Factory"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

def create_app() -> FastAPI:
    app = FastAPI(
        title="LexiBel API",
        description="AI-Native Legal Practice Management for Belgian Bar",
        version="0.1.0",
        docs_url="/api/v1/docs",
        openapi_url="/api/v1/openapi.json",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check
    @app.get("/api/v1/health")
    async def health():
        return {"status": "ok", "service": "lexibel-api", "version": "0.1.0"}

    return app

app = create_app()
EOF

cat > apps/api/tests/__init__.py << 'EOF'
EOF

cat > apps/api/tests/test_health.py << 'EOF'
"""Basic health check test"""
import pytest
from httpx import ASGITransport, AsyncClient
from apps.api.main import app

@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "lexibel-api"
EOF

# ── 4. Workers skeleton ──
cat > apps/workers/__init__.py << 'EOF'
EOF

cat > apps/workers/main.py << 'EOF'
"""LexiBel Celery Workers"""
from celery import Celery
import os

app = Celery(
    "lexibel",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Brussels",
    enable_utc=True,
    task_queues={
        "default": {},
        "indexing": {},
        "migration": {},
        "peppol": {},
    },
)
EOF

# ── 5. DB package skeleton ──
echo "[4/8] Creating database package..."

cat > packages/db/__init__.py << 'EOF'
EOF

cat > packages/db/models/__init__.py << 'EOF'
"""SQLAlchemy Models — to be implemented in Sprint 0 (LXB-005/006)"""
EOF

cat > packages/db/tests/__init__.py << 'EOF'
EOF

cat > packages/db/init/00_extensions.sql << 'EOF'
-- PostgreSQL extensions needed for LexiBel
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
EOF

# ── 6. Frontend skeleton ──
echo "[5/8] Creating frontend skeleton..."

cat > apps/web/package.json << 'EOF'
{
  "name": "web",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "test": "vitest run"
  },
  "dependencies": {
    "next": "14.2.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "@types/node": "^20",
    "@types/react": "^18",
    "typescript": "^5",
    "vitest": "^1.2.0",
    "eslint": "^8",
    "eslint-config-next": "14.2.0",
    "tailwindcss": "^3.4.0",
    "postcss": "^8",
    "autoprefixer": "^10"
  }
}
EOF

mkdir -p apps/web/app
cat > apps/web/app/layout.tsx << 'EOF'
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "LexiBel",
  description: "AI-Native Legal Practice Management for Belgian Bar",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  );
}
EOF

cat > apps/web/app/page.tsx << 'EOF'
export default function Home() {
  return (
    <main style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100vh", fontFamily: "Arial" }}>
      <div style={{ textAlign: "center" }}>
        <h1 style={{ fontSize: "3rem", color: "#1B365D" }}>LexiBel</h1>
        <p style={{ color: "#636E72", fontSize: "1.2rem" }}>
          L&apos;Écosystème Juridique Intelligent pour le Barreau Belge
        </p>
        <p style={{ marginTop: "2rem", color: "#999" }}>v0.1.0 — Sprint 0 in progress</p>
      </div>
    </main>
  );
}
EOF

cat > apps/web/tsconfig.json << 'EOF'
{
  "compilerOptions": {
    "target": "es5",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "paths": { "@/*": ["./*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx"],
  "exclude": ["node_modules"]
}
EOF

# ── 7. CI/CD ──
echo "[6/8] Creating CI/CD pipeline..."

cat > .github/workflows/ci.yml << 'EOF'
name: LexiBel CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_DB: lexibel_test
          POSTGRES_USER: lexibel
          POSTGRES_PASSWORD: test
        ports: ["5432:5432"]
        options: --health-cmd pg_isready --health-interval 5s --health-timeout 3s --health-retries 5
      redis:
        image: redis:7-alpine
        ports: ["6379:6379"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - run: ruff check apps/api/ packages/ || true
      - run: pytest apps/api/tests/ -v --tb=short
        env:
          DATABASE_URL: postgresql+asyncpg://lexibel:test@localhost:5432/lexibel_test
          REDIS_URL: redis://localhost:6379/0

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - run: npm install -g pnpm
      - run: cd apps/web && pnpm install
      - run: cd apps/web && pnpm build

  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: aquasecurity/trivy-action@master
        with:
          scan-type: fs
          scan-ref: .
          severity: CRITICAL,HIGH
        continue-on-error: true
EOF

# ── 8. Final ──
echo "[7/8] Creating Docker configs..."

mkdir -p infra/docker

cat > infra/docker/Dockerfile.api << 'EOF'
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY packages/ packages/
COPY apps/api/ apps/api/
COPY apps/workers/ apps/workers/
EXPOSE 8000
CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

cat > infra/docker/Dockerfile.web << 'EOF'
FROM node:20-alpine
RUN npm install -g pnpm
WORKDIR /app
COPY apps/web/package.json apps/web/pnpm-lock.yaml* ./
RUN pnpm install
COPY apps/web/ .
EXPOSE 3000
CMD ["pnpm", "dev"]
EOF

echo "[8/8] Done!"
echo ""
echo "============================================"
echo "  Monorepo initialized successfully!"
echo "============================================"
echo ""
echo "Next steps:"
echo "  1. Copy CLAUDE.md to this directory"
echo "  2. Copy 6 Word docs to docs/"
echo "  3. Copy .env.example to .env and fill values"
echo "  4. Run: pnpm install"
echo "  5. Run: docker compose up -d"
echo "  6. Run: git add . && git commit -m 'LXB-001: Initialize monorepo'"
echo "  7. Run: git push -u origin main"
echo "  8. Start Claude Code: claude"
echo ""
