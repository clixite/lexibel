"""Email thread model for conversation grouping."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base, TenantMixin, TimestampMixin


class EmailThread(TenantMixin, TimestampMixin, Base):
    """Email conversation thread from Outlook or Gmail."""

    __tablename__ = "email_threads"

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

    # External thread ID from provider
    external_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="External thread ID from email provider",
    )

    # Provider: 'outlook', 'google'
    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Email provider: outlook or google",
    )

    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Participants: {from: {email, name}, to: [], cc: [], bcc: []}
    participants: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    message_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )
    has_attachments: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    is_important: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )

    last_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        Index("idx_email_threads_tenant_case", "tenant_id", "case_id"),
        Index("idx_email_threads_last_message", "last_message_at"),
        # Unique constraint per provider
        {"unique_constraint": ("external_id", "provider")},
    )
