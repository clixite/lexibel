"""LXB-018: Create tenant_settings table for in-app configuration wizard.

Stores API keys, OAuth credentials, and other config per-tenant in DB
instead of .env files. Sensitive values are encrypted at rest (Fernet).

Revision ID: 018
Revises: 017
Create Date: 2026-02-18
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "018"
down_revision: Union[str, None] = "017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenant_settings",
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
        sa.Column("category", sa.String(50), nullable=False, index=True),
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column("value", sa.Text, nullable=False),
        sa.Column(
            "is_encrypted",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("label", sa.String(200), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "is_required",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "updated_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("tenant_id", "key", name="uq_tenant_setting_key"),
    )

    # Enable RLS
    op.execute("ALTER TABLE tenant_settings ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON tenant_settings
        USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid)
        """
    )

    # Index for fast category lookups
    op.create_index(
        "idx_tenant_settings_tenant_category",
        "tenant_settings",
        ["tenant_id", "category"],
    )


def downgrade() -> None:
    op.drop_table("tenant_settings")
