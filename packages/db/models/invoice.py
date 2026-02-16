"""Invoice model — client invoicing with Peppol support.

Invoices follow Belgian VAT rules (21% standard) and can be exported
as UBL 2.1 / BIS Billing 3.0 for Peppol e-invoicing.
Protected by RLS via tenant_id.
"""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import BigInteger, Date, ForeignKey, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base, TenantMixin, TimestampMixin


class Invoice(TenantMixin, TimestampMixin, Base):
    __tablename__ = "invoices"

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
    )
    invoice_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Sequential number, unique per tenant",
    )
    client_contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'draft'"),
        index=True,
        comment="draft | sent | paid | overdue | cancelled",
    )
    issue_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        server_default=text("CURRENT_DATE"),
    )
    due_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Payment due date (typically issue_date + 30 days)",
    )
    subtotal_cents: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        server_default=text("0"),
        comment="Total before VAT (cents)",
    )
    vat_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        server_default=text("21.00"),
        comment="Belgian standard VAT rate",
    )
    vat_amount_cents: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        server_default=text("0"),
        comment="VAT amount (cents)",
    )
    total_cents: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        server_default=text("0"),
        comment="Total including VAT (cents)",
    )
    peppol_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'none'"),
        comment="none | generated | sent | acknowledged | rejected",
    )
    peppol_ubl_xml: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Generated UBL 2.1 / BIS Billing 3.0 XML",
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        server_default=text("'EUR'"),
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<Invoice {self.invoice_number} {self.status} {self.total_cents}c>"
