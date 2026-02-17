"""LXB-014: Create timeline_events and timeline_documents tables.

Revision ID: 014
Revises: 013
Create Date: 2026-02-17
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, UUID

revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── timeline_events ──
    op.create_table(
        "timeline_events",
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
            "event_date",
            sa.Date,
            nullable=False,
            index=True,
        ),
        sa.Column(
            "event_time",
            sa.Time,
            nullable=True,
        ),
        sa.Column(
            "category",
            sa.String(50),
            nullable=False,
            index=True,
            comment="'meeting', 'call', 'email', 'signature'",
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
            "actors",
            ARRAY(sa.String),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
            comment="List of person/company names",
        ),
        sa.Column(
            "location",
            sa.String(200),
            nullable=True,
        ),
        sa.Column(
            "source_type",
            sa.String(50),
            nullable=False,
            index=True,
            comment="'email', 'call', 'document', 'manual'",
        ),
        sa.Column(
            "source_id",
            UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "source_excerpt",
            sa.Text,
            nullable=False,
            comment="Original text",
        ),
        sa.Column(
            "confidence_score",
            sa.Float,
            nullable=False,
            comment="0.0-1.0",
        ),
        sa.Column(
            "is_validated",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "is_key_event",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
            comment="Highlighted in timeline",
        ),
        sa.Column(
            "evidence_links",
            ARRAY(UUID(as_uuid=True)),
            nullable=False,
            server_default=sa.text("'{}'::uuid[]"),
            comment="Links to documents",
        ),
        sa.Column(
            "created_by",
            sa.String(50),
            nullable=False,
            comment="'ai' or user_id",
        ),
        sa.Column(
            "validated_by",
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

    # RLS for timeline_events
    op.execute("ALTER TABLE timeline_events ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON timeline_events
        USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid)
        """
    )

    # Indexes for timeline_events
    op.create_index(
        "idx_timeline_events_tenant_case",
        "timeline_events",
        ["tenant_id", "case_id"],
    )
    op.create_index(
        "idx_timeline_events_event_date",
        "timeline_events",
        ["event_date"],
    )
    op.create_index(
        "idx_timeline_events_category",
        "timeline_events",
        ["category"],
    )

    # ── timeline_documents ──
    op.create_table(
        "timeline_documents",
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
            "timeline_id",
            UUID(as_uuid=True),
            nullable=False,
            index=True,
            comment="References a specific timeline version",
        ),
        sa.Column(
            "format",
            sa.String(20),
            nullable=False,
            comment="'docx', 'pdf', 'html'",
        ),
        sa.Column(
            "file_path",
            sa.String(500),
            nullable=False,
        ),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "generated_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "events_count",
            sa.Integer,
            nullable=False,
        ),
        sa.Column(
            "date_range_start",
            sa.Date,
            nullable=False,
        ),
        sa.Column(
            "date_range_end",
            sa.Date,
            nullable=False,
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

    # RLS for timeline_documents
    op.execute("ALTER TABLE timeline_documents ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON timeline_documents
        USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid)
        """
    )

    # Indexes for timeline_documents
    op.create_index(
        "idx_timeline_documents_tenant_case",
        "timeline_documents",
        ["tenant_id", "case_id"],
    )
    op.create_index(
        "idx_timeline_documents_timeline_id",
        "timeline_documents",
        ["timeline_id"],
    )


def downgrade() -> None:
    op.drop_table("timeline_documents")
    op.drop_table("timeline_events")
