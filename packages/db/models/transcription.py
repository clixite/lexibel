"""Transcription model for AI-powered audio transcription."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base, TenantMixin, TimestampMixin


class Transcription(TenantMixin, TimestampMixin, Base):
    """AI transcription of audio (calls, meetings, notes)."""

    __tablename__ = "transcriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    case_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Source: 'ringover', 'plaud', 'manual'
    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Transcription source: ringover, plaud, manual",
    )

    audio_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    audio_duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Language detected: 'fr', 'nl', 'en'
    language: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
        comment="Detected language code",
    )

    # Status: 'pending', 'processing', 'completed', 'failed'
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default=text("'pending'"),
        index=True,
        comment="Processing status",
    )

    # Full transcript text
    full_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # AI-generated summary
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Sentiment analysis: -1.0 (very negative) to 1.0 (very positive)
    sentiment_score: Mapped[Decimal | None] = mapped_column(
        Numeric(3, 2),
        nullable=True,
    )
    sentiment_label: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Sentiment: positive, neutral, negative",
    )

    # Extracted tasks/action items
    extracted_tasks: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )

    # Additional metadata
    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        Index("idx_transcriptions_tenant_case", "tenant_id", "case_id"),
        Index("idx_transcriptions_status", "status"),
        Index("idx_transcriptions_source", "source"),
    )
