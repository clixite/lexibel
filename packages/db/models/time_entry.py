"""TimeEntry model — billable time tracking for cases.

Time entries go through a lifecycle: draft → submitted → approved → invoiced.
Rounding rules are configurable per entry (6/10/15 min or none).
Protected by RLS via tenant_id.
"""

import uuid
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base, TenantMixin, TimestampMixin


class TimeEntry(TenantMixin, TimestampMixin, Base):
    __tablename__ = "time_entries"

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
        ForeignKey("cases.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Lawyer who performed the work",
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    duration_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Duration after rounding rule applied",
    )
    billable: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )
    date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Date the work was performed",
    )
    rounding_rule: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        server_default=text("'6min'"),
        comment="6min | 10min | 15min | none",
    )
    source: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'MANUAL'"),
        index=True,
        comment="MANUAL | TIMER | RINGOVER | PLAUD | OUTLOOK",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'draft'"),
        index=True,
        comment="draft | submitted | approved | invoiced",
    )
    hourly_rate_cents: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Rate snapshot at time of entry (cents)",
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Partner who approved this entry",
    )

    def __repr__(self) -> str:
        return f"<TimeEntry {self.date} {self.duration_minutes}min {self.status}>"
