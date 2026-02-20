"""LXB-011: Create brain_actions, brain_insights, and brain_memories tables.

Revision ID: 011
Revises: 010
Create Date: 2026-02-17
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── brain_actions ──
    op.create_table(
        "brain_actions",
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
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "action_type",
            sa.String(50),
            nullable=False,
            index=True,
            comment="'alert', 'draft', 'suggestion', 'auto_send'",
        ),
        sa.Column(
            "priority",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'normal'"),
            index=True,
            comment="'critical', 'urgent', 'normal'",
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'pending'"),
            index=True,
            comment="'pending', 'approved', 'rejected', 'executed'",
        ),
        sa.Column(
            "confidence_score",
            sa.Float,
            nullable=False,
            comment="0.0-1.0",
        ),
        sa.Column(
            "trigger_source",
            sa.String(50),
            nullable=False,
            comment="'call', 'email', 'document', 'deadline'",
        ),
        sa.Column(
            "trigger_id",
            UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "action_data",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "generated_content",
            sa.Text,
            nullable=True,
        ),
        sa.Column(
            "executed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "reviewed_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column(
            "feedback",
            sa.Text,
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
    )

    # RLS for brain_actions
    op.execute("ALTER TABLE brain_actions ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON brain_actions
        USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid)
        """
    )

    # Indexes for brain_actions
    op.create_index(
        "idx_brain_actions_tenant_case", "brain_actions", ["tenant_id", "case_id"]
    )
    op.create_index("idx_brain_actions_status", "brain_actions", ["status"])

    # ── brain_insights ──
    op.create_table(
        "brain_insights",
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
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "insight_type",
            sa.String(50),
            nullable=False,
            index=True,
            comment="'risk', 'opportunity', 'contradiction', 'deadline'",
        ),
        sa.Column(
            "severity",
            sa.String(20),
            nullable=False,
            index=True,
            comment="'low', 'medium', 'high', 'critical'",
        ),
        sa.Column(
            "title",
            sa.String(200),
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.Text,
            nullable=False,
        ),
        sa.Column(
            "evidence_ids",
            ARRAY(UUID(as_uuid=True)),
            nullable=False,
            server_default=sa.text("'{}'::uuid[]"),
        ),
        sa.Column(
            "suggested_actions",
            ARRAY(sa.String),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column(
            "dismissed",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "dismissed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "dismissed_by",
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
    )

    # RLS for brain_insights
    op.execute("ALTER TABLE brain_insights ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON brain_insights
        USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid)
        """
    )

    # Indexes for brain_insights
    op.create_index(
        "idx_brain_insights_tenant_case", "brain_insights", ["tenant_id", "case_id"]
    )
    op.create_index("idx_brain_insights_severity", "brain_insights", ["severity"])

    # ── brain_memories ──
    op.create_table(
        "brain_memories",
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
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "memory_type",
            sa.String(50),
            nullable=False,
            index=True,
            comment="'fact', 'preference', 'pattern', 'learning'",
        ),
        sa.Column(
            "content",
            sa.Text,
            nullable=False,
        ),
        sa.Column(
            "qdrant_id",
            sa.String(100),
            nullable=False,
            unique=True,
            comment="ID in Qdrant",
        ),
        sa.Column(
            "source_ids",
            ARRAY(UUID(as_uuid=True)),
            nullable=False,
            server_default=sa.text("'{}'::uuid[]"),
        ),
        sa.Column(
            "confidence",
            sa.Float,
            nullable=False,
            comment="0.0-1.0",
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
    )

    # RLS for brain_memories
    op.execute("ALTER TABLE brain_memories ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON brain_memories
        USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid)
        """
    )

    # Indexes for brain_memories
    op.create_index(
        "idx_brain_memories_tenant_case", "brain_memories", ["tenant_id", "case_id"]
    )
    op.create_index(
        "idx_brain_memories_qdrant_id", "brain_memories", ["qdrant_id"], unique=True
    )


def downgrade() -> None:
    op.drop_table("brain_memories")
    op.drop_table("brain_insights")
    op.drop_table("brain_actions")
