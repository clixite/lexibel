"""Tests for TIMELINE models."""
import uuid
from datetime import date

import pytest

from packages.db.models.timeline_document import TimelineDocument
from packages.db.models.timeline_event import TimelineEvent


def test_timeline_event_model():
    """Test TimelineEvent model."""
    case_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000002")

    event = TimelineEvent(
        tenant_id=tenant_id,
        case_id=case_id,
        event_date=date(2024, 1, 15),
        category="meeting",
        title="Client meeting",
        description="Initial consultation",
        actors=["John Doe", "Jane Smith"],
        source_type="manual",
        source_excerpt="Meeting notes...",
        confidence_score=1.0,
        created_by="ai",
    )

    assert event.category == "meeting"
    assert event.event_date == date(2024, 1, 15)
    assert event.title == "Client meeting"
    assert event.description == "Initial consultation"
    assert event.actors == ["John Doe", "Jane Smith"]
    assert event.source_type == "manual"
    assert event.source_excerpt == "Meeting notes..."
    assert event.confidence_score == 1.0
    assert event.created_by == "ai"
    assert event.case_id == case_id
    assert event.tenant_id == tenant_id


def test_timeline_document_model():
    """Test TimelineDocument model."""
    case_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000002")
    timeline_id = uuid.UUID("00000000-0000-0000-0000-000000000003")
    generated_by = uuid.UUID("00000000-0000-0000-0000-000000000004")

    doc = TimelineDocument(
        tenant_id=tenant_id,
        case_id=case_id,
        timeline_id=timeline_id,
        format="docx",
        file_path="/path/to/timeline.docx",
        generated_by=generated_by,
        events_count=25,
        date_range_start=date(2024, 1, 1),
        date_range_end=date(2024, 12, 31),
    )

    assert doc.events_count == 25
    assert doc.format == "docx"
    assert doc.file_path == "/path/to/timeline.docx"
    assert doc.timeline_id == timeline_id
    assert doc.generated_by == generated_by
    assert doc.date_range_start == date(2024, 1, 1)
    assert doc.date_range_end == date(2024, 12, 31)
    assert doc.case_id == case_id
    assert doc.tenant_id == tenant_id
