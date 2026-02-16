"""InvoiceLine model — individual line items on an invoice.

Each line can optionally reference a time entry for traceability.
Protected by RLS via tenant_id.
"""

import uuid
from decimal import Decimal

from sqlalchemy import BigInteger, ForeignKey, Integer, Numeric, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base, TenantMixin


class InvoiceLine(TenantMixin, Base):
    __tablename__ = "invoice_lines"

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
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Hours or units",
    )
    unit_price_cents: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="Price per unit in cents",
    )
    total_cents: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="quantity * unit_price_cents",
    )
    time_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("time_entries.id", ondelete="SET NULL"),
        nullable=True,
        comment="Link to source time entry for traceability",
    )
    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )

    def __repr__(self) -> str:
        return f"<InvoiceLine {self.description[:30]} {self.total_cents}c>"
