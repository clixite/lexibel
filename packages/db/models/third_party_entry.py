"""ThirdPartyEntry model — Compte de tiers (third-party account).

APPEND-ONLY for OBFG/OVB compliance. Corrections are reversal entries.
Principle P2: No UPDATE, no DELETE at database level.
Protected by RLS via tenant_id.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import BigInteger, Date, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base, TenantMixin


class ThirdPartyEntry(TenantMixin, Base):
    __tablename__ = "third_party_entries"

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
    entry_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="deposit | withdrawal | interest",
    )
    amount_cents: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    reference: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Bank reference or internal reference",
    )
    entry_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=text("now()"),
    )

    def __repr__(self) -> str:
        return f"<ThirdPartyEntry {self.entry_type} {self.amount_cents}c>"
