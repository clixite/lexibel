"""InteractionEvent model — append-only event store.

Principle P2: Event-Sourced Timeline — no UPDATE, no DELETE.
PostgreSQL GRANT enforces INSERT-only at the database level.
Protected by RLS via tenant_id.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base, TenantMixin


class InteractionEvent(TenantMixin, Base):
    __tablename__ = "interaction_events"

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
    case_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
        comment="Linked case (nullable for unassigned inbox items)",
    )
    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="OUTLOOK | RINGOVER | PLAUD | DPA_DEPOSIT | DPA_JBOX | MANUAL",
    )
    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="EMAIL | CALL | TRANSCRIPT | DEPOSIT | COURT_DOC | DOCUMENT | INTERNAL_NOTE | MEETING",
    )
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    body: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Full text body / summary",
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="When the interaction actually happened",
    )
    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        comment="Type-specific metadata (headers, duration, participants...)",
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="User who created this event (NULL for system/webhook)",
    )
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=text("now()"),
    )

    def __repr__(self) -> str:
        return f"<InteractionEvent {self.event_type} {self.title[:30]}>"
