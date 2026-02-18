"""LXB-016: Create ai_audit_logs table for AI Act EU compliance.

Tracks every LLM API call with data sensitivity classification,
anonymization status, and human validation flag.

Revision ID: 016
Revises: 015
Create Date: 2026-02-18
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_audit_logs",
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
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
            comment="User who initiated the LLM request",
        ),
        sa.Column(
            "provider",
            sa.String(50),
            nullable=False,
            index=True,
            comment="anthropic, openai, mistral, deepseek, glm, kimi",
        ),
        sa.Column(
            "model",
            sa.String(100),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "data_sensitivity",
            sa.String(20),
            nullable=False,
            index=True,
            comment="public, semi, sensitive, critical",
        ),
        sa.Column(
            "was_anonymized",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "anonymization_method",
            sa.String(50),
            nullable=True,
        ),
        sa.Column(
            "prompt_hash",
            sa.String(64),
            nullable=False,
            comment="SHA-256 of prompt (never the content)",
        ),
        sa.Column(
            "response_hash",
            sa.String(64),
            nullable=True,
        ),
        sa.Column("token_count_input", sa.Integer, nullable=True),
        sa.Column("token_count_output", sa.Integer, nullable=True),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column("cost_estimate_eur", sa.Numeric(10, 6), nullable=True),
        sa.Column(
            "purpose",
            sa.String(100),
            nullable=False,
            index=True,
            comment="case_analysis, document_draft, legal_research, etc.",
        ),
        sa.Column(
            "human_validated",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
            comment="AI Act Art. 14 — human-in-the-loop",
        ),
        sa.Column(
            "human_validator_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("human_validated_at", sa.DateTime, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column(
            "metadata",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # RLS
    op.execute("ALTER TABLE ai_audit_logs ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON ai_audit_logs
        USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid)
        """
    )

    # Composite indexes for common queries
    op.create_index(
        "idx_ai_audit_logs_tenant_created",
        "ai_audit_logs",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "idx_ai_audit_logs_tenant_provider",
        "ai_audit_logs",
        ["tenant_id", "provider"],
    )
    op.create_index(
        "idx_ai_audit_logs_tenant_sensitivity",
        "ai_audit_logs",
        ["tenant_id", "data_sensitivity"],
    )
    op.create_index(
        "idx_ai_audit_logs_tenant_purpose",
        "ai_audit_logs",
        ["tenant_id", "purpose"],
    )
    op.create_index(
        "idx_ai_audit_logs_human_validated",
        "ai_audit_logs",
        ["human_validated"],
    )

    # INSERT-only policy (append-only audit trail)
    op.execute(
        """
        COMMENT ON TABLE ai_audit_logs IS
        'AI Act EU (2024/1689) compliance audit trail. Append-only.'
        """
    )


def downgrade() -> None:
    op.drop_table("ai_audit_logs")
