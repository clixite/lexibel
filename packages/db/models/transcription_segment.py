"""Transcription segment model for timestamped text."""

import uuid
from sqlalchemy import Column, String, Text, Integer, Numeric, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from packages.db.base import Base, TimestampMixin


class TranscriptionSegment(Base, TimestampMixin):
    """Individual timestamped segment of a transcription."""

    __tablename__ = "transcription_segments"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
    )
    transcription_id = Column(
        UUID(as_uuid=True),
        ForeignKey("transcriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Segment order within transcription
    segment_index = Column(Integer, nullable=False)

    # Speaker diarization (if available)
    speaker = Column(String(100), nullable=True)

    # Timestamp in seconds
    start_time = Column(Numeric(10, 3), nullable=False)  # e.g., 12.345 seconds
    end_time = Column(Numeric(10, 3), nullable=False)

    # Segment text
    text = Column(Text, nullable=False)

    # Confidence score from STT model (0.0 to 1.0)
    confidence = Column(Numeric(3, 2), nullable=True)

    # Relationships
    transcription = relationship("Transcription", back_populates="segments")

    __table_args__ = (
        Index(
            "idx_transcription_segments_transcription",
            "transcription_id",
            "segment_index",
        ),
        # Unique constraint: one segment per index per transcription
        {"unique_constraint": ("transcription_id", "segment_index")},
    )
