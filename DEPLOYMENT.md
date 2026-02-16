# LexiBel Production Deployment Guide

## Quick Deploy

SSH to the production server and run the deployment script:

```bash
ssh root@76.13.46.55
cd /opt/lexibel
bash deploy.sh
```

The script will:
1. Pull latest code from GitHub
2. Update docker-compose.yml configuration
3. Rebuild containers (no cache)
4. Start all services
5. Create database tables
6. Run smoke tests

## Manual Deployment Steps

If you prefer to run commands manually:

### 1. Pull Latest Code
```bash
cd /opt/lexibel
git stash
git pull origin main
```

### 2. Configure Docker Compose

Ensure docker-compose.yml has these settings for web service on port 3200.

### 3. Build and Deploy
```bash
docker compose down
docker compose build --no-cache api web
docker compose up -d
```

### 4. Smoke Tests

Health: https://lexibel.clixite.cloud/api/v1/health

Login: nicolas@clixite.be / LexiBel2026!

## Troubleshooting

View logs: `docker compose logs -f`

Check status: `docker compose ps`
