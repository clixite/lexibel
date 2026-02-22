"""020 — Create email_templates and case_relations tables.

Revision ID: 020
Revises: 019
Create Date: 2026-02-22
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── email_templates ──
    op.create_table(
        "email_templates",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("subject_template", sa.String(500), nullable=False),
        sa.Column("body_template", sa.Text(), nullable=False),
        sa.Column(
            "language", sa.String(5), server_default=sa.text("'fr'"), nullable=False
        ),
        sa.Column(
            "matter_types",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "is_system",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_email_templates"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_email_templates_tenant_id_tenants",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_email_templates_created_by_users",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_email_templates_tenant_id", "email_templates", ["tenant_id"])
    op.create_index("ix_email_templates_category", "email_templates", ["category"])

    # RLS policy
    op.execute("ALTER TABLE email_templates ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON email_templates
        USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid)
        """
    )

    # ── case_relations ──
    op.create_table(
        "case_relations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relation_type", sa.String(50), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_case_relations"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_case_relations_tenant_id_tenants",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_case_id"],
            ["cases.id"],
            name="fk_case_relations_source_case_id_cases",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_case_id"],
            ["cases.id"],
            name="fk_case_relations_target_case_id_cases",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_case_relations_tenant_id", "case_relations", ["tenant_id"])
    op.create_index("ix_case_relations_source", "case_relations", ["source_case_id"])
    op.create_index("ix_case_relations_target", "case_relations", ["target_case_id"])

    # RLS policy
    op.execute("ALTER TABLE case_relations ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON case_relations
        USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid)
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON case_relations")
    op.drop_table("case_relations")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON email_templates")
    op.drop_table("email_templates")
