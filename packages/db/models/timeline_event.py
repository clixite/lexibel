"""TIMELINE event model."""

import uuid
from datetime import date, time

from sqlalchemy import Boolean, Date, Float, ForeignKey, String, Text, Time, text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base, TenantMixin, TimestampMixin


class TimelineEvent(TenantMixin, TimestampMixin, Base):
    """TIMELINE NLP-extracted event with validation."""

    __tablename__ = "timeline_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )
    event_time: Mapped[time | None] = mapped_column(
        Time,
        nullable=True,
    )
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="'meeting', 'call', 'email', 'signature'",
    )
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    actors: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        server_default=text("'{}'::text[]"),
        comment="List of person/company names",
    )
    location: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )
    source_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="'email', 'call', 'document', 'manual'",
    )
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    source_excerpt: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Original text",
    )
    confidence_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="0.0-1.0",
    )
    is_validated: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    is_key_event: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
        comment="Highlighted in timeline",
    )
    evidence_links: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)),
        nullable=False,
        server_default=text("'{}'::uuid[]"),
        comment="Links to documents",
    )
    created_by: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="'ai' or user_id",
    )
    validated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<TimelineEvent {self.category} {self.event_date}>"
