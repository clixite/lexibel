"""Transcription model for AI-powered audio transcription."""
from sqlalchemy import Column, String, Text, Integer, Numeric, ForeignKey, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from packages.db.base import Base
from packages.db.mixins import TenantMixin, TimestampMixin


class Transcription(Base, TenantMixin, TimestampMixin):
    """AI transcription of audio (calls, meetings, notes)."""

    __tablename__ = "transcriptions"

    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="SET NULL"), nullable=True, index=True)

    # Source: 'ringover', 'plaud', 'manual'
    source = Column(String(50), nullable=False, index=True)

    audio_url = Column(String(500), nullable=True)
    audio_duration_seconds = Column(Integer, nullable=True)

    # Language detected: 'fr', 'nl', 'en'
    language = Column(String(10), nullable=True)

    # Status: 'pending', 'processing', 'completed', 'failed'
    status = Column(String(50), nullable=False, default='pending', index=True)

    # Full transcript text
    full_text = Column(Text, nullable=True)

    # AI-generated summary
    summary = Column(Text, nullable=True)

    # Sentiment analysis: -1.0 (very negative) to 1.0 (very positive)
    sentiment_score = Column(Numeric(3, 2), nullable=True)
    sentiment_label = Column(String(50), nullable=True)  # 'positive', 'neutral', 'negative'

    # Extracted tasks/action items
    extracted_tasks = Column(JSONB, nullable=False, default=list, server_default='[]')

    # Additional metadata
    metadata = Column(JSONB, nullable=False, default=dict, server_default='{}')

    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    case = relationship("Case", back_populates="transcriptions")
    segments = relationship("TranscriptionSegment", back_populates="transcription", cascade="all, delete-orphan", order_by="TranscriptionSegment.segment_index")
    call_record = relationship("CallRecord", back_populates="transcription", uselist=False)

    __table_args__ = (
        Index('idx_transcriptions_tenant_case', 'tenant_id', 'case_id'),
        Index('idx_transcriptions_status', 'status'),
        Index('idx_transcriptions_source', 'source'),
    )
