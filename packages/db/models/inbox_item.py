"""InboxItem model — unvalidated items awaiting human review.

Principle P4: Human-in-the-Loop — items start as DRAFT until a user
validates or refuses them. Validation creates an InteractionEvent.
Protected by RLS via tenant_id.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base, TenantMixin


class InboxItem(TenantMixin, Base):
    __tablename__ = "inbox_items"

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
    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="OUTLOOK | RINGOVER | PLAUD | DPA_DEPOSIT | DPA_JBOX | MANUAL",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'DRAFT'"),
        index=True,
        comment="DRAFT | VALIDATED | REFUSED",
    )
    raw_payload: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="Original webhook/ingestion payload",
    )
    suggested_case_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="SET NULL"),
        nullable=True,
        comment="AI-suggested case for auto-attach",
    )
    confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="AI confidence score for suggested_case_id",
    )
    validated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    validated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=text("now()"),
    )

    def __repr__(self) -> str:
        return f"<InboxItem {self.source} {self.status}>"
