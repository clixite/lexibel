"""Tests for graph sync service."""

import pytest
import uuid
from datetime import date
from unittest.mock import AsyncMock, patch, MagicMock

from apps.api.services.sentinel.graph_sync import (
    GraphSyncService,
    get_graph_sync_service,
)


@pytest.mark.asyncio
async def test_sync_person_creates_node():
    """Test person sync creates Neo4j node."""
    # This test requires actual Neo4j and PostgreSQL running
    # For now, we test that the service initializes correctly
    service = GraphSyncService()

    # Mock the Neo4j client
    mock_neo4j = AsyncMock()
    mock_neo4j.execute_query = AsyncMock(return_value=[{"p": {"name": "Test"}}])
    service.neo4j_client = mock_neo4j

    # Mock database query
    person_id = uuid.uuid4()
    mock_person = MagicMock()
    mock_person.id = person_id
    mock_person.type = "natural"
    mock_person.full_name = "Jean Dupont"
    mock_person.email = "jean@example.com"
    mock_person.phone_e164 = "+32470123456"
    mock_person.language = "fr"
    mock_person.address = None

    with patch(
        "apps.api.services.sentinel.graph_sync.get_superadmin_session"
    ) as mock_session:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_person)

        async def mock_execute(*args, **kwargs):
            return mock_result

        mock_sess_obj = MagicMock()
        mock_sess_obj.execute = mock_execute
        mock_sess_obj.__aenter__ = AsyncMock(return_value=mock_sess_obj)
        mock_sess_obj.__aexit__ = AsyncMock(return_value=None)

        mock_session.return_value = mock_sess_obj

        # Test sync
        success = await service.sync_person_to_graph(person_id)

        assert success is True
        mock_neo4j.execute_query.assert_called_once()
        call_args = mock_neo4j.execute_query.call_args
        assert "MERGE (p:Person" in call_args[0][0]
        # Check the parameters dict (second argument)
        params = call_args[0][1]
        assert params["name"] == "Jean Dupont"


@pytest.mark.asyncio
async def test_sync_company_with_bce():
    """Test company sync includes BCE number."""
    service = GraphSyncService()

    # Mock the Neo4j client
    mock_neo4j = AsyncMock()
    mock_neo4j.execute_query = AsyncMock(return_value=[{"c": {"name": "Test"}}])
    service.neo4j_client = mock_neo4j

    # Mock database query
    company_id = uuid.uuid4()
    mock_company = MagicMock()
    mock_company.id = company_id
    mock_company.type = "legal"
    mock_company.full_name = "ACME Corp"
    mock_company.email = "info@acme.be"
    mock_company.phone_e164 = "+3225551234"
    mock_company.bce_number = "0123.456.789"
    mock_company.language = "fr"
    mock_company.address = None

    with patch(
        "apps.api.services.sentinel.graph_sync.get_superadmin_session"
    ) as mock_session:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_company)

        async def mock_execute(*args, **kwargs):
            return mock_result

        mock_sess_obj = MagicMock()
        mock_sess_obj.execute = mock_execute
        mock_sess_obj.__aenter__ = AsyncMock(return_value=mock_sess_obj)
        mock_sess_obj.__aexit__ = AsyncMock(return_value=None)

        mock_session.return_value = mock_sess_obj

        # Test sync
        success = await service.sync_company_to_graph(company_id)

        assert success is True
        mock_neo4j.execute_query.assert_called_once()
        call_args = mock_neo4j.execute_query.call_args
        assert "MERGE (c:Company" in call_args[0][0]
        # Check the parameters dict (second argument)
        params = call_args[0][1]
        assert params["bce_number"] == "0123.456.789"


@pytest.mark.asyncio
async def test_sync_case_node():
    """Test case sync creates Neo4j node."""
    service = GraphSyncService()

    # Mock the Neo4j client
    mock_neo4j = AsyncMock()
    mock_neo4j.execute_query = AsyncMock(
        return_value=[{"case": {"reference": "2026/001"}}]
    )
    service.neo4j_client = mock_neo4j

    # Mock database query
    case_id = uuid.uuid4()
    mock_case = MagicMock()
    mock_case.id = case_id
    mock_case.reference = "2026/001"
    mock_case.title = "Test Case"
    mock_case.matter_type = "civil"
    mock_case.status = "open"
    mock_case.jurisdiction = "Brussels"
    mock_case.court_reference = None
    mock_case.opened_at = date(2026, 1, 15)
    mock_case.closed_at = None

    with patch(
        "apps.api.services.sentinel.graph_sync.get_superadmin_session"
    ) as mock_session:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_case)

        async def mock_execute(*args, **kwargs):
            return mock_result

        mock_sess_obj = MagicMock()
        mock_sess_obj.execute = mock_execute
        mock_sess_obj.__aenter__ = AsyncMock(return_value=mock_sess_obj)
        mock_sess_obj.__aexit__ = AsyncMock(return_value=None)

        mock_session.return_value = mock_sess_obj

        # Test sync
        success = await service.sync_case_to_graph(case_id)

        assert success is True
        mock_neo4j.execute_query.assert_called_once()
        call_args = mock_neo4j.execute_query.call_args
        assert "MERGE (case:Case" in call_args[0][0]
        # Check the parameters dict (second argument)
        params = call_args[0][1]
        assert params["reference"] == "2026/001"


@pytest.mark.asyncio
async def test_sync_relationships():
    """Test relationship sync."""
    service = GraphSyncService()

    # Mock the Neo4j client
    mock_neo4j = AsyncMock()
    mock_neo4j.execute_query = AsyncMock(return_value=[])
    service.neo4j_client = mock_neo4j

    # Mock IDs
    case_id = uuid.uuid4()
    lawyer_id = uuid.uuid4()
    person_id = uuid.uuid4()
    company_id = uuid.uuid4()

    # Mock case
    mock_case = MagicMock()
    mock_case.id = case_id
    mock_case.responsible_user_id = lawyer_id
    mock_case.reference = "2026/001"
    mock_case.opened_at = date(2026, 1, 15)

    # Mock lawyer
    mock_lawyer = MagicMock()
    mock_lawyer.id = lawyer_id
    mock_lawyer.full_name = "Marie Avocat"
    mock_lawyer.email = "marie@law.be"
    mock_lawyer.role = "associate"

    # Mock client contact
    mock_client_contact = MagicMock()
    mock_client_contact.case_id = case_id
    mock_client_contact.contact_id = person_id
    mock_client_contact.role = "client"

    # Mock adverse contact
    mock_adverse_contact = MagicMock()
    mock_adverse_contact.case_id = case_id
    mock_adverse_contact.contact_id = company_id
    mock_adverse_contact.role = "adverse"

    # Mock person
    mock_person = MagicMock()
    mock_person.id = person_id
    mock_person.type = "natural"
    mock_person.full_name = "Jean Dupont"

    # Mock company
    mock_company = MagicMock()
    mock_company.id = company_id
    mock_company.type = "legal"
    mock_company.full_name = "ACME Corp"

    with patch(
        "apps.api.services.sentinel.graph_sync.get_superadmin_session"
    ) as mock_session:
        # Create a sequence of mock results for different queries
        mock_case_result = MagicMock()
        mock_case_result.scalar_one_or_none = MagicMock(return_value=mock_case)

        mock_scalars_obj = MagicMock()
        mock_scalars_obj.all = MagicMock(
            return_value=[mock_client_contact, mock_adverse_contact]
        )
        mock_contacts_result = MagicMock()
        mock_contacts_result.scalars = MagicMock(return_value=mock_scalars_obj)

        mock_lawyer_result = MagicMock()
        mock_lawyer_result.scalar_one_or_none = MagicMock(return_value=mock_lawyer)

        mock_person_result = MagicMock()
        mock_person_result.scalar_one_or_none = MagicMock(return_value=mock_person)

        mock_company_result = MagicMock()
        mock_company_result.scalar_one_or_none = MagicMock(return_value=mock_company)

        mock_clients_scalars_obj = MagicMock()
        mock_clients_scalars_obj.all = MagicMock(return_value=[mock_client_contact])
        mock_clients_result = MagicMock()
        mock_clients_result.scalars = MagicMock(return_value=mock_clients_scalars_obj)

        results = [
            mock_case_result,
            mock_contacts_result,
            mock_lawyer_result,
            mock_person_result,
            mock_company_result,
            mock_clients_result,
            mock_person_result,
        ]

        async def mock_execute(*args, **kwargs):
            return results.pop(0)

        mock_sess_obj = MagicMock()
        mock_sess_obj.execute = mock_execute
        mock_sess_obj.__aenter__ = AsyncMock(return_value=mock_sess_obj)
        mock_sess_obj.__aexit__ = AsyncMock(return_value=None)

        mock_session.return_value = mock_sess_obj

        # Test sync
        rel_count = await service.sync_relationships(case_id)

        assert rel_count >= 2  # At least REPRESENTS and OPPOSES
        assert mock_neo4j.execute_query.call_count >= 3  # Lawyer node + relationships


@pytest.mark.asyncio
async def test_batch_sync_performance():
    """Test batch sync handles entities efficiently."""
    service = GraphSyncService()

    # Mock the Neo4j client
    mock_neo4j = AsyncMock()
    mock_neo4j.execute_query = AsyncMock(return_value=[])
    service.neo4j_client = mock_neo4j

    with patch(
        "apps.api.services.sentinel.graph_sync.get_superadmin_session"
    ) as mock_session:
        # Mock empty results
        mock_scalars_obj = MagicMock()
        mock_scalars_obj.all = MagicMock(return_value=[])
        mock_empty_result = MagicMock()
        mock_empty_result.scalars = MagicMock(return_value=mock_scalars_obj)

        async def mock_execute(*args, **kwargs):
            return mock_empty_result

        mock_sess_obj = MagicMock()
        mock_sess_obj.execute = mock_execute
        mock_sess_obj.__aenter__ = AsyncMock(return_value=mock_sess_obj)
        mock_sess_obj.__aexit__ = AsyncMock(return_value=None)

        mock_session.return_value = mock_sess_obj

        # Mock sync methods to avoid recursion
        service.sync_person_to_graph = AsyncMock(return_value=True)
        service.sync_company_to_graph = AsyncMock(return_value=True)
        service.sync_case_to_graph = AsyncMock(return_value=True)
        service.sync_relationships = AsyncMock(return_value=0)

        # Test batch sync
        result = await service.batch_sync(limit=10)

        assert "persons" in result
        assert "companies" in result
        assert "cases" in result
        assert "lawyers" in result
        assert "relationships" in result
        assert "duration_seconds" in result
        assert "errors" in result
        assert result["duration_seconds"] < 10  # Should be very fast with mocks


@pytest.mark.asyncio
async def test_sync_nonexistent_person():
    """Test syncing a non-existent person returns False."""
    service = GraphSyncService()

    # Mock the Neo4j client
    mock_neo4j = AsyncMock()
    service.neo4j_client = mock_neo4j

    fake_id = uuid.uuid4()

    with patch(
        "apps.api.services.sentinel.graph_sync.get_superadmin_session"
    ) as mock_session:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)

        async def mock_execute(*args, **kwargs):
            return mock_result

        mock_sess_obj = MagicMock()
        mock_sess_obj.execute = mock_execute
        mock_sess_obj.__aenter__ = AsyncMock(return_value=mock_sess_obj)
        mock_sess_obj.__aexit__ = AsyncMock(return_value=None)

        mock_session.return_value = mock_sess_obj

        success = await service.sync_person_to_graph(fake_id)
        assert success is False


@pytest.mark.asyncio
async def test_sync_nonexistent_company():
    """Test syncing a non-existent company returns False."""
    service = GraphSyncService()

    # Mock the Neo4j client
    mock_neo4j = AsyncMock()
    service.neo4j_client = mock_neo4j

    fake_id = uuid.uuid4()

    with patch(
        "apps.api.services.sentinel.graph_sync.get_superadmin_session"
    ) as mock_session:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)

        async def mock_execute(*args, **kwargs):
            return mock_result

        mock_sess_obj = MagicMock()
        mock_sess_obj.execute = mock_execute
        mock_sess_obj.__aenter__ = AsyncMock(return_value=mock_sess_obj)
        mock_sess_obj.__aexit__ = AsyncMock(return_value=None)

        mock_session.return_value = mock_sess_obj

        success = await service.sync_company_to_graph(fake_id)
        assert success is False


@pytest.mark.asyncio
async def test_sync_nonexistent_case():
    """Test syncing a non-existent case returns False."""
    service = GraphSyncService()

    # Mock the Neo4j client
    mock_neo4j = AsyncMock()
    service.neo4j_client = mock_neo4j

    fake_id = uuid.uuid4()

    with patch(
        "apps.api.services.sentinel.graph_sync.get_superadmin_session"
    ) as mock_session:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)

        async def mock_execute(*args, **kwargs):
            return mock_result

        mock_sess_obj = MagicMock()
        mock_sess_obj.execute = mock_execute
        mock_sess_obj.__aenter__ = AsyncMock(return_value=mock_sess_obj)
        mock_sess_obj.__aexit__ = AsyncMock(return_value=None)

        mock_session.return_value = mock_sess_obj

        success = await service.sync_case_to_graph(fake_id)
        assert success is False


@pytest.mark.asyncio
async def test_service_initialization():
    """Test service singleton initialization."""
    # This will use mocked Neo4j client
    with patch(
        "apps.api.services.sentinel.graph_sync.get_neo4j_client"
    ) as mock_get_client:
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client

        service = await get_graph_sync_service()

        assert service is not None
        assert service.neo4j_client is not None
        mock_get_client.assert_called_once()
