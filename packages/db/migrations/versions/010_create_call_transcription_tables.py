"""LXB-010: Create call_records, transcriptions, and transcription_segments tables.

Revision ID: 010
Revises: 009
Create Date: 2026-02-17
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── transcriptions ── (create first because call_records references it)
    op.create_table(
        "transcriptions",
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
        sa.Column("source", sa.String(50), nullable=False, index=True),
        sa.Column("audio_url", sa.String(500), nullable=True),
        sa.Column("audio_duration_seconds", sa.Integer, nullable=True),
        sa.Column("language", sa.String(10), nullable=True),
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            server_default=sa.text("'pending'"),
            index=True,
        ),
        sa.Column("full_text", sa.Text, nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("sentiment_score", sa.Numeric(3, 2), nullable=True),
        sa.Column("sentiment_label", sa.String(50), nullable=True),
        sa.Column(
            "extracted_tasks", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
        sa.Column(
            "metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at", sa.DateTime, nullable=False, server_default=sa.text("now()")
        ),
    )

    # RLS for transcriptions
    op.execute("ALTER TABLE transcriptions ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON transcriptions
        USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid)
        """
    )

    # Indexes
    op.create_index(
        "idx_transcriptions_tenant_case", "transcriptions", ["tenant_id", "case_id"]
    )

    # ── call_records ──
    op.create_table(
        "call_records",
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
        sa.Column(
            "contact_id",
            UUID(as_uuid=True),
            sa.ForeignKey("contacts.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("external_id", sa.String(255), nullable=False, index=True, unique=True),
        sa.Column("direction", sa.String(50), nullable=False, index=True),
        sa.Column("caller_number", sa.String(50), nullable=True),
        sa.Column("callee_number", sa.String(50), nullable=True),
        sa.Column("duration_seconds", sa.Integer, nullable=True),
        sa.Column("call_type", sa.String(50), nullable=True, index=True),
        sa.Column("recording_url", sa.String(500), nullable=True),
        sa.Column(
            "transcription_id",
            UUID(as_uuid=True),
            sa.ForeignKey("transcriptions.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at", sa.DateTime, nullable=False, server_default=sa.text("now()")
        ),
    )

    # RLS for call_records
    op.execute("ALTER TABLE call_records ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON call_records
        USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid)
        """
    )

    # Indexes
    op.create_index(
        "idx_call_records_tenant_case", "call_records", ["tenant_id", "case_id"]
    )

    # ── transcription_segments ──
    op.create_table(
        "transcription_segments",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "transcription_id",
            UUID(as_uuid=True),
            sa.ForeignKey("transcriptions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("segment_index", sa.Integer, nullable=False),
        sa.Column("speaker", sa.String(100), nullable=True),
        sa.Column("start_time", sa.Numeric(10, 3), nullable=False),
        sa.Column("end_time", sa.Numeric(10, 3), nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("confidence", sa.Numeric(3, 2), nullable=True),
        sa.Column(
            "created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at", sa.DateTime, nullable=False, server_default=sa.text("now()")
        ),
    )

    # Indexes
    op.create_index(
        "idx_transcription_segments_transcription_index",
        "transcription_segments",
        ["transcription_id", "segment_index"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("transcription_segments")
    op.drop_table("call_records")
    op.drop_table("transcriptions")
