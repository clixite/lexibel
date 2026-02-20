"""Tests for BRAIN models."""

import uuid


from packages.db.models.brain_action import BrainAction
from packages.db.models.brain_insight import BrainInsight
from packages.db.models.brain_memory import BrainMemory


def test_brain_action_model():
    """Test BrainAction model structure."""
    case_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000002")

    action = BrainAction(
        tenant_id=tenant_id,
        case_id=case_id,
        action_type="alert",
        priority="critical",
        confidence_score=0.95,
        trigger_source="call",
        action_data={"message": "test"},
    )

    assert action.action_type == "alert"
    assert action.confidence_score == 0.95
    assert action.priority == "critical"
    assert action.trigger_source == "call"
    assert action.action_data == {"message": "test"}
    assert action.case_id == case_id
    assert action.tenant_id == tenant_id


def test_brain_insight_model():
    """Test BrainInsight model structure."""
    case_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000002")

    insight = BrainInsight(
        tenant_id=tenant_id,
        case_id=case_id,
        insight_type="risk",
        severity="high",
        title="Test Risk",
        description="Test description",
    )

    assert insight.severity == "high"
    assert insight.insight_type == "risk"
    assert insight.title == "Test Risk"
    assert insight.description == "Test description"
    assert insight.case_id == case_id
    assert insight.tenant_id == tenant_id


def test_brain_memory_model():
    """Test BrainMemory model structure."""
    case_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000002")

    memory = BrainMemory(
        tenant_id=tenant_id,
        case_id=case_id,
        memory_type="fact",
        content="Test fact",
        qdrant_id="test_123",
        confidence=0.9,
    )

    assert memory.confidence == 0.9
    assert memory.memory_type == "fact"
    assert memory.content == "Test fact"
    assert memory.qdrant_id == "test_123"
    assert memory.case_id == case_id
    assert memory.tenant_id == tenant_id
