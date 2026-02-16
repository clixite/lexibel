"""Tests for mobile-optimized endpoints."""

import io
import uuid

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app


TENANT_ID = str(uuid.uuid4())
USER_ID = str(uuid.uuid4())


def _auth_headers() -> dict:
    return {
        "X-Tenant-ID": TENANT_ID,
        "X-User-ID": USER_ID,
        "X-User-Role": "lawyer",
        "X-User-Email": "lawyer@lexibel.be",
    }


@pytest.fixture
def client():
    return TestClient(app)


# ── Mobile Dashboard ──


class TestMobileDashboard:
    def test_aggregated_dashboard(self, client):
        resp = client.get("/api/v1/mobile/dashboard", headers=_auth_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert "recent_cases" in data
        assert "pending_inbox" in data
        assert "hours_today" in data
        assert "upcoming_deadlines" in data
        assert data["user_id"] == USER_ID
        assert "generated_at" in data

    def test_dashboard_requires_auth(self, client):
        resp = client.get("/api/v1/mobile/dashboard")
        assert resp.status_code == 401


# ── Case Summary ──


class TestMobileCaseSummary:
    def test_case_summary(self, client):
        resp = client.get(
            "/api/v1/mobile/case/case-001/summary", headers=_auth_headers()
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["case_id"] == "case-001"
        assert "case" in data
        assert "contacts" in data
        assert "recent_events" in data


# ── Quick Time Entry ──


class TestMobileQuickTime:
    def test_create_quick_time_entry(self, client):
        resp = client.post(
            "/api/v1/mobile/quick-time",
            json={"case_id": "case-001", "minutes": 30, "description": "Appel client"},
            headers=_auth_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["entry"]["case_id"] == "case-001"
        assert data["entry"]["minutes"] == 30
        assert data["entry"]["source"] == "mobile"

    def test_quick_time_missing_case_id(self, client):
        resp = client.post(
            "/api/v1/mobile/quick-time",
            json={"minutes": 30},
            headers=_auth_headers(),
        )
        assert resp.status_code == 400

    def test_quick_time_invalid_minutes(self, client):
        resp = client.post(
            "/api/v1/mobile/quick-time",
            json={"case_id": "case-001", "minutes": -5},
            headers=_auth_headers(),
        )
        assert resp.status_code == 400

    def test_quick_time_zero_minutes(self, client):
        resp = client.post(
            "/api/v1/mobile/quick-time",
            json={"case_id": "case-001", "minutes": 0},
            headers=_auth_headers(),
        )
        assert resp.status_code == 400


# ── Voice Note Upload ──


class TestMobileVoiceNote:
    def test_upload_voice_note(self, client):
        audio_content = b"fake audio data for testing purposes"
        resp = client.post(
            "/api/v1/mobile/voice-note",
            data={"case_id": "case-001"},
            files={"audio": ("note.wav", io.BytesIO(audio_content), "audio/wav")},
            headers=_auth_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["note"]["case_id"] == "case-001"
        assert data["note"]["status"] == "queued"
        assert data["note"]["filename"] == "note.wav"

    def test_upload_non_audio_rejected(self, client):
        resp = client.post(
            "/api/v1/mobile/voice-note",
            data={"case_id": "case-001"},
            files={"audio": ("doc.pdf", io.BytesIO(b"pdf data"), "application/pdf")},
            headers=_auth_headers(),
        )
        assert resp.status_code == 400

    def test_voice_note_requires_case_id(self, client):
        audio_content = b"fake audio"
        resp = client.post(
            "/api/v1/mobile/voice-note",
            files={"audio": ("note.wav", io.BytesIO(audio_content), "audio/wav")},
            headers=_auth_headers(),
        )
        assert resp.status_code == 422  # missing required form field
