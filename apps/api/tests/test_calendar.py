"""Tests for Calendar router — GET/POST/PATCH/DELETE events, stats, sync."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.auth.jwt import create_access_token
from apps.api.main import app

# -- Test data --

TENANT_A = uuid.uuid4()
TENANT_B = uuid.uuid4()
USER_A = uuid.uuid4()
USER_B = uuid.uuid4()
EVENT_ID = uuid.uuid4()

TOKEN_A = create_access_token(USER_A, TENANT_A, "partner", "alice@alpha.be")
TOKEN_B = create_access_token(USER_B, TENANT_B, "partner", "bob@beta.be")

NOW = datetime(2026, 2, 15, 12, 0, 0, tzinfo=timezone.utc)


def _make_event_obj(**overrides):
    """Create a mock CalendarEvent object."""
    defaults = {
        "id": EVENT_ID,
        "tenant_id": TENANT_A,
        "user_id": USER_A,
        "title": "Audience Tribunal",
        "description": "Dossier Dupont",
        "start_time": NOW,
        "end_time": datetime(2026, 2, 15, 13, 0, 0, tzinfo=timezone.utc),
        "location": "Palais de Justice",
        "provider": "manual",
        "is_all_day": False,
        "case_id": None,
        "external_id": "manual-1",
        "attendees": [],
        "metadata_": {},
        "synced_at": None,
        "created_at": NOW,
        "updated_at": NOW,
    }
    defaults.update(overrides)

    class MockEvent:
        pass

    obj = MockEvent()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _patch_db():
    mock_session = AsyncMock()

    async def override_db(tenant_id=None):
        yield mock_session

    return mock_session, override_db


# -- Tests: GET /events --


@pytest.mark.asyncio
async def test_get_calendar_events():
    """GET /api/v1/calendar/events returns paginated events."""
    mock_session, override_db = _patch_db()
    event = _make_event_obj()

    # Mock scalars().all() for events query
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [event]

    # Mock scalar() for count query
    count_result = MagicMock()
    count_result.scalar.return_value = 1

    # First execute returns events, second returns count
    events_result = MagicMock()
    events_result.scalars.return_value = scalars_mock

    mock_session.execute = AsyncMock(side_effect=[events_result, count_result])

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/calendar/events?page=1&per_page=50",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["events"]) == 1
    assert data["events"][0]["title"] == "Audience Tribunal"
    assert data["page"] == 1
    assert data["per_page"] == 50


@pytest.mark.asyncio
async def test_get_calendar_events_empty():
    """GET /api/v1/calendar/events returns empty list when no events."""
    mock_session, override_db = _patch_db()

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = []

    events_result = MagicMock()
    events_result.scalars.return_value = scalars_mock

    count_result = MagicMock()
    count_result.scalar.return_value = 0

    mock_session.execute = AsyncMock(side_effect=[events_result, count_result])

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/calendar/events",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["events"] == []


# -- Tests: POST /events --


@pytest.mark.asyncio
async def test_create_calendar_event():
    """POST /api/v1/calendar/events creates a new event."""
    mock_session, override_db = _patch_db()
    event = _make_event_obj()

    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()
    mock_session.refresh = AsyncMock(return_value=None)

    # After refresh, the event object is returned with its attributes
    # We need to patch CalendarEvent constructor
    with patch("apps.api.routers.calendar.CalendarEvent", return_value=event):
        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/calendar/events",
                params={
                    "title": "Audience Tribunal",
                    "start_time": "2026-02-15T12:00:00Z",
                    "end_time": "2026-02-15T13:00:00Z",
                },
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Audience Tribunal"
    assert data["provider"] == "manual"


@pytest.mark.asyncio
async def test_create_calendar_event_unauthenticated():
    """POST /api/v1/calendar/events without token returns 401."""
    mock_session, override_db = _patch_db()

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/v1/calendar/events",
            params={
                "title": "Test",
                "start_time": "2026-02-15T12:00:00Z",
            },
        )

    app.dependency_overrides = {}

    assert resp.status_code == 401


# -- Tests: PATCH /events/{id} --


@pytest.mark.asyncio
async def test_update_calendar_event():
    """PATCH /api/v1/calendar/events/{id} updates an event."""
    mock_session, override_db = _patch_db()
    event = _make_event_obj()

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = event

    mock_session.execute = AsyncMock(return_value=result_mock)
    mock_session.flush = AsyncMock()
    mock_session.refresh = AsyncMock()

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.patch(
            f"/api/v1/calendar/events/{EVENT_ID}",
            params={"title": "Updated Title"},
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(EVENT_ID)


@pytest.mark.asyncio
async def test_update_calendar_event_not_found():
    """PATCH /api/v1/calendar/events/{id} returns 404 for unknown event."""
    mock_session, override_db = _patch_db()

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None

    mock_session.execute = AsyncMock(return_value=result_mock)

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.patch(
            f"/api/v1/calendar/events/{uuid.uuid4()}",
            params={"title": "Updated"},
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 404


# -- Tests: DELETE /events/{id} --


@pytest.mark.asyncio
async def test_delete_calendar_event():
    """DELETE /api/v1/calendar/events/{id} deletes an event."""
    mock_session, override_db = _patch_db()

    result_mock = MagicMock()
    result_mock.rowcount = 1

    mock_session.execute = AsyncMock(return_value=result_mock)
    mock_session.commit = AsyncMock()

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.delete(
            f"/api/v1/calendar/events/{EVENT_ID}",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_calendar_event_not_found():
    """DELETE /api/v1/calendar/events/{id} returns 404 for unknown event."""
    mock_session, override_db = _patch_db()

    result_mock = MagicMock()
    result_mock.rowcount = 0

    mock_session.execute = AsyncMock(return_value=result_mock)

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.delete(
            f"/api/v1/calendar/events/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 404


# -- Tests: GET /stats --


@pytest.mark.asyncio
async def test_get_calendar_stats():
    """GET /api/v1/calendar/stats returns stats."""
    mock_session, override_db = _patch_db()

    # 3 sequential session.execute calls: total, upcoming, today
    total_result = MagicMock()
    total_result.scalar.return_value = 10

    upcoming_result = MagicMock()
    upcoming_result.scalar.return_value = 5

    today_result = MagicMock()
    today_result.scalar.return_value = 2

    mock_session.execute = AsyncMock(
        side_effect=[total_result, upcoming_result, today_result]
    )

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/calendar/stats",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 10
    assert data["upcoming"] == 5
    assert data["today"] == 2


# -- Tests: POST /sync --


@pytest.mark.asyncio
async def test_trigger_calendar_sync():
    """POST /api/v1/calendar/sync triggers sync and returns results."""
    mock_session, override_db = _patch_db()

    sync_results = {
        "google": {"events_created": 3, "total_processed": 10},
        "outlook": {"events_created": 2, "total_processed": 5},
    }

    with patch("apps.api.routers.calendar.get_calendar_sync_service") as mock_get_svc:
        mock_svc = MagicMock()
        mock_svc.sync_all = AsyncMock(return_value=sync_results)
        mock_get_svc.return_value = mock_svc

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/calendar/sync",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["results"]["google"]["events_created"] == 3


@pytest.mark.asyncio
async def test_trigger_calendar_sync_failure():
    """POST /api/v1/calendar/sync returns 500 on failure."""
    mock_session, override_db = _patch_db()

    with patch("apps.api.routers.calendar.get_calendar_sync_service") as mock_get_svc:
        mock_svc = MagicMock()
        mock_svc.sync_all = AsyncMock(side_effect=Exception("Connection failed"))
        mock_get_svc.return_value = mock_svc

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/calendar/sync",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 500


# -- Tests: cross-tenant isolation --


@pytest.mark.asyncio
async def test_cross_tenant_events_isolated():
    """Tenant B token should only query with their own tenant_id."""
    mock_session, override_db = _patch_db()

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = []

    events_result = MagicMock()
    events_result.scalars.return_value = scalars_mock

    count_result = MagicMock()
    count_result.scalar.return_value = 0

    mock_session.execute = AsyncMock(side_effect=[events_result, count_result])

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/calendar/events",
            headers={"Authorization": f"Bearer {TOKEN_B}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 200
    assert resp.json()["events"] == []
