"""LXB-020-024: Create time_entries, invoices, invoice_lines, third_party_entries with RLS.

third_party_entries is APPEND-ONLY (Principle P2, OBFG/OVB compliance).

Revision ID: 004
Revises: 003
Create Date: 2026-02-15
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── time_entries ──
    op.create_table(
        "time_entries",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "case_id",
            UUID(as_uuid=True),
            sa.ForeignKey("cases.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("duration_minutes", sa.Integer, nullable=False),
        sa.Column(
            "billable", sa.Boolean, nullable=False, server_default=sa.text("true")
        ),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column(
            "rounding_rule",
            sa.String(10),
            nullable=False,
            server_default=sa.text("'6min'"),
        ),
        sa.Column(
            "source",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'MANUAL'"),
            index=True,
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'draft'"),
            index=True,
        ),
        sa.Column("hourly_rate_cents", sa.Integer, nullable=True),
        sa.Column(
            "approved_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at", sa.DateTime, nullable=False, server_default=sa.text("now()")
        ),
    )

    # ── invoices ──
    op.create_table(
        "invoices",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "case_id",
            UUID(as_uuid=True),
            sa.ForeignKey("cases.id", ondelete="RESTRICT"),
            nullable=True,
            index=True,
        ),
        sa.Column("invoice_number", sa.String(50), nullable=False),
        sa.Column(
            "client_contact_id",
            UUID(as_uuid=True),
            sa.ForeignKey("contacts.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'draft'"),
            index=True,
        ),
        sa.Column(
            "issue_date",
            sa.Date,
            nullable=False,
            server_default=sa.text("CURRENT_DATE"),
        ),
        sa.Column("due_date", sa.Date, nullable=False),
        sa.Column(
            "subtotal_cents", sa.BigInteger, nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "vat_rate",
            sa.Numeric(5, 2),
            nullable=False,
            server_default=sa.text("21.00"),
        ),
        sa.Column(
            "vat_amount_cents",
            sa.BigInteger,
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "total_cents", sa.BigInteger, nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "peppol_status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'none'"),
        ),
        sa.Column("peppol_ubl_xml", sa.Text, nullable=True),
        sa.Column(
            "currency", sa.String(3), nullable=False, server_default=sa.text("'EUR'")
        ),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at", sa.DateTime, nullable=False, server_default=sa.text("now()")
        ),
        sa.UniqueConstraint(
            "tenant_id", "invoice_number", name="uq_invoices_tenant_number"
        ),
    )

    # ── invoice_lines ──
    op.create_table(
        "invoice_lines",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "invoice_id",
            UUID(as_uuid=True),
            sa.ForeignKey("invoices.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("quantity", sa.Numeric(10, 2), nullable=False),
        sa.Column("unit_price_cents", sa.BigInteger, nullable=False),
        sa.Column("total_cents", sa.BigInteger, nullable=False),
        sa.Column(
            "time_entry_id",
            UUID(as_uuid=True),
            sa.ForeignKey("time_entries.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "sort_order", sa.Integer, nullable=False, server_default=sa.text("0")
        ),
    )

    # ── third_party_entries (append-only, OBFG/OVB compliance) ──
    op.create_table(
        "third_party_entries",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "case_id",
            UUID(as_uuid=True),
            sa.ForeignKey("cases.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column("entry_type", sa.String(20), nullable=False),
        sa.Column("amount_cents", sa.BigInteger, nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("reference", sa.String(100), nullable=False),
        sa.Column("entry_date", sa.Date, nullable=False),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")
        ),
    )

    # ── RLS policies ──
    for table in ("time_entries", "invoices", "invoice_lines", "third_party_entries"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY tenant_isolation_{table} ON {table}
                USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
        """)

    # ── third_party_entries: APPEND-ONLY (Principle P2) ──
    op.execute("REVOKE UPDATE, DELETE ON third_party_entries FROM lexibel")
    op.execute("GRANT INSERT, SELECT ON third_party_entries TO lexibel")


def downgrade() -> None:
    # Restore permissions
    op.execute("GRANT ALL ON third_party_entries TO lexibel")

    for table in ("third_party_entries", "invoice_lines", "invoices", "time_entries"):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table}")
        op.drop_table(table)
