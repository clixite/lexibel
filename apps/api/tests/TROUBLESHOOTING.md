# Troubleshooting Guide - Integration Tests

## Common Issues and Solutions

### 1. Import Error: `cannot import name 'VECTOR'`

**Error:**
```
ImportError: cannot import name 'VECTOR' from 'sqlalchemy.dialects.postgresql'
```

**Cause:** Missing `pgvector` extension for SQLAlchemy.

**Solution:**
```bash
pip install pgvector
# or
pip install sqlalchemy[postgresql_pgvector]
```

---

### 2. Module Not Found: `apps.api`

**Error:**
```
ModuleNotFoundError: No module named 'apps'
```

**Cause:** Python path not configured correctly.

**Solution:**
```bash
# Run from project root
cd F:/LexiBel

# Or add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:F:/LexiBel"
pytest apps/api/tests/test_integrations.py
```

---

### 3. Async Test Warnings

**Warning:**
```
RuntimeWarning: coroutine 'test_xxx' was never awaited
```

**Cause:** Missing `@pytest.mark.asyncio` decorator.

**Solution:**
Ensure all async tests have the decorator:
```python
@pytest.mark.asyncio
async def test_my_async_function():
    result = await my_function()
    assert result
```

---

### 4. Database Connection Errors

**Error:**
```
sqlalchemy.exc.OperationalError: could not connect to server
```

**Cause:** Tests trying to connect to real database instead of mocks.

**Solution:**
Set test database URL in environment:
```bash
export DATABASE_URL=sqlite+aiosqlite:///:memory:
```

Or use the provided test script:
```bash
./apps/api/tests/test_run.sh
```

---

### 5. HMAC Signature Validation Fails

**Error:**
```
AssertionError: assert 401 == 200
```

**Cause:** Webhook secret mismatch between test and service.

**Solution:**
Ensure secrets match in test environment:
```python
PLAUD_SECRET = "plaud-dev-secret"
```

And in environment variables:
```bash
export PLAUD_WEBHOOK_SECRET=plaud-dev-secret
```

---

### 6. Mock Not Working

**Error:**
```
AttributeError: 'MagicMock' object has no attribute 'xxx'
```

**Cause:** Incomplete mock setup.

**Solution:**
Ensure all required methods are mocked:
```python
mock_client = AsyncMock()
mock_client.request = AsyncMock(return_value=MagicMock(
    status_code=200,
    json=lambda: {"data": "value"}
))
mock_client.__aenter__ = AsyncMock(return_value=mock_client)
mock_client.__aexit__ = AsyncMock()
```

---

### 7. Test Timeout

**Error:**
```
asyncio.TimeoutError: Test timed out
```

**Cause:** Async operation not properly mocked or actual network call.

**Solution:**
Verify all HTTP calls are mocked:
```python
with patch('httpx.AsyncClient') as MockClient:
    # Mock setup
    test_code()
```

---

### 8. Seed Data Test Fails

**Error:**
```
AssertionError: Expected at least 3 CallRecords, got 0
```

**Cause:** Seed script not run or database not initialized.

**Solution:**
Run seed manually first:
```bash
cd F:/LexiBel
python -m apps.api.scripts.seed_demo_data
```

Or skip seed test:
```bash
pytest apps/api/tests/test_integrations.py -k "not seed"
```

---

### 9. OAuth Encryption Key Error

**Error:**
```
ValueError: Encryption key must be exactly 32 bytes
```

**Cause:** Missing or invalid `OAUTH_ENCRYPTION_KEY`.

**Solution:**
Set a valid 32-byte key:
```bash
export OAUTH_ENCRYPTION_KEY="test-encryption-key-32bytes!!!"
```

---

### 10. Idempotency Store Issues

**Error:**
```
KeyError: 'plaud:trans-xxx'
```

**Cause:** Idempotency store not reset between tests.

**Solution:**
Call reset function in test setup:
```python
from apps.api.services.webhook_service import reset_idempotency_store

@pytest.fixture(autouse=True)
def reset_store():
    reset_idempotency_store()
```

Or manually in each test:
```python
def test_my_webhook():
    reset_idempotency_store()
    # test code
```

---

## Running Tests in Isolation

To debug a specific test:

```bash
# Run single test with verbose output
pytest apps/api/tests/test_integrations.py::test_ringover_client_list_calls -vv

# Run with print statements visible
pytest apps/api/tests/test_integrations.py::test_xxx -s

# Run with full traceback
pytest apps/api/tests/test_integrations.py::test_xxx --tb=long

# Run with debugger on failure
pytest apps/api/tests/test_integrations.py::test_xxx --pdb
```

---

## Dependencies Check

Ensure all required packages are installed:

```bash
pip list | grep -E "(pytest|httpx|google-auth|sqlalchemy|fastapi)"
```

Expected output:
```
fastapi                 0.109.0
google-auth             2.27.0
google-auth-oauthlib    1.2.0
httpx                   0.26.0
pytest                  8.0.0
pytest-asyncio          0.23.0
sqlalchemy              2.0.25
```

---

## Environment Setup Checklist

Before running tests, verify:

- [ ] Python 3.11+ installed
- [ ] All dependencies installed: `pip install -r requirements.txt`
- [ ] Working directory is project root: `cd F:/LexiBel`
- [ ] Environment variables set (see `test_run.sh`)
- [ ] No other pytest processes running
- [ ] Database migrations applied (if testing with real DB)

---

## Getting Help

If tests still fail after following this guide:

1. Check the test output carefully for the exact error
2. Review the mock setup in the failing test
3. Verify environment variables are set correctly
4. Try running tests individually to isolate the issue
5. Check if the issue is in the test or the code being tested

---

## Clean Test Environment

To start fresh:

```bash
# Clear Python cache
find F:/LexiBel -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null

# Clear pytest cache
rm -rf F:/LexiBel/.pytest_cache

# Reinstall dependencies
pip install --force-reinstall -r requirements.txt

# Run tests
./apps/api/tests/test_run.sh
```

---

**Last Updated**: 2026-02-17
