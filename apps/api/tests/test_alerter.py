"""Tests for SENTINEL alerter service."""
import pytest
from datetime import datetime
from uuid import uuid4

from apps.api.services.sentinel.alerter import ConflictAlerter, AlertSeverity
from packages.db.models.sentinel_conflict import SentinelConflict


@pytest.mark.asyncio
async def test_get_severity_level():
    """Test severity level mapping."""
    alerter = ConflictAlerter(None)

    assert alerter.get_severity_level(100) == AlertSeverity.CRITICAL
    assert alerter.get_severity_level(75) == AlertSeverity.HIGH
    assert alerter.get_severity_level(55) == AlertSeverity.MEDIUM
    assert alerter.get_severity_level(40) == AlertSeverity.LOW


@pytest.mark.asyncio
async def test_create_conflict_alert():
    """Test conflict alert creation."""
    alerter = ConflictAlerter(None)

    conflict = SentinelConflict(
        id=uuid4(),
        tenant_id=uuid4(),
        trigger_entity_id=uuid4(),
        trigger_entity_type="contact",
        conflict_type="direct_adversary",
        severity_score=95,
        description="Client opposes new contact in active case",
        conflicting_entity_id=uuid4(),
        conflicting_entity_type="company"
    )

    alert = await alerter.create_conflict_alert(conflict, uuid4())

    assert alert["type"] == "conflict_detected"
    assert alert["severity"] == AlertSeverity.CRITICAL
    assert alert["conflict_score"] == 95
    assert "Review" in str(alert["actions"])


@pytest.mark.asyncio
async def test_sse_connection_registration():
    """Test SSE connection registration."""
    alerter = ConflictAlerter(None)
    user_id = uuid4()
    connection = "mock_connection"

    alerter.register_sse_connection(user_id, connection)

    assert user_id in alerter.sse_connections
    assert connection in alerter.sse_connections[user_id]

    alerter.unregister_sse_connection(user_id, connection)
    assert connection not in alerter.sse_connections[user_id]
