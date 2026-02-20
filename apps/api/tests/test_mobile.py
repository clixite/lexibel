"""Tests for mobile-optimized endpoints."""

import io
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.auth.jwt import create_access_token
from apps.api.main import app

TENANT_ID = uuid.uuid4()
USER_ID = uuid.uuid4()
TOKEN = create_access_token(USER_ID, TENANT_ID, "lawyer", "lawyer@lexibel.be")


def _auth_headers() -> dict:
    return {"Authorization": f"Bearer {TOKEN}"}


def _patch_db():
    mock_session = AsyncMock()

    async def override_db(tenant_id=None):
        yield mock_session

    return mock_session, override_db


# ── Mobile Dashboard ──


class TestMobileDashboard:
    @pytest.mark.asyncio
    async def test_aggregated_dashboard(self):
        mock_session, override_db = _patch_db()

        # Mock 3 DB calls: cases (scalars), inbox count (scalar), time entries (scalars)
        cases_scalars = MagicMock()
        cases_scalars.all.return_value = []
        cases_result = MagicMock()
        cases_result.scalars.return_value = cases_scalars

        inbox_result = MagicMock()
        inbox_result.scalar.return_value = 0

        entries_scalars = MagicMock()
        entries_scalars.all.return_value = []
        entries_result = MagicMock()
        entries_result.scalars.return_value = entries_scalars

        mock_session.execute = AsyncMock(
            side_effect=[cases_result, inbox_result, entries_result]
        )

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/mobile/dashboard", headers=_auth_headers())

        app.dependency_overrides = {}

        assert resp.status_code == 200
        data = resp.json()
        assert "recent_cases" in data
        assert "pending_inbox" in data
        assert "hours_today" in data
        assert "upcoming_deadlines" in data
        assert "generated_at" in data

    @pytest.mark.asyncio
    async def test_dashboard_requires_auth(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/mobile/dashboard")

        assert resp.status_code == 401


# ── Case Summary ──


class TestMobileCaseSummary:
    @pytest.mark.asyncio
    async def test_case_summary(self):
        mock_session, override_db = _patch_db()

        # Mock case object
        case_id = uuid.uuid4()

        class MockCase:
            id = case_id
            reference = "2026/001"
            title = "Dossier Test"
            status = "open"
            matter_type = "civil"
            tenant_id = TENANT_ID

        case_result = MagicMock()
        case_result.scalar_one_or_none.return_value = MockCase()

        contacts_result = MagicMock()
        contacts_result.all.return_value = []

        events_scalars = MagicMock()
        events_scalars.all.return_value = []
        events_result = MagicMock()
        events_result.scalars.return_value = events_scalars

        mock_session.execute = AsyncMock(
            side_effect=[case_result, contacts_result, events_result]
        )

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                f"/api/v1/mobile/case/{case_id}/summary",
                headers=_auth_headers(),
            )

        app.dependency_overrides = {}

        assert resp.status_code == 200
        data = resp.json()
        assert data["case_id"] == str(case_id)
        assert "case" in data
        assert "contacts" in data
        assert "recent_events" in data

    @pytest.mark.asyncio
    async def test_case_summary_not_found(self):
        mock_session, override_db = _patch_db()

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=result_mock)

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                f"/api/v1/mobile/case/{uuid.uuid4()}/summary",
                headers=_auth_headers(),
            )

        app.dependency_overrides = {}

        assert resp.status_code == 404


# ── Quick Time Entry ──


class TestMobileQuickTime:
    @pytest.mark.asyncio
    async def test_create_quick_time_entry(self):
        mock_session, override_db = _patch_db()

        test_case_id = uuid.uuid4()

        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/mobile/quick-time",
                json={
                    "case_id": str(test_case_id),
                    "minutes": 30,
                    "description": "Appel client",
                },
                headers=_auth_headers(),
            )

        app.dependency_overrides = {}

        assert resp.status_code == 200
        data = resp.json()
        assert data["entry"]["minutes"] == 30
        assert data["entry"]["source"] == "mobile"

    @pytest.mark.asyncio
    async def test_quick_time_missing_case_id(self):
        mock_session, override_db = _patch_db()

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/mobile/quick-time",
                json={"minutes": 30},
                headers=_auth_headers(),
            )

        app.dependency_overrides = {}

        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_quick_time_invalid_minutes(self):
        mock_session, override_db = _patch_db()

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/mobile/quick-time",
                json={"case_id": str(uuid.uuid4()), "minutes": -5},
                headers=_auth_headers(),
            )

        app.dependency_overrides = {}

        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_quick_time_zero_minutes(self):
        mock_session, override_db = _patch_db()

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/mobile/quick-time",
                json={"case_id": str(uuid.uuid4()), "minutes": 0},
                headers=_auth_headers(),
            )

        app.dependency_overrides = {}

        assert resp.status_code == 422


# ── Voice Note Upload ──


class TestMobileVoiceNote:
    @pytest.mark.asyncio
    async def test_upload_voice_note(self):
        audio_content = b"fake audio data for testing purposes"

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
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

    @pytest.mark.asyncio
    async def test_upload_non_audio_rejected(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/mobile/voice-note",
                data={"case_id": "case-001"},
                files={
                    "audio": (
                        "doc.pdf",
                        io.BytesIO(b"pdf data"),
                        "application/pdf",
                    )
                },
                headers=_auth_headers(),
            )

        assert resp.status_code == 400
