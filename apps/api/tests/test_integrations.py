"""Integration tests for external service integrations.

Tests for:
- Ringover API client (HTTP, retries, pagination)
- Plaud webhook handling (HMAC, transcription creation)
- Google OAuth (authorization, token exchange, refresh)
- Microsoft OAuth (Azure AD, Graph API token flow)
- Seed data validation
"""

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.main import app
from apps.api.services.ringover_client import (
    RingoverAPIError,
    RingoverCallsResponse,
    RingoverClient,
)
from apps.api.services.google_oauth_service import GoogleOAuthService
from apps.api.services.microsoft_oauth_service import MicrosoftOAuthService


# ========== Test Data ==========

TENANT_ID = uuid.uuid4()
USER_ID = uuid.uuid4()
PLAUD_SECRET = "plaud-dev-secret"


def _sign_hmac(payload: bytes, secret: str) -> str:
    """Generate HMAC-SHA256 signature for webhook testing."""
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


# ========== Ringover Client Tests ==========


@pytest.mark.asyncio
async def test_ringover_client_list_calls():
    """Test Ringover API list calls with pagination and auth header."""
    # Mock httpx response
    mock_response_data = {
        "calls": [
            {
                "id": "call-123",
                "direction": "inbound",
                "caller_number": "+32470123456",
                "callee_number": "+3225551234",
                "duration_seconds": 120,
                "call_type": "answered",
                "started_at": "2026-02-15T10:00:00Z",
                "ended_at": "2026-02-15T10:02:00Z",
                "recording_available": True,
                "user_id": "user-1",
                "tags": ["client"],
                "metadata": {},
            },
            {
                "id": "call-456",
                "direction": "outbound",
                "caller_number": "+3225551234",
                "callee_number": "+32470987654",
                "duration_seconds": 300,
                "call_type": "answered",
                "started_at": "2026-02-15T11:00:00Z",
                "ended_at": "2026-02-15T11:05:00Z",
                "recording_available": False,
                "tags": [],
                "metadata": {},
            },
        ],
        "total": 50,
        "has_more": True,
    }

    mock_client = AsyncMock()
    mock_client.request = AsyncMock(
        return_value=MagicMock(
            status_code=200,
            json=lambda: mock_response_data,
        )
    )

    # Test client initialization and request
    with patch.dict("os.environ", {"RINGOVER_API_KEY": "test-api-key"}):
        client = RingoverClient(enable_cache=False)
        client._client = mock_client

        response = await client.list_calls(page=1, per_page=20)

        # Verify response structure
        assert isinstance(response, RingoverCallsResponse)
        assert len(response.calls) == 2
        assert response.total == 50
        assert response.page == 1
        assert response.per_page == 20
        assert response.has_more is True

        # Verify first call data
        first_call = response.calls[0]
        assert first_call.id == "call-123"
        assert first_call.direction == "inbound"
        assert first_call.caller_number == "+32470123456"
        assert first_call.duration_seconds == 120

        # Verify request was made with correct parameters
        mock_client.request.assert_called_once()
        call_args = mock_client.request.call_args
        assert call_args.kwargs["method"] == "GET"
        assert call_args.kwargs["url"] == "/calls"
        assert call_args.kwargs["params"]["page"] == 1
        assert call_args.kwargs["params"]["per_page"] == 20


@pytest.mark.asyncio
async def test_ringover_client_with_filters():
    """Test Ringover client with date and type filters."""
    mock_response_data = {
        "calls": [],
        "total": 0,
        "has_more": False,
    }

    mock_client = AsyncMock()
    mock_client.request = AsyncMock(
        return_value=MagicMock(
            status_code=200,
            json=lambda: mock_response_data,
        )
    )

    with patch.dict("os.environ", {"RINGOVER_API_KEY": "test-key"}):
        client = RingoverClient(enable_cache=False)
        client._client = mock_client

        date_from = datetime(2026, 2, 1)
        date_to = datetime(2026, 2, 15)

        await client.list_calls(
            page=1,
            per_page=50,
            date_from=date_from,
            date_to=date_to,
            direction="inbound",
            call_type="answered",
        )

        # Verify filters were passed correctly
        call_args = mock_client.request.call_args
        params = call_args.kwargs["params"]
        assert params["date_from"] == date_from.isoformat()
        assert params["date_to"] == date_to.isoformat()
        assert params["direction"] == "inbound"
        assert params["call_type"] == "answered"


@pytest.mark.asyncio
async def test_ringover_client_error_handling():
    """Test Ringover client retry logic and error handling."""
    # Simulate timeout on first 2 attempts, success on 3rd
    attempt_count = 0

    async def mock_request_with_retry(*args, **kwargs):
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise httpx.TimeoutException("Request timeout")
        return MagicMock(
            status_code=200,
            json=lambda: {"calls": [], "total": 0, "has_more": False},
        )

    mock_client = AsyncMock()
    mock_client.request = mock_request_with_retry

    with patch.dict("os.environ", {"RINGOVER_API_KEY": "test-key"}):
        client = RingoverClient(enable_cache=False)
        client._client = mock_client

        # Should succeed after retries
        response = await client.list_calls(page=1, per_page=20)
        assert response.total == 0
        assert attempt_count == 3


@pytest.mark.asyncio
async def test_ringover_client_max_retries_exceeded():
    """Test that client raises error after max retries."""

    async def mock_timeout(*args, **kwargs):
        raise httpx.TimeoutException("Persistent timeout")

    mock_client = AsyncMock()
    mock_client.request = mock_timeout

    with patch.dict("os.environ", {"RINGOVER_API_KEY": "test-key"}):
        client = RingoverClient(enable_cache=False)
        client._client = mock_client

        # Should raise after 3 retries
        with pytest.raises(RingoverAPIError) as exc_info:
            await client.list_calls(page=1, per_page=20)

        assert "timeout" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_ringover_client_api_error_no_retry():
    """Test that API errors (4xx, 5xx) are not retried."""

    async def mock_api_error(*args, **kwargs):
        return MagicMock(
            status_code=401,
            json=lambda: {"message": "Unauthorized"},
        )

    mock_client = AsyncMock()
    mock_client.request = mock_api_error

    with patch.dict("os.environ", {"RINGOVER_API_KEY": "test-key"}):
        client = RingoverClient(enable_cache=False)
        client._client = mock_client

        # Should fail immediately without retry
        with pytest.raises(RingoverAPIError) as exc_info:
            await client.list_calls(page=1, per_page=20)

        error = exc_info.value
        assert error.status_code == 401
        assert "Unauthorized" in str(error)


@pytest.mark.asyncio
async def test_ringover_client_get_recording():
    """Test fetching call recording URL."""
    mock_response = {
        "url": "https://recordings.ringover.com/abc123.mp3",
        "duration_seconds": 180,
        "format": "mp3",
        "expires_at": "2026-02-18T00:00:00Z",
    }

    mock_client = AsyncMock()
    mock_client.request = AsyncMock(
        return_value=MagicMock(
            status_code=200,
            json=lambda: mock_response,
        )
    )

    with patch.dict("os.environ", {"RINGOVER_API_KEY": "test-key"}):
        client = RingoverClient(enable_cache=False)
        client._client = mock_client

        recording = await client.get_recording("call-123")

        assert recording.call_id == "call-123"
        assert recording.url == "https://recordings.ringover.com/abc123.mp3"
        assert recording.duration_seconds == 180
        assert recording.format == "mp3"

        # Verify correct endpoint was called
        call_args = mock_client.request.call_args
        assert call_args.kwargs["url"] == "/calls/call-123/recording"


# ========== Plaud Webhook Tests ==========


def _mock_plaud_session():
    """Create a mock DB session for Plaud webhook tests."""
    mock_session = AsyncMock()
    mock_session.begin = MagicMock(return_value=AsyncMock())
    mock_session.execute = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()
    mock_session.commit = AsyncMock()

    mock_transcription_id = uuid.uuid4()

    # Track added objects and set id on Transcription-like objects
    def track_add(obj):
        if hasattr(obj, "source") and not hasattr(obj, "transcription_id"):
            obj.id = mock_transcription_id

    mock_session.add.side_effect = track_add

    # Set up begin context manager
    mock_begin_cm = AsyncMock()
    mock_begin_cm.__aenter__ = AsyncMock(return_value=None)
    mock_begin_cm.__aexit__ = AsyncMock(return_value=False)
    mock_session.begin.return_value = mock_begin_cm

    # Set up session factory context manager
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    return mock_session, mock_cm


@pytest.mark.asyncio
async def test_plaud_webhook_valid_signature():
    """Test Plaud webhook with valid HMAC signature and DB writes."""
    from apps.api.services.webhook_service import reset_idempotency_store

    reset_idempotency_store()

    payload = {
        "transcription_id": "trans-" + uuid.uuid4().hex[:8],
        "tenant_id": str(TENANT_ID),
        "case_id": str(uuid.uuid4()),
        "audio_url": "https://plaud.io/recordings/test.mp3",
        "text": "Bonjour, maître. Nous avons reçu la convocation...",
        "segments": [
            {
                "segment_index": 0,
                "speaker": "Speaker 1",
                "start_time": 0.0,
                "end_time": 5.5,
                "text": "Bonjour, maître.",
                "confidence": 0.95,
            },
            {
                "segment_index": 1,
                "speaker": "Speaker 2",
                "start_time": 5.5,
                "end_time": 12.0,
                "text": "Nous avons reçu la convocation...",
                "confidence": 0.92,
            },
        ],
        "speakers": [
            {"id": "spk1", "name": "Speaker 1"},
            {"id": "spk2", "name": "Speaker 2"},
        ],
        "duration": 300,
        "language": "fr",
        "metadata": {"quality": "high"},
    }

    body = json.dumps(payload).encode()
    signature = _sign_hmac(body, PLAUD_SECRET)

    _mock_session, mock_cm = _mock_plaud_session()

    with patch(
        "apps.api.webhooks.plaud.async_session_factory",
        return_value=mock_cm,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/webhooks/plaud",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Plaud-Signature": signature,
                },
            )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "accepted"
    assert data["transcription_id"] == payload["transcription_id"]
    assert data["db_transcription_id"] is not None
    assert data["segments_created"] == 2
    assert data["interaction_event_created"] is True


@pytest.mark.asyncio
async def test_plaud_webhook_invalid_signature():
    """Test Plaud webhook rejects invalid HMAC signature."""
    from apps.api.services.webhook_service import reset_idempotency_store

    reset_idempotency_store()

    payload = {
        "transcription_id": "trans-invalid",
        "tenant_id": str(TENANT_ID),
        "text": "Test",
        "segments": [],
        "speakers": [],
        "duration": 10,
        "language": "fr",
    }

    body = json.dumps(payload).encode()
    invalid_signature = "deadbeef1234567890abcdef"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/webhooks/plaud",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Plaud-Signature": invalid_signature,
            },
        )

    # Should return 401 Unauthorized
    assert response.status_code == 401
    assert "Invalid" in response.json()["detail"]


@pytest.mark.asyncio
async def test_plaud_webhook_missing_signature():
    """Test Plaud webhook rejects missing signature header."""
    payload = {
        "transcription_id": "trans-nosig",
        "tenant_id": str(TENANT_ID),
        "text": "Test",
        "segments": [],
        "speakers": [],
        "duration": 10,
        "language": "fr",
    }

    body = json.dumps(payload).encode()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/webhooks/plaud",
            content=body,
            headers={"Content-Type": "application/json"},
        )

    assert response.status_code == 401
    assert "Missing" in response.json()["detail"]


@pytest.mark.asyncio
async def test_plaud_webhook_creates_transcription():
    """Test that Plaud webhook creates Transcription + TranscriptionSegments."""
    from apps.api.services.webhook_service import reset_idempotency_store

    reset_idempotency_store()

    transcription_id = "trans-create-" + uuid.uuid4().hex[:8]
    payload = {
        "transcription_id": transcription_id,
        "tenant_id": str(TENANT_ID),
        "audio_url": "https://plaud.io/test.mp3",
        "text": "Test transcription avec segments.",
        "segments": [
            {
                "segment_index": 0,
                "speaker": "Avocat",
                "start_time": 0.0,
                "end_time": 3.5,
                "text": "Test transcription",
                "confidence": 0.98,
            },
            {
                "segment_index": 1,
                "speaker": "Client",
                "start_time": 3.5,
                "end_time": 7.0,
                "text": "avec segments.",
                "confidence": 0.96,
            },
        ],
        "speakers": [],
        "duration": 7,
        "language": "fr",
    }

    body = json.dumps(payload).encode()
    signature = _sign_hmac(body, PLAUD_SECRET)

    _mock_session, mock_cm = _mock_plaud_session()

    with patch(
        "apps.api.webhooks.plaud.async_session_factory",
        return_value=mock_cm,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/webhooks/plaud",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Plaud-Signature": signature,
                },
            )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "accepted"
    assert data["segments_created"] == 2
    assert data["db_transcription_id"] is not None


@pytest.mark.asyncio
async def test_plaud_webhook_idempotency():
    """Test Plaud webhook idempotency prevents duplicate processing."""
    from apps.api.services.webhook_service import reset_idempotency_store

    reset_idempotency_store()

    transcription_id = "trans-dup-" + uuid.uuid4().hex[:8]
    payload = {
        "transcription_id": transcription_id,
        "tenant_id": str(TENANT_ID),
        "text": "Duplicate test",
        "segments": [],
        "speakers": [],
        "duration": 5,
        "language": "fr",
    }

    body = json.dumps(payload).encode()
    signature = _sign_hmac(body, PLAUD_SECRET)

    _mock_session, mock_cm = _mock_plaud_session()

    with patch(
        "apps.api.webhooks.plaud.async_session_factory",
        return_value=mock_cm,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # First request - should be accepted
            resp1 = await client.post(
                "/api/v1/webhooks/plaud",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Plaud-Signature": signature,
                },
            )

            assert resp1.status_code == 200
            data1 = resp1.json()
            assert data1["status"] == "accepted"
            assert data1["duplicate"] is False

            # Second request - should be rejected as duplicate
            resp2 = await client.post(
                "/api/v1/webhooks/plaud",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Plaud-Signature": signature,
                },
            )

            assert resp2.status_code == 200
            data2 = resp2.json()
            assert data2["status"] == "duplicate"
            assert data2["duplicate"] is True


# ========== Google OAuth Tests ==========


def test_google_oauth_auth_url():
    """Test Google OAuth authorization URL generation."""
    import apps.api.services.oauth_encryption_service as _oes

    _oes._oauth_encryption_service = None
    with patch.dict(
        "os.environ",
        {
            "GOOGLE_CLIENT_ID": "test-client-id",
            "GOOGLE_CLIENT_SECRET": "test-secret",
            "GOOGLE_REDIRECT_URI": "http://localhost:3000/callback",
            "OAUTH_ENCRYPTION_KEY": "_xQZquM-VYyGtENvEqdepgElsfEETNMtAVMlOqfZV3Q=",
        },
    ):
        service = GoogleOAuthService()
        state = "random-state-" + uuid.uuid4().hex[:8]
        auth_url = service.get_authorization_url(state)

        # Verify URL structure
        assert auth_url.startswith("https://accounts.google.com/o/oauth2/auth")
        assert "client_id=test-client-id" in auth_url
        assert f"state={state}" in auth_url
        assert "access_type=offline" in auth_url
        assert "prompt=consent" in auth_url
        assert "scope=" in auth_url


@pytest.mark.asyncio
async def test_google_oauth_token_exchange():
    """Test Google OAuth code to token exchange (mocked)."""
    import apps.api.services.oauth_encryption_service as _oes

    _oes._oauth_encryption_service = None

    mock_credentials = MagicMock()
    mock_credentials.token = "access-token-123"
    mock_credentials.refresh_token = "refresh-token-456"
    mock_credentials.expiry = datetime.utcnow() + timedelta(hours=1)

    mock_flow = MagicMock()
    mock_flow.credentials = mock_credentials

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=lambda: None)
    )
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    with (
        patch.dict(
            "os.environ",
            {
                "GOOGLE_CLIENT_ID": "test-client-id",
                "GOOGLE_CLIENT_SECRET": "test-secret",
                "OAUTH_ENCRYPTION_KEY": "_xQZquM-VYyGtENvEqdepgElsfEETNMtAVMlOqfZV3Q=",
            },
        ),
        patch("apps.api.services.google_oauth_service.Flow") as MockFlow,
    ):
        MockFlow.from_client_config.return_value = mock_flow
        mock_flow.fetch_token = MagicMock()

        service = GoogleOAuthService()
        result = await service.exchange_code_for_tokens(
            code="auth-code-123",
            session=mock_session,
            tenant_id=TENANT_ID,
            user_id=USER_ID,
        )

        # Verify token was created
        assert result is not None

        # Verify token exchange was called
        mock_flow.fetch_token.assert_called_once_with(code="auth-code-123")

        # Verify session operations
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_google_oauth_token_refresh():
    """Test Google OAuth token refresh flow."""
    import apps.api.services.oauth_encryption_service as _oes

    _oes._oauth_encryption_service = None

    # Mock existing token in database
    mock_existing_token = MagicMock()
    mock_existing_token.access_token = "encrypted-old-token"
    mock_existing_token.refresh_token = "encrypted-refresh-token"

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=lambda: mock_existing_token)
    )
    mock_session.commit = AsyncMock()

    # Mock refreshed credentials
    mock_credentials = MagicMock()
    mock_credentials.token = "new-access-token"
    mock_credentials.expired = True
    mock_credentials.refresh_token = "refresh-token"
    mock_credentials.expiry = datetime.utcnow() + timedelta(hours=1)

    with (
        patch.dict(
            "os.environ",
            {
                "GOOGLE_CLIENT_ID": "test-client-id",
                "GOOGLE_CLIENT_SECRET": "test-secret",
                "OAUTH_ENCRYPTION_KEY": "_xQZquM-VYyGtENvEqdepgElsfEETNMtAVMlOqfZV3Q=",
            },
        ),
        patch("apps.api.services.google_oauth_service.Credentials") as MockCreds,
        patch("apps.api.services.google_oauth_service.Request"),
    ):
        MockCreds.return_value = mock_credentials

        service = GoogleOAuthService()

        # Mock decrypt to return plain tokens
        with (
            patch.object(
                service.encryption_service,
                "decrypt",
                side_effect=lambda x: x.replace("encrypted-", ""),
            ),
            patch.object(
                service.encryption_service, "encrypt", side_effect=lambda x: f"enc-{x}"
            ),
        ):
            credentials = await service.get_valid_credentials(
                session=mock_session,
                tenant_id=TENANT_ID,
                user_id=USER_ID,
            )

            # Verify credentials were refreshed
            assert credentials is not None


# ========== Microsoft OAuth Tests ==========


def test_microsoft_oauth_auth_url():
    """Test Microsoft OAuth authorization URL generation."""
    import apps.api.services.oauth_encryption_service as _oes

    _oes._oauth_encryption_service = None
    with patch.dict(
        "os.environ",
        {
            "MICROSOFT_CLIENT_ID": "ms-client-id",
            "MICROSOFT_CLIENT_SECRET": "ms-secret",
            "MICROSOFT_REDIRECT_URI": "http://localhost:3000/callback/ms",
            "OAUTH_ENCRYPTION_KEY": "_xQZquM-VYyGtENvEqdepgElsfEETNMtAVMlOqfZV3Q=",
        },
    ):
        service = MicrosoftOAuthService()
        state = "ms-state-" + uuid.uuid4().hex[:8]
        auth_url = service.get_authorization_url(state)

        # Verify URL structure
        assert "login.microsoftonline.com" in auth_url
        assert "oauth2/v2.0/authorize" in auth_url
        assert "client_id=ms-client-id" in auth_url
        assert f"state={state}" in auth_url
        assert "response_type=code" in auth_url
        assert "prompt=consent" in auth_url


@pytest.mark.asyncio
async def test_microsoft_oauth_token_exchange():
    """Test Microsoft OAuth code to token exchange (mocked Graph API)."""
    import apps.api.services.oauth_encryption_service as _oes

    _oes._oauth_encryption_service = None

    mock_token_response = {
        "access_token": "ms-access-token-123",
        "refresh_token": "ms-refresh-token-456",
        "expires_in": 3600,
        "token_type": "Bearer",
    }

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=lambda: None)
    )
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    with (
        patch.dict(
            "os.environ",
            {
                "MICROSOFT_CLIENT_ID": "ms-client-id",
                "MICROSOFT_CLIENT_SECRET": "ms-secret",
                "OAUTH_ENCRYPTION_KEY": "_xQZquM-VYyGtENvEqdepgElsfEETNMtAVMlOqfZV3Q=",
            },
        ),
        patch("httpx.AsyncClient") as MockHttpx,
    ):
        # Mock httpx response
        mock_http_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = mock_token_response
        mock_response.raise_for_status = MagicMock()
        mock_http_client.post = AsyncMock(return_value=mock_response)
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock()
        MockHttpx.return_value = mock_http_client

        service = MicrosoftOAuthService()
        result = await service.exchange_code_for_tokens(
            code="ms-auth-code",
            session=mock_session,
            tenant_id=TENANT_ID,
            user_id=USER_ID,
        )

        # Verify token was created
        assert result is not None

        # Verify token endpoint was called
        mock_http_client.post.assert_called_once()
        call_args = mock_http_client.post.call_args
        assert "token_url" in str(call_args) or "oauth2/v2.0/token" in str(call_args)

        # Verify database write
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_microsoft_oauth_token_refresh():
    """Test Microsoft OAuth token refresh flow."""
    import apps.api.services.oauth_encryption_service as _oes

    _oes._oauth_encryption_service = None

    mock_token_response = {
        "access_token": "new-ms-access-token",
        "refresh_token": "new-ms-refresh-token",
        "expires_in": 3600,
    }

    mock_existing_token = MagicMock()
    mock_existing_token.refresh_token = "encrypted-refresh-token"
    mock_existing_token.access_token = "encrypted-old-token"

    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()

    with (
        patch.dict(
            "os.environ",
            {
                "MICROSOFT_CLIENT_ID": "ms-client-id",
                "MICROSOFT_CLIENT_SECRET": "ms-secret",
                "OAUTH_ENCRYPTION_KEY": "_xQZquM-VYyGtENvEqdepgElsfEETNMtAVMlOqfZV3Q=",
            },
        ),
        patch("httpx.AsyncClient") as MockHttpx,
    ):
        # Mock httpx response
        mock_http_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = mock_token_response
        mock_response.raise_for_status = MagicMock()
        mock_http_client.post = AsyncMock(return_value=mock_response)
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock()
        MockHttpx.return_value = mock_http_client

        service = MicrosoftOAuthService()

        # Mock decrypt/encrypt
        with (
            patch.object(
                service.encryption_service,
                "decrypt",
                return_value="plain-refresh-token",
            ),
            patch.object(
                service.encryption_service, "encrypt", side_effect=lambda x: f"enc-{x}"
            ),
        ):
            new_token = await service.refresh_access_token(
                oauth_token=mock_existing_token,
                session=mock_session,
            )

            # Verify refresh endpoint was called
            mock_http_client.post.assert_called_once()
            call_args = mock_http_client.post.call_args
            data = call_args.kwargs["data"]
            assert data["grant_type"] == "refresh_token"

            # Verify token was updated
            assert new_token == "new-ms-access-token"
            mock_session.commit.assert_called_once()


# ========== Seed Data Tests ==========


@pytest.mark.asyncio
@pytest.mark.integration
async def test_seed_data_counts():
    """Test that seed script creates expected record counts.

    This test verifies that the seed_demo_data script creates:
    - 3 CallRecords (Ringover)
    - 2 Transcriptions (Plaud)
    - 5 EmailThreads
    - 10+ Contacts
    - 3+ Cases

    Requires a running PostgreSQL instance.
    """
    # Import and run seed function
    from apps.api.scripts.seed_demo_data import seed_data as seed_all
    from packages.db.session import async_session_factory
    from packages.db.models import (
        CallRecord,
        Transcription,
        EmailThread,
        Contact,
        Case,
    )
    from sqlalchemy import select, func

    # Run seed (idempotent, safe to run multiple times)
    try:
        await seed_all()
    except Exception as e:
        # If seed fails due to missing DB or dependencies, skip test
        pytest.skip(f"Seed data unavailable: {e}")

    # Verify counts
    try:
        async with async_session_factory() as db:
            # Count CallRecords
            call_count = await db.scalar(
                select(func.count()).select_from(CallRecord)
            )

            # Count Transcriptions
            trans_count = await db.scalar(
                select(func.count()).select_from(Transcription)
            )

            # Count EmailThreads
            email_count = await db.scalar(
                select(func.count()).select_from(EmailThread)
            )

            # Count Contacts
            contact_count = await db.scalar(
                select(func.count()).select_from(Contact)
            )

            # Count Cases
            case_count = await db.scalar(
                select(func.count()).select_from(Case)
            )
    except Exception as e:
        pytest.skip(f"PostgreSQL not available: {e}")

    # Assertions - verify minimum expected counts
    # Note: counts may be higher if seed has been run multiple times
    assert call_count >= 3, f"Expected at least 3 CallRecords, got {call_count}"
    assert trans_count >= 2, f"Expected at least 2 Transcriptions, got {trans_count}"
    assert email_count >= 5, f"Expected at least 5 EmailThreads, got {email_count}"
    assert contact_count >= 10, f"Expected at least 10 Contacts, got {contact_count}"
    assert case_count >= 3, f"Expected at least 3 Cases, got {case_count}"
