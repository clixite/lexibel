# LexiBel — Developer Setup Guide & Production Pipeline

## Architecture Overview

```
┌─────────────┐     git push      ┌──────────────────┐    CI/CD       ┌─────────────────────┐
│  Your Local  │ ──────────────▶  │  GitHub Actions   │ ────────────▶ │  Production Server  │
│  (Windows)   │                  │  (Build + Test)   │               │  76.x.x.x           │
│  Claude Code │                  │  Docker images    │               │  Docker Compose      │
└─────────────┘                  └──────────────────┘               │  Nginx reverse proxy │
       │                                                             │  lexibel.clixite.cloud│
       │  docs/                                                      └─────────────────────┘
       │  (6 Word docs as                                     
       │   reference for                                      
       │   Claude Code)                                       
```

## Step-by-Step Implementation Plan

---

### PHASE 0: Prerequisites (Your Machine)

**Required software:**
- Git for Windows
- Node.js 20 LTS
- Python 3.11+
- Docker Desktop
- Claude Code CLI (`npm install -g @anthropic-ai/claude-code`)
- pnpm (`npm install -g pnpm`)
- VS Code (optional but recommended)

---

### STEP 1: Create GitHub Repository

```bash
# On your machine, open terminal
mkdir lexibel && cd lexibel
git init
git branch -M main

# Go to github.com/clixite → New repository
# Name: lexibel
# Private repo
# Do NOT initialize with README (we'll push from local)

git remote add origin git@github.com:clixite/lexibel.git
```

**SSH key setup (if not done):**
```bash
ssh-keygen -t ed25519 -C "nicolas@clixite.com"
# Add ~/.ssh/id_ed25519.pub to GitHub → Settings → SSH Keys
```

---

### STEP 2: Initialize Monorepo Structure

```bash
# From the lexibel/ root directory
pnpm init

# Create Turborepo config
cat > turbo.json << 'EOF'
{
  "$schema": "https://turbo.build/schema.json",
  "globalDependencies": [".env"],
  "pipeline": {
    "build": { "dependsOn": ["^build"], "outputs": [".next/**", "dist/**"] },
    "test": { "dependsOn": ["build"] },
    "lint": {},
    "dev": { "cache": false, "persistent": true }
  }
}
EOF

# Create directory structure
mkdir -p apps/web apps/api apps/workers
mkdir -p packages/shared-types packages/db packages/llm-gateway
mkdir -p infra/{k8s,docker,nginx}
mkdir -p scripts docs

# Copy your 6 Word documents into docs/
# docs/01_LexiBel_Business_Case.docx
# docs/02_LexiBel_Architecture.docx
# docs/03_LexiBel_Backend_Guide.docx
# docs/04_LexiBel_Frontend_Guide.docx
# docs/05_LexiBel_Implementation_Playbook.docx
# docs/06_LexiBel_PRD.docx
```

---

### STEP 3: Configure Claude Code

Create the Claude Code configuration file at the root:

```bash
cat > CLAUDE.md << 'EOF'
# LexiBel — Claude Code Context

## Project Overview
LexiBel is an AI-native Practice Management System (PMS) for Belgian law firms.
Full specifications are in the docs/ folder (6 Word documents).

## Architecture
- **Frontend**: Next.js 14 (App Router), Shadcn UI, TailwindCSS, Zustand, TipTap
- **Backend**: FastAPI (Python 3.11), SQLAlchemy 2.0 async, Pydantic v2
- **Workers**: Celery + Redis
- **Data**: PostgreSQL 16 (RLS), Qdrant, Neo4j, MinIO/S3, Redis
- **LLM Gateway**: vLLM (Multi-LoRA), Azure OpenAI (Zero Retention fallback)
- **Infra**: Docker Compose (dev), Kubernetes (prod), GitHub Actions CI/CD

## Key Principles (NEVER violate)
1. **Multi-tenant isolation**: Every table has tenant_id + RLS. Test cross-tenant in every PR.
2. **Append-only events**: interaction_events and audit_logs are INSERT-only.
3. **No Source No Claim**: AI responses must cite sources or refuse.
4. **Idempotence**: All webhooks use idempotency_key.
5. **Peppol native**: UBL 2.1 / BIS Billing 3.0 from day 1.

## Monorepo Structure
- apps/web — Next.js 14 frontend
- apps/api — FastAPI backend
- apps/workers — Celery workers
- packages/db — SQLAlchemy models + Alembic migrations
- packages/shared-types — Pydantic models shared between api/workers
- packages/llm-gateway — LLM Gateway service
- infra/ — Docker, K8s, Nginx configs
- docs/ — Specification documents (Word)

## Coding Standards
- Python: ruff linter, black formatter, type hints everywhere, pytest
- TypeScript: ESLint + Prettier, strict mode, Zod for validation
- Commits: LXB-XXX: short description (reference ticket IDs from Playbook doc)
- Tests: pytest (backend), vitest (frontend), cross-tenant tests mandatory
- No hardcoded secrets. Use .env files (never committed).

## Reference Documents
Read these documents (in docs/) for detailed specifications:
- 03_LexiBel_Backend_Guide.docx — Data model, API, services
- 04_LexiBel_Frontend_Guide.docx — UI components, pages, design system  
- 05_LexiBel_Implementation_Playbook.docx — Sprint tickets with acceptance criteria
- 02_LexiBel_Architecture.docx — Full architecture details
- 06_LexiBel_PRD.docx — Complete product requirements

## Current Sprint
Sprint 0: Foundations (LXB-001 through LXB-011)
Focus: repo init, Docker, CI/CD, PostgreSQL + RLS, auth
EOF
```

---

### STEP 4: Docker Compose (Development Environment)

```bash
cat > docker-compose.yml << 'EOF'
version: "3.9"

services:
  # ── PostgreSQL 16 with RLS ──
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: lexibel
      POSTGRES_USER: lexibel
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-lexibel_dev_2026}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./packages/db/init:/docker-entrypoint-initdb.d
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U lexibel"]
      interval: 5s
      timeout: 3s
      retries: 5

  # ── Redis (cache + Celery broker) ──
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s

  # ── Qdrant (vector DB) ──
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage

  # ── MinIO (S3-compatible object storage) ──
  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: lexibel
      MINIO_ROOT_PASSWORD: ${MINIO_PASSWORD:-lexibel_minio_2026}
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data

  # ── FastAPI Backend ──
  api:
    build:
      context: .
      dockerfile: infra/docker/Dockerfile.api
    environment:
      DATABASE_URL: postgresql+asyncpg://lexibel:${POSTGRES_PASSWORD:-lexibel_dev_2026}@postgres:5432/lexibel
      REDIS_URL: redis://redis:6379/0
      QDRANT_URL: http://qdrant:6333
      MINIO_ENDPOINT: minio:9000
      MINIO_ACCESS_KEY: lexibel
      MINIO_SECRET_KEY: ${MINIO_PASSWORD:-lexibel_minio_2026}
      SECRET_KEY: ${SECRET_KEY:-dev-secret-change-me}
      ENVIRONMENT: development
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./apps/api:/app/apps/api
      - ./packages:/app/packages
    command: uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload

  # ── Celery Workers ──
  worker:
    build:
      context: .
      dockerfile: infra/docker/Dockerfile.api
    environment:
      DATABASE_URL: postgresql+asyncpg://lexibel:${POSTGRES_PASSWORD:-lexibel_dev_2026}@postgres:5432/lexibel
      REDIS_URL: redis://redis:6379/0
      QDRANT_URL: http://qdrant:6333
      MINIO_ENDPOINT: minio:9000
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./apps/workers:/app/apps/workers
      - ./packages:/app/packages
    command: celery -A apps.workers.main worker -l info -Q default,indexing,migration,peppol

  # ── Next.js Frontend ──
  web:
    build:
      context: .
      dockerfile: infra/docker/Dockerfile.web
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000/api/v1
    volumes:
      - ./apps/web:/app/apps/web
      - ./packages/shared-types:/app/packages/shared-types
    command: pnpm --filter web dev

volumes:
  postgres_data:
  qdrant_data:
  minio_data:
EOF
```

---

### STEP 5: Dockerfiles

```bash
# Backend (Python)
mkdir -p infra/docker

cat > infra/docker/Dockerfile.api << 'EOF'
FROM python:3.11-slim AS base
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY packages/ packages/
COPY apps/api/ apps/api/
COPY apps/workers/ apps/workers/
EXPOSE 8000
CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

# Frontend (Node.js)
cat > infra/docker/Dockerfile.web << 'EOF'
FROM node:20-alpine AS base
RUN npm install -g pnpm
WORKDIR /app
COPY pnpm-workspace.yaml package.json pnpm-lock.yaml* ./
COPY apps/web/package.json apps/web/
COPY packages/shared-types/package.json packages/shared-types/
RUN pnpm install --frozen-lockfile
COPY apps/web/ apps/web/
COPY packages/shared-types/ packages/shared-types/
EXPOSE 3000
CMD ["pnpm", "--filter", "web", "dev"]
EOF
```

---

### STEP 6: Production Server Setup

**Connect to server:**
```bash
ssh root@76.13.46.55
```

**A) Create dedicated user + SSH key auth:**
```bash
# On server
adduser lexibel
usermod -aG docker lexibel
usermod -aG sudo lexibel

# Switch to lexibel user
su - lexibel
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# From YOUR machine, copy your public key:
# ssh-copy-id -i ~/.ssh/id_ed25519.pub lexibel@76.13.46.55

# Then on server, disable password auth for this user (after key works):
# sudo sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
# sudo systemctl restart sshd
```

**B) Install Docker + Docker Compose (if not present):**
```bash
# As root on server
curl -fsSL https://get.docker.com | sh
apt-get install -y docker-compose-plugin
systemctl enable docker
```

**C) Create project directory:**
```bash
su - lexibel
mkdir -p /home/lexibel/lexibel
mkdir -p /home/lexibel/lexibel-data/{postgres,redis,qdrant,minio}
```

**D) Nginx reverse proxy config:**
```bash
# As root, add to existing nginx
cat > /etc/nginx/sites-available/lexibel.clixite.cloud << 'EOF'
# LexiBel — lexibel.clixite.cloud
server {
    listen 80;
    server_name lexibel.clixite.cloud;

    # Redirect HTTP to HTTPS (after certbot)
    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name lexibel.clixite.cloud;

    # SSL (managed by certbot)
    ssl_certificate /etc/letsencrypt/live/lexibel.clixite.cloud/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/lexibel.clixite.cloud/privkey.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline';" always;

    # Frontend (Next.js)
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # API Backend
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 50M;
    }

    # SSE (Server-Sent Events) — long-lived connections
    location /api/v1/events/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Connection '';
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400s;
    }

    # WebSocket (for migration progress, etc.)
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
EOF

# Enable site
ln -sf /etc/nginx/sites-available/lexibel.clixite.cloud /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

# SSL certificate (first time, HTTP must work for challenge)
certbot --nginx -d lexibel.clixite.cloud
```

---

### STEP 7: GitHub Actions CI/CD Pipeline

```bash
mkdir -p .github/workflows

cat > .github/workflows/ci.yml << 'EOF'
name: LexiBel CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_PREFIX: ghcr.io/clixite/lexibel

jobs:
  # ── Lint & Test Backend ──
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
        options: >-
          --health-cmd pg_isready
          --health-interval 5s
          --health-timeout 3s
          --health-retries 5
      redis:
        image: redis:7-alpine
        ports: ["6379:6379"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - run: ruff check apps/api/ packages/
      - run: ruff format --check apps/api/ packages/
      - run: |
          pytest apps/api/tests/ packages/db/tests/ \
            --tb=short -q \
            --cov=apps/api --cov=packages \
            --cov-report=xml
        env:
          DATABASE_URL: postgresql+asyncpg://lexibel:test@localhost:5432/lexibel_test
          REDIS_URL: redis://localhost:6379/0

  # ── Lint & Test Frontend ──
  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - run: npm install -g pnpm
      - run: pnpm install
      - run: pnpm --filter web lint
      - run: pnpm --filter web build
      - run: pnpm --filter web test -- --run

  # ── Security Scan ──
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: aquasecurity/trivy-action@master
        with:
          scan-type: fs
          scan-ref: .
          severity: CRITICAL,HIGH

  # ── Build & Push Docker Images ──
  build:
    needs: [backend, frontend, security]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v5
        with:
          context: .
          file: infra/docker/Dockerfile.api
          push: true
          tags: ${{ env.IMAGE_PREFIX }}-api:${{ github.sha }},${{ env.IMAGE_PREFIX }}-api:latest
      - uses: docker/build-push-action@v5
        with:
          context: .
          file: infra/docker/Dockerfile.web
          push: true
          tags: ${{ env.IMAGE_PREFIX }}-web:${{ github.sha }},${{ env.IMAGE_PREFIX }}-web:latest

  # ── Deploy to Production ──
  deploy:
    needs: build
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.PROD_HOST }}
          username: lexibel
          key: ${{ secrets.PROD_SSH_KEY }}
          script: |
            cd /home/lexibel/lexibel
            git pull origin main
            docker compose -f docker-compose.prod.yml pull
            docker compose -f docker-compose.prod.yml up -d --remove-orphans
            docker system prune -f
EOF
```

---

### STEP 8: GitHub Secrets to Configure

Go to **github.com/clixite/lexibel → Settings → Secrets → Actions** and add:

| Secret Name | Value |
|---|---|
| `PROD_HOST` | `76.13.46.55` |
| `PROD_SSH_KEY` | Content of your SSH private key for `lexibel` user |
| `POSTGRES_PASSWORD` | A strong production password |
| `SECRET_KEY` | Random 64-char hex string for JWT signing |

---

### STEP 9: Production Docker Compose

```bash
cat > docker-compose.prod.yml << 'EOF'
version: "3.9"

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: lexibel
      POSTGRES_USER: lexibel
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - /home/lexibel/lexibel-data/postgres:/var/lib/postgresql/data
    restart: always
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U lexibel"]
      interval: 10s

  redis:
    image: redis:7-alpine
    volumes:
      - /home/lexibel/lexibel-data/redis:/data
    restart: always

  qdrant:
    image: qdrant/qdrant:latest
    volumes:
      - /home/lexibel/lexibel-data/qdrant:/qdrant/storage
    restart: always

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: lexibel
      MINIO_ROOT_PASSWORD: ${MINIO_PASSWORD}
    volumes:
      - /home/lexibel/lexibel-data/minio:/data
    restart: always

  api:
    image: ghcr.io/clixite/lexibel-api:latest
    environment:
      DATABASE_URL: postgresql+asyncpg://lexibel:${POSTGRES_PASSWORD}@postgres:5432/lexibel
      REDIS_URL: redis://redis:6379/0
      QDRANT_URL: http://qdrant:6333
      MINIO_ENDPOINT: minio:9000
      MINIO_ACCESS_KEY: lexibel
      MINIO_SECRET_KEY: ${MINIO_PASSWORD}
      SECRET_KEY: ${SECRET_KEY}
      ENVIRONMENT: production
    ports:
      - "127.0.0.1:8000:8000"
    depends_on:
      postgres: { condition: service_healthy }
    restart: always

  worker:
    image: ghcr.io/clixite/lexibel-api:latest
    environment:
      DATABASE_URL: postgresql+asyncpg://lexibel:${POSTGRES_PASSWORD}@postgres:5432/lexibel
      REDIS_URL: redis://redis:6379/0
    depends_on:
      postgres: { condition: service_healthy }
    command: celery -A apps.workers.main worker -l info
    restart: always

  web:
    image: ghcr.io/clixite/lexibel-web:latest
    environment:
      NEXT_PUBLIC_API_URL: https://lexibel.clixite.cloud/api/v1
    ports:
      - "127.0.0.1:3000:3000"
    restart: always
EOF
```

---

### STEP 10: .gitignore & .env

```bash
cat > .gitignore << 'EOF'
# Dependencies
node_modules/
__pycache__/
*.pyc
.venv/
venv/

# Build
.next/
dist/
*.egg-info/

# Environment
.env
.env.local
.env.production

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db

# Docker volumes
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

cat > .env.example << 'EOF'
# Copy to .env and fill in values
POSTGRES_PASSWORD=change_me_strong_password
MINIO_PASSWORD=change_me_strong_password
SECRET_KEY=generate_with_openssl_rand_hex_64
ENVIRONMENT=development
EOF
```

---

### STEP 11: First Push

```bash
# From lexibel/ root
git add .
git commit -m "LXB-001: Initialize monorepo structure with Docker, CI/CD, and documentation"
git push -u origin main
```

---

### STEP 12: Start Claude Code Development

```bash
# From lexibel/ root
claude

# First prompt to Claude Code:
# "Read CLAUDE.md and docs/05_LexiBel_Implementation_Playbook.docx.
#  Start with ticket LXB-005: Create PostgreSQL schema with RLS
#  for tenants, users, and audit_logs tables.
#  Include Alembic migrations and pytest cross-tenant isolation tests."
```

---

## Execution Checklist

| # | Task | Command / Action | Status |
|---|---|---|---|
| 1 | Install prerequisites | Node 20, Python 3.11, Docker, pnpm, Claude Code | ☐ |
| 2 | Create GitHub repo | github.com/clixite/lexibel (private) | ☐ |
| 3 | SSH key setup | ssh-keygen + add to GitHub + server | ☐ |
| 4 | Init monorepo locally | mkdir, turbo, CLAUDE.md | ☐ |
| 5 | Copy docs to docs/ | 6 Word files from Seagate | ☐ |
| 6 | Create Docker configs | docker-compose.yml + Dockerfiles | ☐ |
| 7 | Create CI/CD pipeline | .github/workflows/ci.yml | ☐ |
| 8 | First commit + push | git push origin main | ☐ |
| 9 | Server: create user | adduser lexibel + SSH key | ☐ |
| 10 | Server: install Docker | curl get.docker.com | ☐ |
| 11 | Server: nginx config | lexibel.clixite.cloud + certbot SSL | ☐ |
| 12 | Server: clone repo | git clone + docker-compose.prod.yml | ☐ |
| 13 | GitHub: add secrets | PROD_HOST, PROD_SSH_KEY, passwords | ☐ |
| 14 | Test full pipeline | Push to main → CI → Deploy | ☐ |
| 15 | Start Claude Code | Sprint 0, ticket LXB-005 | ☐ |

---

## Security Reminders

1. **CHANGE YOUR SERVER PASSWORD IMMEDIATELY** — it was shared in clear text
2. Use SSH keys, disable password authentication
3. Never commit .env files
4. Use GitHub Secrets for all sensitive values
5. Production PostgreSQL password should be 32+ chars random
6. Enable fail2ban on the server
7. Keep Docker images updated (Trivy scans in CI)

---

## Development Workflow (Daily)

```
1. Open Claude Code in lexibel/ directory
2. Reference a ticket from the Playbook (e.g., LXB-012)
3. Claude Code reads CLAUDE.md + relevant docs
4. Develop feature with tests
5. git commit -m "LXB-012: Cases CRUD with RLS and conflict check"
6. git push → GitHub Actions runs CI
7. If main branch: auto-deploys to lexibel.clixite.cloud
8. Verify on production
```
