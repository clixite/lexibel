# LexiBel Deployment Guide

## Prerequisites

- Docker Engine 24+ and Docker Compose v2
- A server with at least 8 GB RAM and 4 CPU cores (Ubuntu 22.04+ recommended)
- DNS A record pointing your domain to the server IP
- Git access to the repository

## 1. Clone the Repository

```bash
ssh root@your-server
git clone https://github.com/your-org/lexibel.git /opt/lexibel
cd /opt/lexibel
```

## 2. Configure Environment Variables

Copy the example env and fill in all secrets:

```bash
cp .env.example .env
nano .env
```

Required variables:

| Variable | Description |
|---|---|
| `POSTGRES_PASSWORD` | PostgreSQL password |
| `REDIS_PASSWORD` | Redis requirepass |
| `SECRET_KEY` | JWT signing key (generate with `openssl rand -hex 32`) |
| `NEXTAUTH_SECRET` | NextAuth session secret (generate with `openssl rand -hex 32`) |
| `NEXTAUTH_URL` | Public URL, e.g. `https://lexibel.clixite.cloud` |
| `NEO4J_PASSWORD` | Neo4j database password |
| `MINIO_ROOT_USER` | MinIO admin user |
| `MINIO_ROOT_PASSWORD` | MinIO admin password |
| `LLM_API_KEY` | LLM provider API key (optional) |
| `VLLM_BASE_URL` | vLLM endpoint (optional) |
| `CORS_ORIGINS` | Allowed CORS origins, e.g. `https://lexibel.clixite.cloud` |

The web container also requires:

| Variable | Description |
|---|---|
| `API_URL_INTERNAL` | Internal API URL: `http://api:8000/api/v1` |
| `NEXT_PUBLIC_API_URL` | Public API URL: `https://lexibel.clixite.cloud/api/v1` |
| `AUTH_TRUST_HOST` | Set to `true` for reverse proxy setups |

## 3. Build Images

```bash
docker compose -f infra/docker/docker-compose.prod.yml build
```

This builds the `api` and `web` images from their respective Dockerfiles. All other services use official images.

## 4. Database Migrations

Migrations run automatically on API startup via the FastAPI lifespan handler. No manual migration step is needed.

If you need to run migrations manually:

```bash
docker compose -f infra/docker/docker-compose.prod.yml run --rm api \
  python -m alembic -c packages/db/alembic.ini upgrade head
```

## 5. Start Services

```bash
docker compose -f infra/docker/docker-compose.prod.yml up -d
```

This starts 8 containers:

| Service | Port | Description |
|---|---|---|
| `postgres` | 5432 (internal) | PostgreSQL 16 with RLS |
| `redis` | 6379 (internal) | Redis 7 (cache + Celery broker) |
| `qdrant` | 6333 (internal) | Vector DB for semantic search |
| `neo4j` | 7687 (internal) | Knowledge graph |
| `minio` | 9000 (internal) | S3-compatible document storage |
| `api` | 8000 (internal) | FastAPI backend (2 replicas) |
| `worker` | — | Celery worker (indexing, Peppol, migrations) |
| `web` | 3000 (internal) | Next.js frontend |
| `nginx` | 80, 443 | Reverse proxy with SSL |

## 6. Verify Health

```bash
curl -s https://lexibel.clixite.cloud/api/v1/health | python3 -m json.tool
```

Expected output includes `"status": "healthy"` with all service checks passing.

## 7. SSL Setup with Certbot

If SSL is not yet configured:

```bash
# Install certbot
apt install certbot python3-certbot-nginx

# Obtain certificate
certbot certonly --webroot -w /var/www/certbot \
  -d lexibel.clixite.cloud \
  --email admin@your-domain.com --agree-tos

# Auto-renew (crontab)
echo "0 3 * * * certbot renew --quiet && docker compose -f /opt/lexibel/infra/docker/docker-compose.prod.yml restart nginx" | crontab -
```

Certificate files are mounted into the nginx container at `/etc/letsencrypt`.

## 8. Nginx Configuration

Nginx config files are in `infra/nginx/`:

- `nginx.conf` — main config (worker processes, logging)
- `lexibel.conf` — server block with SSL, proxy_pass to `api:8000` and `web:3000`

Key routing:

```
/api/v1/*  → http://api:8000
/*         → http://web:3000
```

## 9. Updating / Redeploying

```bash
cd /opt/lexibel
git pull origin main

# Rebuild only changed images
docker compose -f infra/docker/docker-compose.prod.yml build --no-cache api web

# Rolling restart
docker compose -f infra/docker/docker-compose.prod.yml up -d
```

Quick deploy (from local machine):

```bash
ssh root@76.13.46.55 "cd /opt/lexibel && git pull && docker compose -f infra/docker/docker-compose.prod.yml build --no-cache api web && docker compose -f infra/docker/docker-compose.prod.yml up -d"
```

## 10. Logs and Debugging

```bash
# All service logs
docker compose -f infra/docker/docker-compose.prod.yml logs -f

# Specific service
docker compose -f infra/docker/docker-compose.prod.yml logs -f api

# Database shell
docker compose -f infra/docker/docker-compose.prod.yml exec postgres psql -U lexibel -d lexibel
```

## 11. Backups

PostgreSQL backup:

```bash
docker compose -f infra/docker/docker-compose.prod.yml exec postgres \
  pg_dump -U lexibel -d lexibel | gzip > backup_$(date +%Y%m%d).sql.gz
```

Volumes to back up: `postgres_data`, `minio_data`, `qdrant_data`, `neo4j_data`.
