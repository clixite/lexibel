"""LXB-025-027: Tests for Webhooks — HMAC, Ringover, Plaud, idempotency, contact matching."""
import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.main import app
from apps.api.services.webhook_service import (
    parse_e164,
    reset_idempotency_store,
    verify_hmac_signature,
)

# ── Test data ──

TENANT_A = uuid.uuid4()
RINGOVER_SECRET = "ringover-dev-secret"
PLAUD_SECRET = "plaud-dev-secret"


def _sign_payload(payload: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 signature for testing."""
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def _ringover_call_event(**overrides) -> dict:
    defaults = {
        "call_id": f"call-{uuid.uuid4().hex[:8]}",
        "tenant_id": str(TENANT_A),
        "call_type": "answered",
        "caller_number": "+32470123456",
        "callee_number": "+3225551234",
        "direction": "inbound",
        "duration_seconds": 300,
        "started_at": "2026-02-15T10:00:00Z",
        "ended_at": "2026-02-15T10:05:00Z",
    }
    defaults.update(overrides)
    return defaults


def _plaud_event(**overrides) -> dict:
    defaults = {
        "recording_id": f"rec-{uuid.uuid4().hex[:8]}",
        "tenant_id": str(TENANT_A),
        "status": "completed",
        "transcript": "Bonjour, maître. Nous avons reçu la convocation...",
        "speakers": [
            {"id": "spk1", "name": "Maître Dupont", "segments": []},
            {"id": "spk2", "name": "Client", "segments": []},
        ],
        "duration_seconds": 1800,
        "language": "fr",
        "audio_url": "https://plaud.io/recordings/abc123.mp3",
        "audio_mime_type": "audio/mp3",
        "audio_size_bytes": 5242880,
    }
    defaults.update(overrides)
    return defaults


# ── HMAC verification tests ──


def test_hmac_valid_signature():
    payload = b'{"test": "data"}'
    secret = "my-secret"
    sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    assert verify_hmac_signature(payload, sig, secret) is True


def test_hmac_invalid_signature():
    payload = b'{"test": "data"}'
    assert verify_hmac_signature(payload, "invalid-sig", "my-secret") is False


def test_hmac_wrong_secret():
    payload = b'{"test": "data"}'
    sig = hmac.new(b"correct-secret", payload, hashlib.sha256).hexdigest()
    assert verify_hmac_signature(payload, sig, "wrong-secret") is False


# ── E.164 parsing tests ──


def test_parse_e164_already_valid():
    assert parse_e164("+32470123456") == "+32470123456"


def test_parse_e164_international_prefix():
    assert parse_e164("0032470123456") == "+32470123456"


def test_parse_e164_belgian_local():
    assert parse_e164("0470123456") == "+32470123456"


def test_parse_e164_with_formatting():
    assert parse_e164("+32 470 12 34 56") == "+32470123456"
    assert parse_e164("+32-470-123-456") == "+32470123456"


def test_parse_e164_invalid():
    assert parse_e164("123") is None
    assert parse_e164("abc") is None


# ── Ringover webhook tests ──


@pytest.mark.asyncio
async def test_ringover_webhook_valid():
    reset_idempotency_store()
    event = _ringover_call_event()
    payload = json.dumps(event).encode()
    sig = _sign_payload(payload, RINGOVER_SECRET)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/webhooks/ringover",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "X-Ringover-Signature": sig,
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "accepted"
    assert data["inbox_item_created"] is True
    assert data["time_entry_created"] is True  # answered call with duration


@pytest.mark.asyncio
async def test_ringover_webhook_missed_call():
    reset_idempotency_store()
    event = _ringover_call_event(call_type="missed", duration_seconds=0)
    payload = json.dumps(event).encode()
    sig = _sign_payload(payload, RINGOVER_SECRET)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/webhooks/ringover",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "X-Ringover-Signature": sig,
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["time_entry_created"] is False  # missed call, no time entry


@pytest.mark.asyncio
async def test_ringover_missing_signature():
    event = _ringover_call_event()
    payload = json.dumps(event).encode()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/webhooks/ringover",
            content=payload,
            headers={"Content-Type": "application/json"},
        )

    assert resp.status_code == 401
    assert "Missing" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_ringover_invalid_signature():
    event = _ringover_call_event()
    payload = json.dumps(event).encode()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/webhooks/ringover",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "X-Ringover-Signature": "deadbeef",
            },
        )

    assert resp.status_code == 401
    assert "Invalid" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_ringover_idempotency():
    """Duplicate webhook should be rejected."""
    reset_idempotency_store()
    event = _ringover_call_event(call_id="duplicate-call-1")
    payload = json.dumps(event).encode()
    sig = _sign_payload(payload, RINGOVER_SECRET)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # First call — accepted
        resp1 = await client.post(
            "/api/v1/webhooks/ringover",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "X-Ringover-Signature": sig,
            },
        )
        assert resp1.json()["status"] == "accepted"

        # Second call — duplicate
        resp2 = await client.post(
            "/api/v1/webhooks/ringover",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "X-Ringover-Signature": sig,
            },
        )
        assert resp2.json()["status"] == "duplicate"
        assert resp2.json()["duplicate"] is True


# ── Plaud webhook tests ──


@pytest.mark.asyncio
async def test_plaud_webhook_valid():
    reset_idempotency_store()
    event = _plaud_event()
    payload = json.dumps(event).encode()
    sig = _sign_payload(payload, PLAUD_SECRET)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/webhooks/plaud",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "X-Plaud-Signature": sig,
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "accepted"
    assert data["inbox_item_created"] is True
    assert data["evidence_link_created"] is True


@pytest.mark.asyncio
async def test_plaud_webhook_failed_transcription():
    reset_idempotency_store()
    event = _plaud_event(status="failed", transcript=None)
    payload = json.dumps(event).encode()
    sig = _sign_payload(payload, PLAUD_SECRET)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/webhooks/plaud",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "X-Plaud-Signature": sig,
            },
        )

    assert resp.status_code == 200
    assert resp.json()["status"] == "skipped"


@pytest.mark.asyncio
async def test_plaud_missing_signature():
    event = _plaud_event()
    payload = json.dumps(event).encode()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/webhooks/plaud",
            content=payload,
            headers={"Content-Type": "application/json"},
        )

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_plaud_idempotency():
    """Duplicate Plaud webhook should be rejected."""
    reset_idempotency_store()
    event = _plaud_event(recording_id="dup-recording-1")
    payload = json.dumps(event).encode()
    sig = _sign_payload(payload, PLAUD_SECRET)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp1 = await client.post(
            "/api/v1/webhooks/plaud",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "X-Plaud-Signature": sig,
            },
        )
        assert resp1.json()["status"] == "accepted"

        resp2 = await client.post(
            "/api/v1/webhooks/plaud",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "X-Plaud-Signature": sig,
            },
        )
        assert resp2.json()["duplicate"] is True


# ── Integration status test ──


@pytest.mark.asyncio
async def test_integration_status():
    from apps.api.auth.jwt import create_access_token
    token = create_access_token(uuid.uuid4(), TENANT_A, "partner", "test@test.be")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/integrations/status",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["integrations"]) >= 3
    names = [i["name"] for i in data["integrations"]]
    assert "ringover" in names
    assert "plaud" in names
    assert "outlook" in names


# ── Outlook sync stub test ──


@pytest.mark.asyncio
async def test_outlook_sync_stub():
    from apps.api.auth.jwt import create_access_token

    mock_session = AsyncMock()

    async def override_db(tenant_id=None):
        yield mock_session

    token = create_access_token(uuid.uuid4(), TENANT_A, "partner", "test@test.be")

    from apps.api.dependencies import get_db_session
    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/integrations/outlook/sync",
            json={"mailbox": "cabinet@lexibel.be"},
            headers={"Authorization": f"Bearer {token}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 200
    assert resp.json()["items_synced"] == 0  # stub returns empty
