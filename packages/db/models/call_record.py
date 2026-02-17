"""Call record model for Ringover telephony integration."""

import uuid
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from packages.db.base import Base, TenantMixin, TimestampMixin


class CallRecord(Base, TenantMixin, TimestampMixin):
    """Phone call record from Ringover or other telephony providers."""

    __tablename__ = "call_records"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
    )
    case_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    contact_id = Column(
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # External call ID from Ringover
    external_id = Column(String(255), nullable=False, index=True, unique=True)

    # Direction: 'inbound', 'outbound'
    direction = Column(String(50), nullable=False, index=True)

    caller_number = Column(String(50), nullable=True)
    callee_number = Column(String(50), nullable=True)

    duration_seconds = Column(Integer, nullable=True)

    # Call type: 'answered', 'missed', 'voicemail'
    call_type = Column(String(50), nullable=True, index=True)

    # Recording URL from provider
    recording_url = Column(String(500), nullable=True)

    # Link to transcription if available
    transcription_id = Column(
        UUID(as_uuid=True),
        ForeignKey("transcriptions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    started_at = Column(DateTime(timezone=True), nullable=True, index=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)

    # AI insights: {sentiment_score, sentiment_label, ai_summary, extracted_tasks}
    metadata_ = Column("metadata", JSONB, nullable=False, default=dict, server_default="{}")

    synced_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    case = relationship("Case", back_populates="call_records")
    contact = relationship("Contact", back_populates="call_records")
    transcription = relationship(
        "Transcription", back_populates="call_record", uselist=False
    )

    __table_args__ = (
        Index("idx_call_records_tenant_case", "tenant_id", "case_id"),
        Index("idx_call_records_started", "started_at"),
        Index("idx_call_records_direction", "direction"),
    )
