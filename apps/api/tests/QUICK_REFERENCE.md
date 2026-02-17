# Integration Tests - Quick Reference Commands

## Run All Tests

```bash
# Using test script (recommended)
./apps/api/tests/test_run.sh

# Using pytest directly
pytest apps/api/tests/test_integrations.py -v -x
```

---

## Run Specific Service Tests

```bash
# Ringover tests only (6 tests)
pytest apps/api/tests/test_integrations.py -k "ringover" -v

# Plaud webhook tests only (5 tests)
pytest apps/api/tests/test_integrations.py -k "plaud" -v

# Google OAuth tests only (3 tests)
pytest apps/api/tests/test_integrations.py -k "google" -v

# Microsoft OAuth tests only (3 tests)
pytest apps/api/tests/test_integrations.py -k "microsoft" -v

# OAuth tests (both Google and Microsoft)
pytest apps/api/tests/test_integrations.py -k "oauth" -v

# Seed data test only
pytest apps/api/tests/test_integrations.py -k "seed" -v
```

---

## Run Single Test

```bash
# Specific test by name
pytest apps/api/tests/test_integrations.py::test_ringover_client_list_calls -v
pytest apps/api/tests/test_integrations.py::test_plaud_webhook_valid_signature -v
pytest apps/api/tests/test_integrations.py::test_google_oauth_auth_url -v
```

---

## Debug Options

```bash
# Show print statements
pytest apps/api/tests/test_integrations.py -s

# Show local variables on failure
pytest apps/api/tests/test_integrations.py --showlocals

# Full traceback
pytest apps/api/tests/test_integrations.py --tb=long

# Stop on first failure
pytest apps/api/tests/test_integrations.py -x

# Enter debugger on failure
pytest apps/api/tests/test_integrations.py --pdb

# Verbose output with full test names
pytest apps/api/tests/test_integrations.py -vv
```

---

## Coverage Reports

```bash
# Run with coverage
pytest apps/api/tests/test_integrations.py \
    --cov=apps.api.services \
    --cov=apps.api.webhooks \
    --cov-report=term

# HTML coverage report
pytest apps/api/tests/test_integrations.py \
    --cov=apps.api.services \
    --cov=apps.api.webhooks \
    --cov-report=html

# Then open: htmlcov/index.html

# XML coverage (for CI)
pytest apps/api/tests/test_integrations.py \
    --cov=apps.api \
    --cov-report=xml
```

---

## Test Performance

```bash
# Show slowest tests
pytest apps/api/tests/test_integrations.py --durations=10

# Show all test durations
pytest apps/api/tests/test_integrations.py --durations=0

# Profile tests
pytest apps/api/tests/test_integrations.py --profile
```

---

## Filter Tests

```bash
# Run async tests only
pytest apps/api/tests/test_integrations.py -m asyncio

# Skip slow tests
pytest apps/api/tests/test_integrations.py -m "not slow"

# Run only webhook tests
pytest apps/api/tests/test_integrations.py -k "webhook"

# Run only client tests
pytest apps/api/tests/test_integrations.py -k "client"
```

---

## Test Output Formats

```bash
# Quiet mode (minimal output)
pytest apps/api/tests/test_integrations.py -q

# Verbose mode
pytest apps/api/tests/test_integrations.py -v

# Very verbose mode
pytest apps/api/tests/test_integrations.py -vv

# Show test summary
pytest apps/api/tests/test_integrations.py -ra

# No color output
pytest apps/api/tests/test_integrations.py --color=no
```

---

## Parallel Execution

```bash
# Install pytest-xdist first
pip install pytest-xdist

# Run tests in parallel (4 workers)
pytest apps/api/tests/test_integrations.py -n 4

# Auto-detect CPU count
pytest apps/api/tests/test_integrations.py -n auto
```

---

## CI/CD Commands

```bash
# CI mode (exit code 0 on success)
pytest apps/api/tests/test_integrations.py \
    --tb=short \
    --strict-markers \
    --junit-xml=test-results.xml

# With coverage for CI
pytest apps/api/tests/test_integrations.py \
    --cov=apps.api \
    --cov-report=xml \
    --cov-report=term \
    --junit-xml=test-results.xml
```

---

## Maintenance Commands

```bash
# Check imports
python -c "from apps.api.tests.test_integrations import *"

# Format with Ruff
ruff format apps/api/tests/test_integrations.py

# Lint with Ruff
ruff check apps/api/tests/test_integrations.py

# Fix auto-fixable issues
ruff check apps/api/tests/test_integrations.py --fix

# Count tests
grep -c "^async def test_\|^def test_" apps/api/tests/test_integrations.py

# List all test names
grep "^async def test_\|^def test_" apps/api/tests/test_integrations.py
```

---

## Environment Setup

```bash
# Set test environment variables
export ENVIRONMENT=test
export RINGOVER_API_KEY=test-api-key
export PLAUD_WEBHOOK_SECRET=plaud-dev-secret
export GOOGLE_CLIENT_ID=test-google-client-id
export GOOGLE_CLIENT_SECRET=test-google-secret
export MICROSOFT_CLIENT_ID=test-microsoft-client-id
export MICROSOFT_CLIENT_SECRET=test-microsoft-secret
export OAUTH_ENCRYPTION_KEY=test-encryption-key-32bytes!!!
export DATABASE_URL=sqlite+aiosqlite:///:memory:

# Run tests
pytest apps/api/tests/test_integrations.py -v
```

---

## Clean Up

```bash
# Clear pytest cache
rm -rf .pytest_cache

# Clear Python cache
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null

# Clear coverage files
rm -rf htmlcov .coverage

# Full clean
rm -rf .pytest_cache htmlcov .coverage
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
```

---

## Common Test Patterns

```bash
# Test security features
pytest apps/api/tests/test_integrations.py -k "signature or hmac" -v

# Test error handling
pytest apps/api/tests/test_integrations.py -k "error or invalid" -v

# Test retry logic
pytest apps/api/tests/test_integrations.py -k "retry" -v

# Test idempotency
pytest apps/api/tests/test_integrations.py -k "idempotency" -v
```

---

## Watch Mode

```bash
# Install pytest-watch
pip install pytest-watch

# Watch for changes and re-run tests
ptw apps/api/tests/test_integrations.py

# Watch with clear screen
ptw --clear apps/api/tests/test_integrations.py
```

---

## Generate Test Report

```bash
# Install pytest-html
pip install pytest-html

# Generate HTML report
pytest apps/api/tests/test_integrations.py \
    --html=test-report.html \
    --self-contained-html

# Then open: test-report.html
```

---

## Quick Status Check

```bash
# Run tests and show summary only
pytest apps/api/tests/test_integrations.py -q --tb=no

# Count passing/failing tests
pytest apps/api/tests/test_integrations.py -q --tb=no | tail -1
```

---

## Docker Testing

```bash
# Build test image
docker build -t lexibel-tests -f Dockerfile.test .

# Run tests in container
docker run --rm lexibel-tests pytest apps/api/tests/test_integrations.py -v

# Run with volume mount (for code changes)
docker run --rm -v $(pwd):/app lexibel-tests \
    pytest apps/api/tests/test_integrations.py -v
```

---

**Last Updated**: 2026-02-17
**Quick Tip**: Use `test_run.sh` for the easiest experience!
