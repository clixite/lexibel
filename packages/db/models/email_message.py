"""Email message model for individual emails."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base, TenantMixin, TimestampMixin


class EmailMessage(TenantMixin, TimestampMixin, Base):
    """Individual email message within a thread."""

    __tablename__ = "email_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("email_threads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # External message ID from provider
    external_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="External message ID from email provider",
    )

    # Provider: 'outlook', 'google'
    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Email provider: outlook or google",
    )

    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)

    from_address: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    to_addresses: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    cc_addresses: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    bcc_addresses: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )

    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_html: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Attachments: [{filename, size, content_type, download_url}]
    attachments: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )

    is_read: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    is_important: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )

    received_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        Index("idx_email_messages_tenant_thread", "tenant_id", "thread_id"),
        Index("idx_email_messages_received", "received_at"),
        # Unique constraint per provider
        {"unique_constraint": ("external_id", "provider")},
    )
