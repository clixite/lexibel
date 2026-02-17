#!/bin/bash
# Script to run Alembic migrations for LexiBel

set -e

echo "🔍 Checking Docker..."
if ! docker ps > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop and try again."
    exit 1
fi

echo "✅ Docker is running"

echo "🔍 Checking PostgreSQL container..."
if ! docker ps | grep -q postgres; then
    echo "⚠️  PostgreSQL container not running. Starting services..."
    cd /f/LexiBel
    docker compose up -d postgres redis
    echo "⏳ Waiting 5 seconds for PostgreSQL to be ready..."
    sleep 5
fi

echo "✅ PostgreSQL is running"

echo "🚀 Running Alembic migrations..."
cd /f/LexiBel
alembic upgrade head

echo "✅ Migrations completed!"

echo "📊 Checking tables..."
docker exec lexibel-postgres-1 psql -U lexibel -d lexibel -c "\dt"

echo "✅ All done!"
