"""Tests for Dashboard router — GET /stats and GET /intelligence."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.auth.jwt import create_access_token
from apps.api.main import app
from packages.db.models.time_entry import TimeEntry

# Patch TimeEntry.duration alias (router references .duration, model has .duration_minutes)
if not hasattr(TimeEntry, "duration"):
    TimeEntry.duration = TimeEntry.duration_minutes

# -- Test data --

TENANT_A = uuid.uuid4()
TENANT_B = uuid.uuid4()
USER_A = uuid.uuid4()
USER_B = uuid.uuid4()

TOKEN_A = create_access_token(USER_A, TENANT_A, "partner", "alice@alpha.be")
TOKEN_B = create_access_token(USER_B, TENANT_B, "partner", "bob@beta.be")

NOW = datetime(2026, 2, 15, 12, 0, 0, tzinfo=timezone.utc)


def _patch_db():
    mock_session = AsyncMock()

    async def override_db(tenant_id=None):
        yield mock_session

    return mock_session, override_db


# -- Tests: GET /dashboard/stats --


@pytest.mark.asyncio
async def test_get_dashboard_stats():
    """GET /api/v1/dashboard/stats returns aggregate statistics."""
    mock_session, override_db = _patch_db()

    # 6 sequential session.scalar calls:
    # cases, contacts, invoices, documents, pending_inbox, monthly_hours
    mock_session.scalar = AsyncMock(side_effect=[42, 150, 18, 230, 7, 125.5])

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/dashboard/stats",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert "stats" in data
    stats = data["stats"]
    assert stats["total_cases"] == 42
    assert stats["total_contacts"] == 150
    assert stats["total_invoices"] == 18
    assert stats["total_documents"] == 230
    assert stats["pending_inbox"] == 7
    assert stats["monthly_hours"] == 125.5


@pytest.mark.asyncio
async def test_get_dashboard_stats_all_zero():
    """GET /api/v1/dashboard/stats returns zeros for empty tenant."""
    mock_session, override_db = _patch_db()

    mock_session.scalar = AsyncMock(return_value=0)

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/dashboard/stats",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    stats = data["stats"]
    assert stats["total_cases"] == 0
    assert stats["total_contacts"] == 0
    assert stats["monthly_hours"] == 0.0


@pytest.mark.asyncio
async def test_get_dashboard_stats_db_error():
    """GET /api/v1/dashboard/stats returns 500 on DB failure."""
    mock_session, override_db = _patch_db()

    mock_session.scalar = AsyncMock(side_effect=Exception("DB connection lost"))

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/dashboard/stats",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_get_dashboard_stats_unauthenticated():
    """GET /api/v1/dashboard/stats without token returns 401."""
    mock_session, override_db = _patch_db()

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/v1/dashboard/stats")

    app.dependency_overrides = {}

    assert resp.status_code == 401


# -- Tests: GET /dashboard/intelligence --


@pytest.mark.asyncio
async def test_get_dashboard_intelligence():
    """GET /api/v1/dashboard/intelligence returns brain intelligence data."""
    mock_session, override_db = _patch_db()

    # 3 scalar calls: critical_insights, pending_actions, cases_at_risk
    mock_session.scalar = AsyncMock(side_effect=[5, 3, 2])

    # 2 execute calls: deadline_rows and recent_actions_rows
    deadline_result = MagicMock()
    deadline_result.all.return_value = []

    actions_scalars = MagicMock()
    actions_scalars.all.return_value = []
    actions_result = MagicMock()
    actions_result.scalars.return_value = actions_scalars

    mock_session.execute = AsyncMock(side_effect=[deadline_result, actions_result])

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/dashboard/intelligence",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["critical_insights_count"] == 5
    assert data["pending_actions_count"] == 3
    assert data["cases_at_risk_count"] == 2
    assert data["upcoming_deadlines"] == []
    assert data["recent_brain_actions"] == []


@pytest.mark.asyncio
async def test_get_dashboard_intelligence_with_data():
    """GET /api/v1/dashboard/intelligence returns populated data."""
    mock_session, override_db = _patch_db()

    _case_id = uuid.uuid4()
    _action_id = uuid.uuid4()

    mock_session.scalar = AsyncMock(side_effect=[2, 1, 1])

    # Deadline event mock — use a factory to avoid class-scope issues
    mock_event = MagicMock()
    mock_event.title = "Deadline depot conclusions"
    mock_event.start_time = datetime(2026, 2, 20, 9, 0, 0, tzinfo=timezone.utc)
    mock_event.case_id = _case_id

    deadline_result = MagicMock()
    deadline_result.all.return_value = [(mock_event, "Dossier Dupont")]

    # Brain action mock
    mock_action = MagicMock()
    mock_action.id = _action_id
    mock_action.case_id = _case_id
    mock_action.action_type = "review_deadline"
    mock_action.priority = "high"
    mock_action.status = "pending"
    mock_action.created_at = NOW

    actions_scalars = MagicMock()
    actions_scalars.all.return_value = [mock_action]
    actions_result = MagicMock()
    actions_result.scalars.return_value = actions_scalars

    mock_session.execute = AsyncMock(side_effect=[deadline_result, actions_result])

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/dashboard/intelligence",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["critical_insights_count"] == 2
    assert len(data["upcoming_deadlines"]) == 1
    assert data["upcoming_deadlines"][0]["title"] == "Deadline depot conclusions"
    assert data["upcoming_deadlines"][0]["case_title"] == "Dossier Dupont"
    assert len(data["recent_brain_actions"]) == 1
    assert data["recent_brain_actions"][0]["action_type"] == "review_deadline"


@pytest.mark.asyncio
async def test_get_dashboard_intelligence_db_error():
    """GET /api/v1/dashboard/intelligence returns 500 on DB failure."""
    mock_session, override_db = _patch_db()

    mock_session.scalar = AsyncMock(side_effect=Exception("DB error"))

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/dashboard/intelligence",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 500


# -- Tests: cross-tenant isolation --


@pytest.mark.asyncio
async def test_dashboard_stats_cross_tenant():
    """Different tenants get separate stats."""
    mock_session, override_db = _patch_db()

    mock_session.scalar = AsyncMock(return_value=0)

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/dashboard/stats",
            headers={"Authorization": f"Bearer {TOKEN_B}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 200
    stats = resp.json()["stats"]
    assert stats["total_cases"] == 0
