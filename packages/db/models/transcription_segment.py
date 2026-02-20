"""Transcription segment model for timestamped text."""

import uuid
from decimal import Decimal

from sqlalchemy import (
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base, TimestampMixin


class TranscriptionSegment(TimestampMixin, Base):
    """Individual timestamped segment of a transcription."""

    __tablename__ = "transcription_segments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    transcription_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transcriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Segment order within transcription
    segment_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Segment order in transcription",
    )

    # Speaker diarization (if available)
    speaker: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Speaker identifier for diarization",
    )

    # Timestamp in seconds
    start_time: Mapped[Decimal] = mapped_column(
        Numeric(10, 3),
        nullable=False,
        comment="Segment start time in seconds",
    )
    end_time: Mapped[Decimal] = mapped_column(
        Numeric(10, 3),
        nullable=False,
        comment="Segment end time in seconds",
    )

    # Segment text
    text: Mapped[str] = mapped_column(Text, nullable=False)

    # Confidence score from STT model (0.0 to 1.0)
    confidence: Mapped[Decimal | None] = mapped_column(
        Numeric(3, 2),
        nullable=True,
        comment="STT confidence score 0.0-1.0",
    )

    __table_args__ = (
        Index(
            "idx_transcription_segments_transcription",
            "transcription_id",
            "segment_index",
        ),
        # Unique constraint: one segment per index per transcription
        UniqueConstraint(
            "transcription_id", "segment_index", name="uq_transcription_segment_idx"
        ),
    )
