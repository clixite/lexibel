#!/bin/bash
set -e  # Exit on any error

echo "=================================================="
echo "  LexiBel Production Deployment Script"
echo "  Server: 76.13.46.55"
echo "  Domain: lexibel.clixite.cloud"
echo "=================================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

PROJECT_DIR="/opt/lexibel"
cd $PROJECT_DIR

echo -e "${BLUE}[1/9] Pulling latest code from GitHub...${NC}"
git stash
git pull origin main
echo -e "${GREEN}✓ Code updated${NC}"
echo ""

echo -e "${BLUE}[2/9] Updating docker-compose.yml configuration...${NC}"
# Ensure web service runs on port 3200 (not 3000, conflict with welaw)
sed -i 's/"3000:3000"/"3200:3000"/' docker-compose.yml || true

# Verify critical environment variables are set
if ! grep -q "NEXTAUTH_SECRET" docker-compose.yml; then
  echo -e "${RED}WARNING: NEXTAUTH_SECRET not found in docker-compose.yml${NC}"
  echo "Please add it manually to the web service environment section."
fi

echo -e "${GREEN}✓ Configuration updated${NC}"
echo ""

echo -e "${BLUE}[3/9] Stopping existing containers...${NC}"
docker compose down
echo -e "${GREEN}✓ Containers stopped${NC}"
echo ""

echo -e "${BLUE}[4/9] Building API container (no cache)...${NC}"
docker compose build --no-cache api
echo -e "${GREEN}✓ API built${NC}"
echo ""

echo -e "${BLUE}[5/9] Building Web container (no cache)...${NC}"
docker compose build --no-cache web
echo -e "${GREEN}✓ Web built${NC}"
echo ""

echo -e "${BLUE}[6/9] Starting all containers...${NC}"
docker compose up -d
echo -e "${GREEN}✓ Containers started${NC}"
echo ""

echo -e "${BLUE}[7/9] Waiting 30s for services to initialize...${NC}"
sleep 30
echo -e "${GREEN}✓ Services should be ready${NC}"
echo ""

echo -e "${BLUE}[8/9] Creating database tables if needed...${NC}"
docker exec lexibel-api-1 python -c "
import asyncio
from packages.db.session import engine
from packages.db.models import Base

async def create():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print('✓ Tables created/verified')

asyncio.run(create())
" || echo -e "${RED}Note: Table creation may have failed - check if tables already exist${NC}"
echo ""

echo -e "${BLUE}[9/9] Running smoke tests...${NC}"
echo ""

# Test 1: Health check
echo -n "  - API health check... "
HEALTH=$(curl -s https://lexibel.clixite.cloud/api/v1/health || echo "FAIL")
if echo "$HEALTH" | grep -q "ok"; then
  echo -e "${GREEN}✓${NC}"
else
  echo -e "${RED}✗ Failed${NC}"
  echo "    Response: $HEALTH"
fi

# Test 2: Bootstrap admin (will fail if already exists, that's OK)
echo -n "  - Bootstrap admin user... "
BOOTSTRAP=$(curl -s -X POST https://lexibel.clixite.cloud/api/v1/bootstrap/admin \
  -H "Content-Type: application/json" \
  -d '{"email":"nicolas@clixite.be","password":"LexiBel2026!","full_name":"Nicolas Simon"}' 2>&1)

if echo "$BOOTSTRAP" | grep -q "created\|already exists"; then
  echo -e "${GREEN}✓${NC}"
else
  echo -e "${RED}✗ May have failed${NC}"
  echo "    Response: $BOOTSTRAP"
fi

# Test 3: Login
echo -n "  - Login test... "
TOKEN=$(curl -s -X POST https://lexibel.clixite.cloud/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"nicolas@clixite.be","password":"LexiBel2026!"}' | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token','FAIL'))" 2>/dev/null)

if [ "$TOKEN" != "FAIL" ] && [ ! -z "$TOKEN" ]; then
  echo -e "${GREEN}✓${NC}"

  # Test 4: Authenticated API call
  echo -n "  - Cases endpoint (authenticated)... "
  CASES=$(curl -s -H "Authorization: Bearer $TOKEN" \
    -H "X-Tenant-ID: 00000000-0000-4000-a000-000000000001" \
    https://lexibel.clixite.cloud/api/v1/cases)

  if echo "$CASES" | grep -q "items\|total"; then
    echo -e "${GREEN}✓${NC}"
  else
    echo -e "${RED}✗ Failed${NC}"
    echo "    Response: $CASES"
  fi
else
  echo -e "${RED}✗ Failed to get token${NC}"
fi

echo ""
echo -e "${GREEN}=================================================="
echo "  ✓ Deployment Complete!"
echo "=================================================="
echo ""
echo "  🌐 Frontend: https://lexibel.clixite.cloud"
echo "  🔌 API:      https://lexibel.clixite.cloud/api/v1"
echo "  📊 Health:   https://lexibel.clixite.cloud/api/v1/health"
echo ""
echo "  👤 Admin credentials:"
echo "     Email:    nicolas@clixite.be"
echo "     Password: LexiBel2026!"
echo ""
echo "  📝 View logs:"
echo "     docker compose logs -f web"
echo "     docker compose logs -f api"
echo ""
echo "=================================================="
echo -e "${NC}"

# Show running containers
echo -e "${BLUE}Running containers:${NC}"
docker compose ps
