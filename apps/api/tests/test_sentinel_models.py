"""Tests for SENTINEL models."""

import uuid


from packages.db.models.sentinel_conflict import SentinelConflict
from packages.db.models.sentinel_entity import SentinelEntity


def test_sentinel_conflict_model():
    """Test SentinelConflict model structure."""
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    trigger_entity_id = uuid.UUID("00000000-0000-0000-0000-000000000002")
    conflicting_entity_id = uuid.UUID("00000000-0000-0000-0000-000000000003")

    conflict = SentinelConflict(
        tenant_id=tenant_id,
        trigger_entity_id=trigger_entity_id,
        trigger_entity_type="contact",
        conflict_type="direct_adversary",
        severity_score=85,
        description="Conflict detected",
        conflicting_entity_id=conflicting_entity_id,
        conflicting_entity_type="case",
        graph_path=[{"node": "A", "edge": "adversary"}],
    )

    assert conflict.trigger_entity_id == trigger_entity_id
    assert conflict.trigger_entity_type == "contact"
    assert conflict.conflict_type == "direct_adversary"
    assert conflict.severity_score == 85
    assert conflict.description == "Conflict detected"
    assert conflict.conflicting_entity_id == conflicting_entity_id
    assert conflict.conflicting_entity_type == "case"
    assert conflict.graph_path == [{"node": "A", "edge": "adversary"}]
    assert conflict.tenant_id == tenant_id


def test_sentinel_entity_model():
    """Test SentinelEntity model structure."""
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    lexibel_id = uuid.UUID("00000000-0000-0000-0000-000000000002")

    entity = SentinelEntity(
        tenant_id=tenant_id,
        entity_type="company",
        lexibel_id=lexibel_id,
        neo4j_id="neo4j_123",
        enrichment_data={"bce": "0123456789"},
    )

    assert entity.entity_type == "company"
    assert entity.lexibel_id == lexibel_id
    assert entity.neo4j_id == "neo4j_123"
    assert entity.enrichment_data == {"bce": "0123456789"}
    assert entity.tenant_id == tenant_id
