"""LXB-008: Create email_threads and email_messages tables for email sync.

Revision ID: 008
Revises: 007
Create Date: 2026-02-17
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── email_threads ──
    op.create_table(
        "email_threads",
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
            sa.ForeignKey("cases.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("external_id", sa.String(255), nullable=False, index=True),
        sa.Column("provider", sa.String(50), nullable=False, index=True),
        sa.Column("subject", sa.String(500), nullable=True),
        sa.Column(
            "participants", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column(
            "message_count", sa.Integer, nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "has_attachments",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "is_important", sa.Boolean, nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "last_message_at", sa.DateTime(timezone=True), nullable=True, index=True
        ),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at", sa.DateTime, nullable=False, server_default=sa.text("now()")
        ),
    )

    # RLS for email_threads
    op.execute("ALTER TABLE email_threads ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON email_threads
        USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid)
        """
    )

    # Indexes
    op.create_index(
        "idx_email_threads_tenant_case", "email_threads", ["tenant_id", "case_id"]
    )
    op.create_index(
        "idx_email_threads_external_provider",
        "email_threads",
        ["external_id", "provider"],
        unique=True,
    )

    # ── email_messages ──
    op.create_table(
        "email_messages",
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
            "thread_id",
            UUID(as_uuid=True),
            sa.ForeignKey("email_threads.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("external_id", sa.String(255), nullable=False, index=True),
        sa.Column("provider", sa.String(50), nullable=False, index=True),
        sa.Column("subject", sa.String(500), nullable=True),
        sa.Column("from_address", sa.String(255), nullable=False, index=True),
        sa.Column(
            "to_addresses", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
        sa.Column(
            "cc_addresses", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
        sa.Column(
            "bcc_addresses",
            JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("body_text", sa.Text, nullable=True),
        sa.Column("body_html", sa.Text, nullable=True),
        sa.Column(
            "attachments", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
        sa.Column(
            "is_read", sa.Boolean, nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "is_important", sa.Boolean, nullable=False, server_default=sa.text("false")
        ),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at", sa.DateTime, nullable=False, server_default=sa.text("now()")
        ),
    )

    # RLS for email_messages
    op.execute("ALTER TABLE email_messages ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON email_messages
        USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid)
        """
    )

    # Indexes
    op.create_index(
        "idx_email_messages_tenant_thread", "email_messages", ["tenant_id", "thread_id"]
    )
    op.create_index(
        "idx_email_messages_external_provider",
        "email_messages",
        ["external_id", "provider"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("email_messages")
    op.drop_table("email_threads")
