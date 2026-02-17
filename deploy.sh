#!/bin/bash
# LexiBel Production Deployment Script
# Usage: ./deploy.sh
# Usage with seed data: SEED_DATA=true ./deploy.sh
# Make executable: chmod +x deploy.sh

set -e  # Exit on error

echo "🚀 LexiBel Deployment Script"
echo "=============================="

# 1. Git pull
echo "📦 Pulling latest changes..."
git pull origin main

# 2. Docker build (no cache for clean build)
echo "🐳 Building Docker images..."
docker compose build --no-cache

# 3. Run migrations
echo "🗄️  Running database migrations..."
docker compose exec -T api alembic upgrade head

# 4. Seed demo data (only if DB is empty, use flag)
if [ "$SEED_DATA" = "true" ]; then
    echo "🌱 Seeding demo data..."
    docker compose exec -T api python -m apps.api.scripts.seed_demo_data
fi

# 5. Restart services
echo "♻️  Restarting services..."
docker compose up -d

# 6. Health check
echo "🏥 Health check..."
sleep 5
curl -f https://lexibel.clixite.cloud/api/v1/health || echo "⚠️  Health check failed!"

# 7. Show status
echo ""
echo "✅ Deployment complete!"
echo ""
echo "📊 Service status:"
docker compose ps

echo ""
echo "🔗 URLs de test:"
echo "  - API Health: https://lexibel.clixite.cloud/api/v1/health"
echo "  - API Docs: https://lexibel.clixite.cloud/api/v1/docs"
echo "  - Frontend: https://lexibel.clixite.cloud"
echo ""
