"""Email thread model for conversation grouping."""

import uuid
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from packages.db.base import Base, TenantMixin, TimestampMixin


class EmailThread(Base, TenantMixin, TimestampMixin):
    """Email conversation thread from Outlook or Gmail."""

    __tablename__ = "email_threads"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
    )
    case_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # External thread ID from provider
    external_id = Column(String(255), nullable=False, index=True)

    # Provider: 'outlook', 'google'
    provider = Column(String(50), nullable=False, index=True)

    subject = Column(String(500), nullable=True)

    # Participants: {from: {email, name}, to: [], cc: [], bcc: []}
    participants = Column(JSONB, nullable=False, default=dict, server_default="{}")

    message_count = Column(Integer, nullable=False, default=0, server_default="0")
    has_attachments = Column(Boolean, default=False, server_default="false")
    is_important = Column(Boolean, default=False, server_default="false")

    last_message_at = Column(DateTime(timezone=True), nullable=True, index=True)
    synced_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    case = relationship("Case", back_populates="email_threads")
    messages = relationship(
        "EmailMessage", back_populates="thread", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_email_threads_tenant_case", "tenant_id", "case_id"),
        Index("idx_email_threads_last_message", "last_message_at"),
        # Unique constraint per provider
        {"unique_constraint": ("external_id", "provider")},
    )
