# Integration Tests - LexiBel

## Overview

This document describes the integration tests for LexiBel's external service integrations.

## Test File: `test_integrations.py`

### Coverage

The integration test suite covers:

1. **Ringover API Client** (`ringover_client.py`)
   - HTTP request handling with authentication
   - Pagination and filtering
   - Retry logic with exponential backoff
   - Error handling (timeouts, API errors)
   - Call recording retrieval

2. **Plaud Webhook Handler** (`webhooks/plaud.py`)
   - HMAC-SHA256 signature verification
   - Webhook payload validation
   - Database writes (Transcription + TranscriptionSegments)
   - Idempotency protection
   - InteractionEvent creation

3. **Google OAuth Service** (`google_oauth_service.py`)
   - Authorization URL generation
   - OAuth code-to-token exchange
   - Token refresh flow
   - Token encryption and storage

4. **Microsoft OAuth Service** (`microsoft_oauth_service.py`)
   - Azure AD OAuth URL generation
   - Microsoft Graph API token exchange
   - Token refresh with Graph API
   - Token encryption and storage

5. **Seed Data Validation** (`scripts/seed_demo_data.py`)
   - Verification of expected record counts
   - Data integrity checks

## Running the Tests

### Quick Start

```bash
# Run all integration tests
./apps/api/tests/test_run.sh
```

### Manual Execution

```bash
# Run with pytest directly
pytest apps/api/tests/test_integrations.py -v -x

# Run specific test
pytest apps/api/tests/test_integrations.py::test_ringover_client_list_calls -v

# Run with coverage
pytest apps/api/tests/test_integrations.py --cov=apps.api.services --cov-report=html
```

## Test Organization

### Ringover Client Tests (6 tests)

- `test_ringover_client_list_calls`: Validates pagination and response parsing
- `test_ringover_client_with_filters`: Tests date/type filters
- `test_ringover_client_error_handling`: Tests retry logic on timeout
- `test_ringover_client_max_retries_exceeded`: Validates retry limit
- `test_ringover_client_api_error_no_retry`: Tests immediate failure on API errors
- `test_ringover_client_get_recording`: Tests recording URL retrieval

### Plaud Webhook Tests (5 tests)

- `test_plaud_webhook_valid_signature`: Full webhook processing flow
- `test_plaud_webhook_invalid_signature`: Security validation (401)
- `test_plaud_webhook_missing_signature`: Missing header validation (401)
- `test_plaud_webhook_creates_transcription`: DB write verification
- `test_plaud_webhook_idempotency`: Duplicate detection

### Google OAuth Tests (3 tests)

- `test_google_oauth_auth_url`: URL generation with PKCE
- `test_google_oauth_token_exchange`: Code-to-token flow
- `test_google_oauth_token_refresh`: Refresh token flow

### Microsoft OAuth Tests (3 tests)

- `test_microsoft_oauth_auth_url`: Azure AD URL generation
- `test_microsoft_oauth_token_exchange`: Graph API token exchange
- `test_microsoft_oauth_token_refresh`: Token refresh flow

### Seed Data Test (1 test)

- `test_seed_data_counts`: Validates demo data creation

## Mocking Strategy

### HTTP Requests

All external HTTP calls are mocked using `unittest.mock.AsyncMock`:

```python
mock_client = AsyncMock()
mock_client.request = AsyncMock(return_value=MagicMock(
    status_code=200,
    json=lambda: {"data": "..."}
))
```

### Database Operations

Database sessions are mocked to avoid actual DB writes during most tests:

```python
mock_session = AsyncMock()
mock_session.commit = AsyncMock()
mock_session.execute = AsyncMock(return_value=...)
```

### Environment Variables

Test environment variables are injected via `patch.dict`:

```python
with patch.dict("os.environ", {
    "RINGOVER_API_KEY": "test-key",
    "PLAUD_WEBHOOK_SECRET": "test-secret"
}):
    # test code
```

## Environment Variables Required

For the test suite to run, the following environment variables should be set:

```bash
# API Keys (mocked in tests)
RINGOVER_API_KEY=test-api-key
PLAUD_WEBHOOK_SECRET=plaud-dev-secret
RINGOVER_WEBHOOK_SECRET=ringover-dev-secret

# OAuth Credentials (mocked)
GOOGLE_CLIENT_ID=test-google-client-id
GOOGLE_CLIENT_SECRET=test-google-secret
MICROSOFT_CLIENT_ID=test-microsoft-client-id
MICROSOFT_CLIENT_SECRET=test-microsoft-secret
OAUTH_ENCRYPTION_KEY=test-encryption-key-32bytes!!!

# Database (in-memory for tests)
DATABASE_URL=sqlite+aiosqlite:///:memory:
```

These are automatically set by the `test_run.sh` script.

## Test Patterns and Best Practices

### Async Tests

All async functions use `@pytest.mark.asyncio`:

```python
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_call()
    assert result is not None
```

### HMAC Signature Testing

Webhook tests use a helper function to generate valid signatures:

```python
def _sign_hmac(payload: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
```

### Idempotency Testing

Tests reset the idempotency store before webhook tests:

```python
from apps.api.services.webhook_service import reset_idempotency_store

reset_idempotency_store()
```

## Troubleshooting

### Test Failures

1. **Import Errors**: Ensure all dependencies are installed:
   ```bash
   pip install -r requirements.txt
   pip install pytest pytest-asyncio httpx
   ```

2. **Database Errors**: The seed data test may fail if database models are incomplete. This is expected during early development.

3. **Mock Issues**: If mocks don't work as expected, verify the patch paths match the actual import structure.

### Common Issues

- **Async warnings**: Make sure all async tests use `@pytest.mark.asyncio`
- **Patch paths**: Use the full import path where the object is used, not where it's defined
- **Environment variables**: Check that all required env vars are set in `test_run.sh`

## Adding New Tests

When adding new integration tests:

1. Follow the existing test structure
2. Mock all external HTTP calls
3. Use descriptive test names: `test_<service>_<scenario>`
4. Add docstrings explaining what is being tested
5. Use clear assertions with helpful error messages
6. Update this README with new test coverage

## CI/CD Integration

These tests are designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions step
- name: Run Integration Tests
  run: |
    export ENVIRONMENT=test
    pytest apps/api/tests/test_integrations.py -v --tb=short
```

## Performance

Expected test execution time: **< 5 seconds**

All HTTP calls are mocked, so tests run entirely in-memory without network delays.

## Maintenance

- Review tests quarterly to ensure they match current API contracts
- Update mocked responses when external APIs change
- Add regression tests for any production bugs found
- Keep environment variables in sync with production requirements
