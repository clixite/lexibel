"""Email message model for individual emails."""

import uuid
from sqlalchemy import Column, String, Text, Boolean, ForeignKey, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from packages.db.base import Base, TenantMixin, TimestampMixin


class EmailMessage(Base, TenantMixin, TimestampMixin):
    """Individual email message within a thread."""

    __tablename__ = "email_messages"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
    )
    thread_id = Column(
        UUID(as_uuid=True),
        ForeignKey("email_threads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # External message ID from provider
    external_id = Column(String(255), nullable=False, index=True)

    # Provider: 'outlook', 'google'
    provider = Column(String(50), nullable=False, index=True)

    subject = Column(String(500), nullable=True)

    from_address = Column(String(255), nullable=False, index=True)
    to_addresses = Column(JSONB, nullable=False, default=list, server_default="[]")
    cc_addresses = Column(JSONB, nullable=False, default=list, server_default="[]")
    bcc_addresses = Column(JSONB, nullable=False, default=list, server_default="[]")

    body_text = Column(Text, nullable=True)
    body_html = Column(Text, nullable=True)

    # Attachments: [{filename, size, content_type, download_url}]
    attachments = Column(JSONB, nullable=False, default=list, server_default="[]")

    is_read = Column(Boolean, default=False, server_default="false")
    is_important = Column(Boolean, default=False, server_default="false")

    received_at = Column(DateTime(timezone=True), nullable=True, index=True)
    synced_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    thread = relationship("EmailThread")

    __table_args__ = (
        Index("idx_email_messages_tenant_thread", "tenant_id", "thread_id"),
        Index("idx_email_messages_received", "received_at"),
        # Unique constraint per provider
        {"unique_constraint": ("external_id", "provider")},
    )
