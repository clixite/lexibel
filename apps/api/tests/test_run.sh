#!/bin/bash
# Test runner script for integration tests
# Usage: ./test_run.sh

set -e  # Exit on error

echo "=========================================="
echo "Running Integration Tests"
echo "=========================================="
echo ""

# Change to project root
cd "$(dirname "$0")/../../.."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Set test environment variables
export ENVIRONMENT=test
export RINGOVER_API_KEY=test-api-key
export PLAUD_WEBHOOK_SECRET=plaud-dev-secret
export RINGOVER_WEBHOOK_SECRET=ringover-dev-secret
export GOOGLE_CLIENT_ID=test-google-client-id
export GOOGLE_CLIENT_SECRET=test-google-secret
export MICROSOFT_CLIENT_ID=test-microsoft-client-id
export MICROSOFT_CLIENT_SECRET=test-microsoft-secret
export OAUTH_ENCRYPTION_KEY=test-encryption-key-32bytes!!!
export DATABASE_URL=sqlite+aiosqlite:///:memory:

echo "Environment: $ENVIRONMENT"
echo "Running pytest on test_integrations.py..."
echo ""

# Run pytest with verbose output and stop on first failure
pytest apps/api/tests/test_integrations.py \
    -v \
    -x \
    --tb=short \
    --color=yes \
    --disable-warnings

echo ""
echo "=========================================="
echo "Integration Tests Complete"
echo "=========================================="
