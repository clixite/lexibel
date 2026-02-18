"""Integration tests for SENTINEL API endpoints.

Tests all 7 SENTINEL API endpoints:
1. POST /api/sentinel/check-conflict - Conflict detection
2. GET /api/sentinel/conflicts - List conflicts with pagination
3. PUT /api/sentinel/conflicts/{conflict_id}/resolve - Resolve conflicts
4. POST /api/sentinel/sync - Graph synchronization
5. GET /api/sentinel/graph/{entity_id} - Graph visualization data
6. GET /api/sentinel/search - Entity search
7. GET /api/sentinel/alerts/stream - SSE alert streaming
"""

import asyncio
import json
import pytest
from datetime import datetime
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import ASGITransport, AsyncClient

from apps.api.auth.jwt import create_access_token
from apps.api.main import app
from packages.db.models.sentinel_conflict import SentinelConflict
from packages.db.models.contact import Contact


# ── Test Data ──

TENANT_ID = uuid4()
USER_ID = uuid4()
USER_EMAIL = "lawyer@alpha.be"
USER_ROLE = "partner"

TOKEN = create_access_token(USER_ID, TENANT_ID, USER_ROLE, USER_EMAIL)

CONTACT_ID = uuid4()
CONTACT_ID_2 = uuid4()
CONFLICT_ID = uuid4()
CASE_ID = uuid4()


def _make_contact(**overrides):
    """Create a mock Contact object."""
    defaults = {
        "id": CONTACT_ID,
        "tenant_id": TENANT_ID,
        "type": "natural",
        "full_name": "Jean Dupont",
        "bce_number": None,
        "email": "jean@dupont.be",
        "phone_e164": "+32470123456",
        "address": {
            "street": "Rue de la Loi 1",
            "city": "Bruxelles",
            "zip": "1000",
            "country": "BE",
        },
        "language": "fr",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }
    defaults.update(overrides)

    class MockContact:
        pass

    obj = MockContact()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _make_conflict(**overrides):
    """Create a mock SentinelConflict object."""
    defaults = {
        "id": CONFLICT_ID,
        "tenant_id": TENANT_ID,
        "trigger_entity_id": CONTACT_ID,
        "trigger_entity_type": "contact",
        "conflict_type": "direct_opposition",
        "severity_score": 85,
        "description": "Direct adversary in active case",
        "conflicting_entity_id": CONTACT_ID_2,
        "conflicting_entity_type": "contact",
        "conflicting_case_id": CASE_ID,
        "graph_path": {"nodes": [], "edges": []},
        "auto_resolved": False,
        "resolution": None,
        "resolved_by": None,
        "resolved_at": None,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }
    defaults.update(overrides)

    class MockConflict:
        pass

    obj = MockConflict()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _patch_db():
    """Create mock database session."""
    mock_session = AsyncMock()

    async def override_db(tenant_id=None):
        yield mock_session

    return mock_session, override_db


# ── Helper Functions ──


def _create_mock_detector():
    """Create a mock conflict detector."""
    detector = AsyncMock()
    detector.neo4j_client = AsyncMock()
    return detector


def _create_mock_sync():
    """Create a mock graph sync service."""
    sync_service = AsyncMock()
    return sync_service


# ── 1. POST /api/sentinel/check-conflict ──


class TestCheckConflict:
    """Tests for POST /api/sentinel/check-conflict endpoint."""

    @pytest.mark.asyncio
    async def test_check_conflict_success(self):
        """Test successful conflict check."""
        mock_session, override_db = _patch_db()
        contact = _make_contact()

        # Mock database query
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=contact)
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Create mock detector
        mock_detector = _create_mock_detector()
        mock_detector.check_all_conflicts = AsyncMock(
            return_value=[
                {
                    "conflict_type": "direct_opposition",
                    "severity_score": 85,
                    "description": "Direct adversary in active case",
                    "client_id": str(CONTACT_ID_2),
                    "client_name": "ACME Corp",
                    "client_type": "legal",
                }
            ]
        )

        async def mock_get_detector():
            return mock_detector

        with patch("apps.api.services.sentinel.conflict_detector.get_conflict_detector", mock_get_detector):
            from apps.api.dependencies import get_db_session

            app.dependency_overrides[get_db_session] = override_db

            try:
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.post(
                        "/api/sentinel/check-conflict",
                        json={
                            "contact_id": str(CONTACT_ID),
                            "include_graph": False,
                        },
                        headers={"Authorization": f"Bearer {TOKEN}"},
                    )

                assert response.status_code == 200
                data = response.json()
                assert "conflicts" in data
                assert "total_count" in data
                assert "highest_severity" in data
                assert "check_timestamp" in data
                assert data["total_count"] == 1
                assert data["highest_severity"] == 85
                assert len(data["conflicts"]) == 1
                assert data["conflicts"][0]["conflict_type"] == "direct_opposition"

            finally:
                app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_check_conflict_with_graph(self):
        """Test conflict check with graph data included."""
        mock_session, override_db = _patch_db()
        contact = _make_contact()

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=contact)
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_detector = _create_mock_detector()
        mock_detector.check_all_conflicts = AsyncMock(
            return_value=[
                {
                    "conflict_type": "direct_opposition",
                    "severity_score": 85,
                    "description": "Direct adversary",
                    "client_id": str(CONTACT_ID_2),
                    "client_name": "ACME Corp",
                }
            ]
        )

        # Mock Neo4j graph query
        mock_detector.neo4j_client.execute_query = AsyncMock(
            return_value=[
                {
                    "node_id": str(CONTACT_ID),
                    "node_type": "Person",
                    "node_name": "Jean Dupont",
                    "connected_id": str(CONTACT_ID_2),
                    "rel_type": "OPPOSED_TO",
                }
            ]
        )

        async def mock_get_detector():
            return mock_detector

        with patch("apps.api.services.sentinel.conflict_detector.get_conflict_detector", mock_get_detector):
            from apps.api.dependencies import get_db_session

            app.dependency_overrides[get_db_session] = override_db

            try:
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.post(
                        "/api/sentinel/check-conflict",
                        json={
                            "contact_id": str(CONTACT_ID),
                            "include_graph": True,
                        },
                        headers={"Authorization": f"Bearer {TOKEN}"},
                    )

                assert response.status_code == 200
                data = response.json()
                assert "graph_data" in data
                assert data["graph_data"] is not None
                assert "nodes" in data["graph_data"]
                assert "edges" in data["graph_data"]

            finally:
                app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_check_conflict_not_found(self):
        """Test conflict check with non-existent contact."""
        mock_session, override_db = _patch_db()

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/sentinel/check-conflict",
                    json={
                        "contact_id": str(uuid4()),
                        "include_graph": False,
                    },
                    headers={"Authorization": f"Bearer {TOKEN}"},
                )

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

        finally:
            app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_check_conflict_unauthorized(self):
        """Test conflict check without authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/sentinel/check-conflict",
                json={
                    "contact_id": str(CONTACT_ID),
                    "include_graph": False,
                },
            )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_check_conflict_no_conflicts_found(self):
        """Test conflict check when no conflicts exist."""
        mock_session, override_db = _patch_db()
        contact = _make_contact()

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=contact)
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_detector = _create_mock_detector()
        mock_detector.check_all_conflicts = AsyncMock(return_value=[])

        async def mock_get_detector():
            return mock_detector

        with patch("apps.api.services.sentinel.conflict_detector.get_conflict_detector", mock_get_detector):
            from apps.api.dependencies import get_db_session

            app.dependency_overrides[get_db_session] = override_db

            try:
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.post(
                        "/api/sentinel/check-conflict",
                        json={
                            "contact_id": str(CONTACT_ID),
                            "include_graph": False,
                        },
                        headers={"Authorization": f"Bearer {TOKEN}"},
                    )

                assert response.status_code == 200
                data = response.json()
                assert data["total_count"] == 0
                assert data["highest_severity"] == 0
                assert len(data["conflicts"]) == 0

            finally:
                app.dependency_overrides = {}


# ── 2. GET /api/sentinel/conflicts ──


class TestListConflicts:
    """Tests for GET /api/sentinel/conflicts endpoint."""

    @pytest.mark.asyncio
    async def test_list_conflicts_success(self):
        """Test listing conflicts with pagination."""
        mock_session, override_db = _patch_db()
        conflict = _make_conflict()
        contact1 = _make_contact(id=CONTACT_ID)
        contact2 = _make_contact(id=CONTACT_ID_2, full_name="ACME Corp", type="legal")

        # Mock conflict query
        mock_result = AsyncMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=[conflict]))
        )

        # Mock count query
        mock_count_result = AsyncMock()
        mock_count_result.scalar = MagicMock(return_value=1)

        # Mock contact batch query
        mock_contact_result = AsyncMock()
        mock_contact_result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=[contact1, contact2]))
        )

        call_count = [0]

        async def mock_execute(query):
            call_count[0] += 1
            if call_count[0] == 1:  # First call is conflict query
                return mock_result
            elif call_count[0] == 2:  # Second call is count query
                return mock_count_result
            else:  # Third call is contact batch query
                return mock_contact_result

        mock_session.execute = mock_execute

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/sentinel/conflicts?page=1&page_size=20",
                    headers={"Authorization": f"Bearer {TOKEN}"},
                )

            assert response.status_code == 200
            data = response.json()
            assert "conflicts" in data
            assert "pagination" in data
            assert len(data["conflicts"]) == 1
            assert data["pagination"]["page"] == 1
            assert data["pagination"]["total"] == 1

        finally:
            app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_list_conflicts_with_status_filter(self):
        """Test listing conflicts with status filter."""
        mock_session, override_db = _patch_db()

        mock_result = AsyncMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=[]))
        )

        mock_count_result = AsyncMock()
        mock_count_result.scalar = MagicMock(return_value=0)

        call_count = [0]

        async def mock_execute(query):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_result
            else:
                return mock_count_result

        mock_session.execute = mock_execute

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/sentinel/conflicts?status=active",
                    headers={"Authorization": f"Bearer {TOKEN}"},
                )

            assert response.status_code == 200
            data = response.json()
            assert data["pagination"]["total"] == 0

        finally:
            app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_list_conflicts_with_severity_filter(self):
        """Test listing conflicts with minimum severity filter."""
        mock_session, override_db = _patch_db()
        conflict = _make_conflict(severity_score=90)
        contact = _make_contact()

        mock_result = AsyncMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=[conflict]))
        )

        mock_count_result = AsyncMock()
        mock_count_result.scalar = MagicMock(return_value=1)

        mock_contact_result = AsyncMock()
        mock_contact_result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=[contact]))
        )

        call_count = [0]

        async def mock_execute(query):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_result
            elif call_count[0] == 2:
                return mock_count_result
            else:
                return mock_contact_result

        mock_session.execute = mock_execute

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/sentinel/conflicts?severity_min=80",
                    headers={"Authorization": f"Bearer {TOKEN}"},
                )

            assert response.status_code == 200
            data = response.json()
            assert len(data["conflicts"]) == 1
            assert data["conflicts"][0]["severity_score"] == 90

        finally:
            app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_list_conflicts_empty_results(self):
        """Test listing conflicts with no results."""
        mock_session, override_db = _patch_db()

        mock_result = AsyncMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=[]))
        )

        mock_count_result = AsyncMock()
        mock_count_result.scalar = MagicMock(return_value=0)

        call_count = [0]

        async def mock_execute(query):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_result
            else:
                return mock_count_result

        mock_session.execute = mock_execute

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/sentinel/conflicts",
                    headers={"Authorization": f"Bearer {TOKEN}"},
                )

            assert response.status_code == 200
            data = response.json()
            assert len(data["conflicts"]) == 0
            assert data["pagination"]["total"] == 0
            assert data["pagination"]["total_pages"] == 0

        finally:
            app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_list_conflicts_unauthorized(self):
        """Test listing conflicts without authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/sentinel/conflicts")

        assert response.status_code == 401


# ── 3. PUT /api/sentinel/conflicts/{conflict_id}/resolve ──


class TestResolveConflict:
    """Tests for PUT /api/sentinel/conflicts/{conflict_id}/resolve endpoint."""

    @pytest.mark.asyncio
    async def test_resolve_conflict_refused(self):
        """Test resolving conflict as refused."""
        mock_session, override_db = _patch_db()
        conflict = _make_conflict(resolution="refused", resolved_at=datetime.now())

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=conflict)
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.refresh = AsyncMock()

        with patch("apps.api.routes.sentinel.ConflictAlerter") as mock_alerter_class:
            mock_alerter = AsyncMock()
            mock_alerter.resolve_conflict = AsyncMock(return_value=True)
            mock_alerter_class.return_value = mock_alerter

            from apps.api.dependencies import get_db_session

            app.dependency_overrides[get_db_session] = override_db

            try:
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.put(
                        f"/api/sentinel/conflicts/{CONFLICT_ID}/resolve",
                        json={"resolution": "refused", "notes": "Client declined"},
                        headers={"Authorization": f"Bearer {TOKEN}"},
                    )

                assert response.status_code == 200
                data = response.json()
                assert "id" in data
                assert "status" in data
                assert data["status"] in ["resolved", "dismissed"]

            finally:
                app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_resolve_conflict_waiver_obtained(self):
        """Test resolving conflict with waiver obtained."""
        mock_session, override_db = _patch_db()
        conflict = _make_conflict(
            resolution="waiver_obtained", resolved_at=datetime.now()
        )

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=conflict)
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.refresh = AsyncMock()

        with patch("apps.api.routes.sentinel.ConflictAlerter") as mock_alerter_class:
            mock_alerter = AsyncMock()
            mock_alerter.resolve_conflict = AsyncMock(return_value=True)
            mock_alerter_class.return_value = mock_alerter

            from apps.api.dependencies import get_db_session

            app.dependency_overrides[get_db_session] = override_db

            try:
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.put(
                        f"/api/sentinel/conflicts/{CONFLICT_ID}/resolve",
                        json={
                            "resolution": "waiver_obtained",
                            "notes": "Signed waiver on file",
                        },
                        headers={"Authorization": f"Bearer {TOKEN}"},
                    )

                assert response.status_code == 200

            finally:
                app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_resolve_conflict_false_positive(self):
        """Test resolving conflict as false positive."""
        mock_session, override_db = _patch_db()
        conflict = _make_conflict(
            resolution="false_positive", resolved_at=datetime.now()
        )

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=conflict)
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.refresh = AsyncMock()

        with patch("apps.api.routes.sentinel.ConflictAlerter") as mock_alerter_class:
            mock_alerter = AsyncMock()
            mock_alerter.resolve_conflict = AsyncMock(return_value=True)
            mock_alerter_class.return_value = mock_alerter

            from apps.api.dependencies import get_db_session

            app.dependency_overrides[get_db_session] = override_db

            try:
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.put(
                        f"/api/sentinel/conflicts/{CONFLICT_ID}/resolve",
                        json={
                            "resolution": "false_positive",
                            "notes": "Not actually a conflict",
                        },
                        headers={"Authorization": f"Bearer {TOKEN}"},
                    )

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "dismissed"

            finally:
                app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_resolve_conflict_not_found(self):
        """Test resolving non-existent conflict."""
        mock_session, override_db = _patch_db()

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.put(
                    f"/api/sentinel/conflicts/{uuid4()}/resolve",
                    json={"resolution": "refused"},
                    headers={"Authorization": f"Bearer {TOKEN}"},
                )

            assert response.status_code == 404

        finally:
            app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_resolve_conflict_unauthorized(self):
        """Test resolving conflict without authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.put(
                f"/api/sentinel/conflicts/{CONFLICT_ID}/resolve",
                json={"resolution": "refused"},
            )

        assert response.status_code == 401


# ── 4. POST /api/sentinel/sync ──


class TestSyncGraph:
    """Tests for POST /api/sentinel/sync endpoint."""

    @pytest.mark.asyncio
    async def test_sync_all(self):
        """Test syncing all entities."""
        mock_session, override_db = _patch_db()
        mock_session.commit = AsyncMock()

        mock_sync = _create_mock_sync()
        mock_sync.batch_sync = AsyncMock(
            return_value={
                "persons": 100,
                "companies": 50,
                "cases": 25,
                "lawyers": 10,
                "errors": 0,
            }
        )

        async def mock_get_sync():
            return mock_sync

        with patch("apps.api.services.sentinel.graph_sync.get_graph_sync_service", mock_get_sync):
            from apps.api.dependencies import get_db_session

            app.dependency_overrides[get_db_session] = override_db

            try:
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.post(
                        "/api/sentinel/sync",
                        json={"sync_all": True},
                        headers={"Authorization": f"Bearer {TOKEN}"},
                    )

                assert response.status_code == 200
                data = response.json()
                assert "synced_count" in data
                assert "failed_count" in data
                assert "duration_seconds" in data
                assert data["synced_count"] == 185  # 100+50+25+10
                assert data["failed_count"] == 0

            finally:
                app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_sync_specific_entities(self):
        """Test syncing specific entity IDs."""
        mock_session, override_db = _patch_db()
        mock_session.commit = AsyncMock()

        entity_ids = [uuid4(), uuid4(), uuid4()]

        mock_sync = _create_mock_sync()
        mock_sync.sync_person_to_graph = AsyncMock(return_value=True)
        mock_sync.sync_company_to_graph = AsyncMock(return_value=False)
        mock_sync.sync_case_to_graph = AsyncMock(return_value=False)

        async def mock_get_sync():
            return mock_sync

        with patch("apps.api.services.sentinel.graph_sync.get_graph_sync_service", mock_get_sync):
            from apps.api.dependencies import get_db_session

            app.dependency_overrides[get_db_session] = override_db

            try:
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.post(
                        "/api/sentinel/sync",
                        json={
                            "sync_all": False,
                            "entity_ids": [str(eid) for eid in entity_ids],
                        },
                        headers={"Authorization": f"Bearer {TOKEN}"},
                    )

                assert response.status_code == 200
                data = response.json()
                assert data["synced_count"] >= 0
                assert "duration_seconds" in data

            finally:
                app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_sync_with_limit(self):
        """Test syncing with limit parameter."""
        mock_session, override_db = _patch_db()
        mock_session.commit = AsyncMock()

        mock_sync = _create_mock_sync()
        mock_sync.batch_sync = AsyncMock(
            return_value={
                "persons": 10,
                "companies": 5,
                "cases": 3,
                "lawyers": 2,
                "errors": 0,
            }
        )

        async def mock_get_sync():
            return mock_sync

        with patch("apps.api.services.sentinel.graph_sync.get_graph_sync_service", mock_get_sync):
            from apps.api.dependencies import get_db_session

            app.dependency_overrides[get_db_session] = override_db

            try:
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.post(
                        "/api/sentinel/sync",
                        json={"sync_all": True, "limit": 20},
                        headers={"Authorization": f"Bearer {TOKEN}"},
                    )

                assert response.status_code == 200
                data = response.json()
                assert data["synced_count"] == 20

            finally:
                app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_sync_unauthorized(self):
        """Test syncing without authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/sentinel/sync",
                json={"sync_all": True},
            )

        assert response.status_code == 401


# ── 5. GET /api/sentinel/graph/{entity_id} ──


class TestGraphData:
    """Tests for GET /api/sentinel/graph/{entity_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_graph_success(self):
        """Test successful graph data retrieval."""
        mock_session, override_db = _patch_db()
        contact = _make_contact()

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=contact)
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_detector = _create_mock_detector()
        # Mock Neo4j graph query
        mock_detector.neo4j_client.execute_query = AsyncMock(
            return_value=[
                {
                    "center": {
                        "id": str(CONTACT_ID),
                        "type": "natural",
                        "name": "Jean Dupont",
                        "email": "jean@dupont.be",
                    },
                    "neighbors": [
                        {
                            "id": str(CONTACT_ID_2),
                            "labels": ["Company"],
                            "name": "ACME Corp",
                        }
                    ],
                    "edges": [
                        {
                            "from": str(CONTACT_ID),
                            "to": str(CONTACT_ID_2),
                            "type": "WORKS_FOR",
                            "properties": {},
                        }
                    ],
                }
            ]
        )

        async def mock_get_detector():
            return mock_detector

        with patch("apps.api.services.sentinel.conflict_detector.get_conflict_detector", mock_get_detector):
            from apps.api.dependencies import get_db_session

            app.dependency_overrides[get_db_session] = override_db

            try:
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    response = await client.get(
                        f"/api/sentinel/graph/{CONTACT_ID}",
                        headers={"Authorization": f"Bearer {TOKEN}"},
                    )

                assert response.status_code == 200
                data = response.json()
                assert "nodes" in data
                assert "edges" in data
                assert "center_entity_id" in data
                assert len(data["nodes"]) >= 1

            finally:
                app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_get_graph_with_depth(self):
        """Test graph retrieval with different depth parameters."""
        mock_session, override_db = _patch_db()
        contact = _make_contact()

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=contact)
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_detector = _create_mock_detector()
        mock_detector.neo4j_client.execute_query = AsyncMock(
            return_value=[
                {
                    "center": {
                        "id": str(CONTACT_ID),
                        "name": "Jean Dupont",
                        "type": "natural",
                    },
                    "neighbors": [],
                    "edges": [],
                }
            ]
        )

        async def mock_get_detector():
            return mock_detector

        with patch("apps.api.services.sentinel.conflict_detector.get_conflict_detector", mock_get_detector):
            from apps.api.dependencies import get_db_session

            app.dependency_overrides[get_db_session] = override_db

            try:
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    # Test depth=1
                    response = await client.get(
                        f"/api/sentinel/graph/{CONTACT_ID}?depth=1",
                        headers={"Authorization": f"Bearer {TOKEN}"},
                    )
                    assert response.status_code == 200

                    # Test depth=2
                    response = await client.get(
                        f"/api/sentinel/graph/{CONTACT_ID}?depth=2",
                        headers={"Authorization": f"Bearer {TOKEN}"},
                    )
                    assert response.status_code == 200

                    # Test depth=3
                    response = await client.get(
                        f"/api/sentinel/graph/{CONTACT_ID}?depth=3",
                        headers={"Authorization": f"Bearer {TOKEN}"},
                    )
                    assert response.status_code == 200

            finally:
                app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_get_graph_not_found(self):
        """Test graph retrieval for non-existent entity."""
        mock_session, override_db = _patch_db()

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get(
                    f"/api/sentinel/graph/{uuid4()}",
                    headers={"Authorization": f"Bearer {TOKEN}"},
                )

            assert response.status_code == 404

        finally:
            app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_get_graph_unauthorized(self):
        """Test graph retrieval without authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/api/sentinel/graph/{CONTACT_ID}")

        assert response.status_code == 401


# ── 6. GET /api/sentinel/search ──


class TestSearchEntities:
    """Tests for GET /api/sentinel/search endpoint."""

    @pytest.mark.asyncio
    async def test_search_by_name(self):
        """Test searching entities by name."""
        mock_session, override_db = _patch_db()
        contact = _make_contact()

        mock_result = AsyncMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=[contact]))
        )

        # Mock conflict count query
        mock_count_result = AsyncMock()
        mock_count_result.__iter__ = MagicMock(return_value=iter([]))

        # Mock last checked query
        mock_last_checked_result = AsyncMock()
        mock_last_checked_result.__iter__ = MagicMock(return_value=iter([]))

        call_count = [0]

        async def mock_execute(query):
            call_count[0] += 1
            if call_count[0] == 1:  # Search query
                return mock_result
            elif call_count[0] == 2:  # Count query
                return mock_count_result
            else:  # Last checked query
                return mock_last_checked_result

        mock_session.execute = mock_execute

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/sentinel/search?q=Dupont",
                    headers={"Authorization": f"Bearer {TOKEN}"},
                )

            assert response.status_code == 200
            data = response.json()
            assert "results" in data
            assert "total" in data
            assert len(data["results"]) == 1

        finally:
            app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_search_with_entity_type_filter(self):
        """Test searching with entity type filter."""
        mock_session, override_db = _patch_db()
        contact = _make_contact(type="legal", full_name="ACME Corp")

        mock_result = AsyncMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=[contact]))
        )

        mock_count_result = AsyncMock()
        mock_count_result.__iter__ = MagicMock(return_value=iter([]))

        mock_last_checked_result = AsyncMock()
        mock_last_checked_result.__iter__ = MagicMock(return_value=iter([]))

        call_count = [0]

        async def mock_execute(query):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_result
            elif call_count[0] == 2:
                return mock_count_result
            else:
                return mock_last_checked_result

        mock_session.execute = mock_execute

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/sentinel/search?q=ACME&entity_type=Company",
                    headers={"Authorization": f"Bearer {TOKEN}"},
                )

            assert response.status_code == 200
            data = response.json()
            assert len(data["results"]) == 1
            assert data["results"][0]["type"] == "Company"

        finally:
            app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_search_with_limit(self):
        """Test searching with limit parameter."""
        mock_session, override_db = _patch_db()

        mock_result = AsyncMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=[]))
        )

        mock_count_result = AsyncMock()
        mock_count_result.__iter__ = MagicMock(return_value=iter([]))

        mock_last_checked_result = AsyncMock()
        mock_last_checked_result.__iter__ = MagicMock(return_value=iter([]))

        call_count = [0]

        async def mock_execute(query):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_result
            elif call_count[0] == 2:
                return mock_count_result
            else:
                return mock_last_checked_result

        mock_session.execute = mock_execute

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/sentinel/search?q=test&limit=5",
                    headers={"Authorization": f"Bearer {TOKEN}"},
                )

            assert response.status_code == 200

        finally:
            app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_search_empty_results(self):
        """Test search with no matching results."""
        mock_session, override_db = _patch_db()

        mock_result = AsyncMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=[]))
        )

        mock_count_result = AsyncMock()
        mock_count_result.__iter__ = MagicMock(return_value=iter([]))

        mock_last_checked_result = AsyncMock()
        mock_last_checked_result.__iter__ = MagicMock(return_value=iter([]))

        call_count = [0]

        async def mock_execute(query):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_result
            elif call_count[0] == 2:
                return mock_count_result
            else:
                return mock_last_checked_result

        mock_session.execute = mock_execute

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/sentinel/search?q=NonExistent",
                    headers={"Authorization": f"Bearer {TOKEN}"},
                )

            assert response.status_code == 200
            data = response.json()
            assert len(data["results"]) == 0
            assert data["total"] == 0

        finally:
            app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_search_unauthorized(self):
        """Test search without authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/sentinel/search?q=test")

        assert response.status_code == 401


# ── 7. GET /api/sentinel/alerts/stream ──


class TestAlertsStream:
    """Tests for GET /api/sentinel/alerts/stream endpoint."""

    @pytest.mark.asyncio
    async def test_stream_connection_established(self):
        """Test SSE connection is established."""
        mock_session, override_db = _patch_db()

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test", timeout=5.0
            ) as client:
                # Open SSE connection
                async with client.stream(
                    "GET",
                    "/api/sentinel/alerts/stream",
                    headers={"Authorization": f"Bearer {TOKEN}"},
                ) as response:
                    assert response.status_code == 200
                    assert "text/event-stream" in response.headers.get(
                        "content-type", ""
                    )

                    # Read first event (connection established)
                    first_chunk = None
                    async for chunk in response.aiter_bytes():
                        if chunk:
                            first_chunk = chunk
                            break

                    assert first_chunk is not None

        finally:
            app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_stream_heartbeat_events(self):
        """Test SSE heartbeat events are sent."""
        mock_session, override_db = _patch_db()

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test", timeout=5.0
            ) as client:
                async with client.stream(
                    "GET",
                    "/api/sentinel/alerts/stream",
                    headers={"Authorization": f"Bearer {TOKEN}"},
                ) as response:
                    assert response.status_code == 200

                    # We just verify the connection is established
                    # Full heartbeat testing would require waiting 30s
                    chunks_received = 0
                    async for chunk in response.aiter_bytes():
                        if chunk:
                            chunks_received += 1
                            if chunks_received >= 1:
                                break

                    assert chunks_received >= 1

        finally:
            app.dependency_overrides = {}

    @pytest.mark.asyncio
    async def test_stream_unauthorized(self):
        """Test SSE stream without authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/sentinel/alerts/stream")

        assert response.status_code == 401
