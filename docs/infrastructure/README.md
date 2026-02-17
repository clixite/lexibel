# LexiBel Infrastructure Overview

Complete infrastructure stack for the LexiBel AI-powered legal management platform.

## Components

### Core Databases

| Service | Image | Ports | Purpose |
|---------|-------|-------|---------|
| **PostgreSQL 16** | `postgres:16-alpine` | 5434:5432 | Main relational database |
| **Redis 7** | `redis:7-alpine` | 6381:6379 | Cache & message broker |
| **Qdrant** | `qdrant/qdrant:latest` | 6333, 6334 | Vector embeddings (RAG) |
| **Neo4j 5** | `neo4j:5-community` | 7474, 7687 | Knowledge graph (conflicts) |

### Storage & Services

| Service | Image | Ports | Purpose |
|---------|-------|-------|---------|
| **MinIO** | `minio/minio:latest` | 9000, 9001 | S3-compatible object storage |
| **vLLM** (optional) | Custom build | 8001:8000 | Multi-LoRA inference |

### Application Layer

| Service | Ports | Purpose |
|---------|-------|---------|
| **API** (FastAPI) | 8000 | REST API backend |
| **Worker** (Celery) | - | Async task processing |
| **Web** (Next.js) | 3000 | Frontend application |

### Monitoring (Optional)

| Service | Ports | Purpose |
|---------|-------|---------|
| **Prometheus** | 9090 | Metrics collection |
| **Grafana** | 3200 | Metrics visualization |

## Quick Start

### 1. Start Core Services

```bash
cd /f/LexiBel
docker compose up -d postgres redis qdrant neo4j minio
```

### 2. Start Application

```bash
docker compose up -d api worker web
```

### 3. Start Monitoring (Optional)

```bash
docker compose up -d prometheus grafana
```

### 4. Enable vLLM (GPU Required)

```bash
ENABLE_VLLM=true docker compose --profile gpu up -d vllm
```

## Port Mappings

### Database Access

- **PostgreSQL**: `localhost:5434`
  - Database: `lexibel`
  - User: `lexibel`
  - Password: `lexibel_dev_2026` (default)

- **Redis**: `localhost:6381`

- **Qdrant**:
  - REST API: `http://localhost:6333`
  - gRPC: `localhost:6334`
  - Dashboard: `http://localhost:6333/dashboard`

- **Neo4j**:
  - Browser: `http://localhost:7474`
  - Bolt: `bolt://localhost:7687`
  - User: `neo4j`
  - Password: `lexibel2026` (default)

### Storage & Services

- **MinIO**:
  - API: `http://localhost:9000`
  - Console: `http://localhost:9001`
  - User: `lexibel`
  - Password: `lexibel_dev_2026` (default)

- **vLLM**: `http://localhost:8001/v1` (OpenAI-compatible)

### Application

- **API**: `http://localhost:8000`
  - Docs: `http://localhost:8000/docs`
  - Metrics: `http://localhost:8000/metrics`

- **Web**: `http://localhost:3000`

### Monitoring

- **Prometheus**: `http://localhost:9090`
- **Grafana**: `http://localhost:3200`

## Environment Variables

Create `.env` file in project root:

```bash
# PostgreSQL
POSTGRES_PASSWORD=lexibel_dev_2026

# Neo4j
NEO4J_PASSWORD=lexibel2026

# MinIO
MINIO_PASSWORD=lexibel_dev_2026

# API
SECRET_KEY=your-secret-key-here
CORS_ORIGINS=http://localhost:3000

# vLLM (optional)
VLLM_MODEL=mistralai/Mistral-7B-Instruct-v0.2
VLLM_MAX_CTX=8192
VLLM_TP=1

# Next.js
NEXTAUTH_SECRET=your-nextauth-secret
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

## Health Checks

Check service health:

```bash
# PostgreSQL
docker compose exec postgres pg_isready -U lexibel -d lexibel

# Redis
docker compose exec redis redis-cli ping

# Qdrant
curl http://localhost:6333/healthz

# Neo4j
curl http://localhost:7474/

# API
curl http://localhost:8000/health
```

## Volume Management

### List Volumes

```bash
docker volume ls | grep lexibel
```

### Backup PostgreSQL

```bash
docker compose exec postgres pg_dump -U lexibel lexibel > backup.sql
```

### Restore PostgreSQL

```bash
cat backup.sql | docker compose exec -T postgres psql -U lexibel lexibel
```

### Clear All Data (DESTRUCTIVE)

```bash
docker compose down -v
```

## Detailed Guides

- [Neo4j Setup](./neo4j-setup.md) - Knowledge graph configuration
- [Qdrant Setup](./qdrant-setup.md) - Vector database setup
- [Monitoring](./monitoring.md) - Prometheus + Grafana configuration

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker compose logs <service-name>

# Restart service
docker compose restart <service-name>

# Full rebuild
docker compose up -d --build <service-name>
```

### Database Connection Issues

```bash
# Verify PostgreSQL is listening
docker compose exec postgres psql -U lexibel -d lexibel -c "SELECT 1"

# Check network
docker network inspect lexibel_default
```

### Out of Disk Space

```bash
# Clean unused Docker resources
docker system prune -a --volumes

# Check volume sizes
docker system df -v
```

## Production Considerations

1. **Secrets Management**: Use Docker secrets or external secret managers
2. **SSL/TLS**: Enable encryption for all services
3. **Backups**: Implement automated backup strategy
4. **Resource Limits**: Set memory and CPU limits in docker-compose.yml
5. **Monitoring**: Enable full monitoring stack
6. **High Availability**: Use replicated services and load balancing
