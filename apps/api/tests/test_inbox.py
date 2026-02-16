"""LXB-018-019: Tests for Inbox — validate/refuse flow, status transitions, create-case."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.auth.jwt import create_access_token
from apps.api.main import app

# ── Test data ──

TENANT_A = uuid.uuid4()
USER_A = uuid.uuid4()
CASE_ID = uuid.uuid4()
INBOX_ID = uuid.uuid4()
EVENT_ID = uuid.uuid4()

TOKEN_A = create_access_token(USER_A, TENANT_A, "partner", "alice@alpha.be")

NOW = datetime(2026, 2, 15, 12, 0, 0, tzinfo=timezone.utc)


def _make_inbox_obj(**overrides):
    """Create a mock InboxItem object."""
    defaults = {
        "id": INBOX_ID,
        "tenant_id": TENANT_A,
        "source": "OUTLOOK",
        "status": "DRAFT",
        "raw_payload": {"subject": "Re: Dossier Dupont", "from": "jean@dupont.be"},
        "suggested_case_id": CASE_ID,
        "confidence": 0.87,
        "validated_by": None,
        "validated_at": None,
        "created_at": NOW,
    }
    defaults.update(overrides)

    class MockInbox:
        pass

    obj = MockInbox()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _make_event_obj(**overrides):
    """Create a mock InteractionEvent object."""
    defaults = {
        "id": EVENT_ID,
        "tenant_id": TENANT_A,
        "case_id": CASE_ID,
        "source": "OUTLOOK",
        "event_type": "EMAIL",
        "title": "Re: Dossier Dupont",
        "body": None,
        "occurred_at": NOW,
        "metadata": {},
        "created_by": USER_A,
        "created_at": NOW,
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


# ── Tests ──


@pytest.mark.asyncio
async def test_list_inbox():
    """GET /inbox returns paginated inbox items."""
    mock_session, override_db = _patch_db()
    items = [_make_inbox_obj(id=uuid.uuid4()) for _ in range(3)]

    with patch("apps.api.routers.inbox.inbox_service") as mock_svc:
        mock_svc.list_inbox = AsyncMock(return_value=(items, 3))

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/v1/inbox?page=1&per_page=10",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3


@pytest.mark.asyncio
async def test_list_inbox_with_status_filter():
    """GET /inbox?status=DRAFT filters by status."""
    mock_session, override_db = _patch_db()

    with patch("apps.api.routers.inbox.inbox_service") as mock_svc:
        mock_svc.list_inbox = AsyncMock(return_value=([], 0))

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/v1/inbox?status=DRAFT",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    call_kwargs = mock_svc.list_inbox.call_args
    assert call_kwargs.kwargs.get("status") == "DRAFT"


@pytest.mark.asyncio
async def test_validate_inbox_item():
    """POST /inbox/{id}/validate creates event and marks as VALIDATED."""
    mock_session, override_db = _patch_db()
    validated_item = _make_inbox_obj(
        status="VALIDATED", validated_by=USER_A, validated_at=NOW
    )
    event_obj = _make_event_obj()

    with patch("apps.api.routers.inbox.inbox_service") as mock_svc:
        mock_svc.validate_inbox_item = AsyncMock(
            return_value=(validated_item, event_obj)
        )

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/v1/inbox/{INBOX_ID}/validate",
                json={
                    "case_id": str(CASE_ID),
                    "event_type": "EMAIL",
                    "title": "Re: Dossier Dupont",
                },
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "VALIDATED"
    assert data["validated_by"] == str(USER_A)


@pytest.mark.asyncio
async def test_validate_already_validated():
    """POST /inbox/{id}/validate on already-validated item returns 409."""
    mock_session, override_db = _patch_db()
    already_validated = _make_inbox_obj(status="VALIDATED")

    with patch("apps.api.routers.inbox.inbox_service") as mock_svc:
        mock_svc.validate_inbox_item = AsyncMock(return_value=(already_validated, None))

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/v1/inbox/{INBOX_ID}/validate",
                json={
                    "case_id": str(CASE_ID),
                    "event_type": "EMAIL",
                    "title": "Test",
                },
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_validate_not_found():
    """POST /inbox/{id}/validate returns 404 for unknown item."""
    mock_session, override_db = _patch_db()

    with patch("apps.api.routers.inbox.inbox_service") as mock_svc:
        mock_svc.validate_inbox_item = AsyncMock(return_value=(None, None))

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/v1/inbox/{uuid.uuid4()}/validate",
                json={
                    "case_id": str(CASE_ID),
                    "event_type": "EMAIL",
                    "title": "Test",
                },
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_refuse_inbox_item():
    """POST /inbox/{id}/refuse marks item as REFUSED."""
    mock_session, override_db = _patch_db()
    refused_item = _make_inbox_obj(
        status="REFUSED", validated_by=USER_A, validated_at=NOW
    )

    with patch("apps.api.routers.inbox.inbox_service") as mock_svc:
        mock_svc.refuse_inbox_item = AsyncMock(return_value=refused_item)

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/v1/inbox/{INBOX_ID}/refuse",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    assert resp.json()["status"] == "REFUSED"


@pytest.mark.asyncio
async def test_refuse_not_found():
    """POST /inbox/{id}/refuse returns 404 for unknown item."""
    mock_session, override_db = _patch_db()

    with patch("apps.api.routers.inbox.inbox_service") as mock_svc:
        mock_svc.refuse_inbox_item = AsyncMock(return_value=None)

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/v1/inbox/{uuid.uuid4()}/refuse",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_case_from_inbox():
    """POST /inbox/{id}/create-case creates case + event, marks VALIDATED."""
    mock_session, override_db = _patch_db()
    validated_item = _make_inbox_obj(
        status="VALIDATED", validated_by=USER_A, validated_at=NOW
    )

    class MockCase:
        pass

    case_obj = MockCase()
    case_obj.id = CASE_ID
    event_obj = _make_event_obj()

    with patch("apps.api.routers.inbox.inbox_service") as mock_svc:
        mock_svc.create_case_from_inbox = AsyncMock(
            return_value=(validated_item, case_obj, event_obj)
        )

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/v1/inbox/{INBOX_ID}/create-case",
                json={
                    "reference": "2026/042",
                    "title": "Nouveau dossier Dupont",
                    "matter_type": "civil",
                    "responsible_user_id": str(USER_A),
                },
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "VALIDATED"


@pytest.mark.asyncio
async def test_create_case_from_inbox_already_validated():
    """POST /inbox/{id}/create-case on already-validated item returns 409."""
    mock_session, override_db = _patch_db()
    already_validated = _make_inbox_obj(status="VALIDATED")

    with patch("apps.api.routers.inbox.inbox_service") as mock_svc:
        mock_svc.create_case_from_inbox = AsyncMock(
            return_value=(already_validated, None, None)
        )

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/v1/inbox/{INBOX_ID}/create-case",
                json={
                    "reference": "2026/042",
                    "title": "Test",
                    "matter_type": "civil",
                    "responsible_user_id": str(USER_A),
                },
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 409
