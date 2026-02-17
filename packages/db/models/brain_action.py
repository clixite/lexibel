"""BRAIN action model."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base, TenantMixin, TimestampMixin


class BrainAction(TenantMixin, TimestampMixin, Base):
    """BRAIN action pending or executed."""

    __tablename__ = "brain_actions"

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
    action_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="'alert', 'draft', 'suggestion', 'auto_send'",
    )
    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'normal'"),
        index=True,
        comment="'critical', 'urgent', 'normal'",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'pending'"),
        index=True,
        comment="'pending', 'approved', 'rejected', 'executed'",
    )
    confidence_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="0.0-1.0",
    )
    trigger_source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="'call', 'email', 'document', 'deadline'",
    )
    trigger_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    action_data: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    generated_content: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    executed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    feedback: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    # case: Mapped["Case"] = relationship("Case")
    # reviewer: Mapped["User"] = relationship("User", foreign_keys=[reviewed_by])

    def __repr__(self) -> str:
        return f"<BrainAction {self.action_type} {self.status}>"
