"""TIMELINE document model."""
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base, TenantMixin, TimestampMixin


class TimelineDocument(TenantMixin, TimestampMixin, Base):
    """TIMELINE generated chronology document (Word/PDF)."""

    __tablename__ = "timeline_documents"

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
    timeline_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="References a specific timeline version",
    )
    format: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="'docx', 'pdf', 'html'",
    )
    file_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    generated_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    events_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    date_range_start: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    date_range_end: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    # Relationships
    # case: Mapped["Case"] = relationship("Case")
    # generator: Mapped["User"] = relationship("User", foreign_keys=[generated_by])

    def __repr__(self) -> str:
        return f"<TimelineDocument {self.format} {self.events_count} events>"
