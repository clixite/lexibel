"""Call record model for Ringover telephony integration."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base, TenantMixin, TimestampMixin


class CallRecord(TenantMixin, TimestampMixin, Base):
    """Phone call record from Ringover or other telephony providers."""

    __tablename__ = "call_records"

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
    contact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # External call ID from Ringover
    external_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        unique=True,
        comment="External call ID from telephony provider",
    )

    # Direction: 'inbound', 'outbound'
    direction: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Call direction: inbound or outbound",
    )

    caller_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    callee_number: Mapped[str | None] = mapped_column(String(50), nullable=True)

    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Call type: 'answered', 'missed', 'voicemail'
    call_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        comment="Call type: answered, missed, voicemail",
    )

    # Recording URL from provider
    recording_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Link to transcription if available
    transcription_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transcriptions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # AI insights: {sentiment_score, sentiment_label, ai_summary, extracted_tasks}
    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        Index("idx_call_records_tenant_case", "tenant_id", "case_id"),
        Index("idx_call_records_started", "started_at"),
        Index("idx_call_records_direction", "direction"),
    )
