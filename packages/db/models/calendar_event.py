"""Calendar event model for Outlook/Google Calendar sync."""

import uuid
from sqlalchemy import Column, String, Text, ForeignKey, DateTime, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from packages.db.base import Base, TenantMixin, TimestampMixin


class CalendarEvent(Base, TenantMixin, TimestampMixin):
    """Synced calendar event from Outlook or Google Calendar."""

    __tablename__ = "calendar_events"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    case_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # External ID from provider
    external_id = Column(String(255), nullable=False, index=True)

    # Provider: 'outlook', 'google'
    provider = Column(String(50), nullable=False, index=True)

    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    end_time = Column(DateTime(timezone=True), nullable=False)

    location = Column(String(500), nullable=True)

    # Attendees: [{email, name, status}]
    attendees = Column(JSONB, nullable=False, default=list, server_default="[]")

    # Is all-day event
    is_all_day = Column(Boolean, default=False, server_default="false")

    # Additional metadata
    metadata_ = Column(
        "metadata", JSONB, nullable=False, default=dict, server_default="{}"
    )

    # Last sync timestamp
    synced_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="calendar_events")
    case = relationship("Case", back_populates="calendar_events")

    __table_args__ = (
        Index("idx_calendar_events_tenant_user", "tenant_id", "user_id"),
        Index("idx_calendar_events_start_time", "start_time"),
        # Unique constraint per provider
        {"unique_constraint": ("external_id", "provider")},
    )
