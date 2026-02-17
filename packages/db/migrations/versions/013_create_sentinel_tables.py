"""LXB-013: Create sentinel_conflicts and sentinel_entities tables.

Revision ID: 013
Revises: 012
Create Date: 2026-02-17
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── sentinel_entities ── (create first because sentinel_conflicts may reference it indirectly)
    op.create_table(
        "sentinel_entities",
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
            "entity_type",
            sa.String(50),
            nullable=False,
            index=True,
            comment="'person', 'company'",
        ),
        sa.Column(
            "lexibel_id",
            UUID(as_uuid=True),
            nullable=False,
            index=True,
            comment="Link to Contact or Case",
        ),
        sa.Column(
            "neo4j_id",
            sa.String(100),
            nullable=False,
            unique=True,
            comment="Node ID in Neo4j",
        ),
        sa.Column(
            "enrichment_data",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment="BCE data, LinkedIn, etc.",
        ),
        sa.Column(
            "last_synced_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
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

    # RLS for sentinel_entities
    op.execute("ALTER TABLE sentinel_entities ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON sentinel_entities
        USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid)
        """
    )

    # Indexes for sentinel_entities
    op.create_index(
        "idx_sentinel_entities_tenant_lexibel",
        "sentinel_entities",
        ["tenant_id", "lexibel_id"],
    )
    op.create_index(
        "idx_sentinel_entities_neo4j_id",
        "sentinel_entities",
        ["neo4j_id"],
        unique=True,
    )

    # ── sentinel_conflicts ──
    op.create_table(
        "sentinel_conflicts",
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
            "trigger_entity_id",
            UUID(as_uuid=True),
            nullable=False,
            index=True,
            comment="Contact or Case who triggered conflict detection",
        ),
        sa.Column(
            "trigger_entity_type",
            sa.String(50),
            nullable=False,
            index=True,
            comment="'contact', 'case'",
        ),
        sa.Column(
            "conflict_type",
            sa.String(100),
            nullable=False,
            index=True,
            comment="'direct_adversary', 'indirect_ownership', 'director_overlap'",
        ),
        sa.Column(
            "severity_score",
            sa.Integer,
            nullable=False,
            index=True,
            comment="0-100",
        ),
        sa.Column(
            "description",
            sa.Text,
            nullable=False,
        ),
        sa.Column(
            "conflicting_entity_id",
            UUID(as_uuid=True),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "conflicting_entity_type",
            sa.String(50),
            nullable=False,
            comment="'contact', 'case'",
        ),
        sa.Column(
            "conflicting_case_id",
            UUID(as_uuid=True),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "graph_path",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment="Path in Neo4j graph",
        ),
        sa.Column(
            "auto_resolved",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "resolution",
            sa.String(50),
            nullable=True,
            index=True,
            comment="'refused', 'waiver_obtained', 'false_positive'",
        ),
        sa.Column(
            "resolved_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column(
            "resolved_at",
            sa.DateTime(timezone=True),
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

    # RLS for sentinel_conflicts
    op.execute("ALTER TABLE sentinel_conflicts ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON sentinel_conflicts
        USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid)
        """
    )

    # Indexes for sentinel_conflicts
    op.create_index(
        "idx_sentinel_conflicts_tenant_trigger",
        "sentinel_conflicts",
        ["tenant_id", "trigger_entity_id"],
    )
    op.create_index(
        "idx_sentinel_conflicts_severity",
        "sentinel_conflicts",
        ["severity_score"],
    )
    op.create_index(
        "idx_sentinel_conflicts_resolution",
        "sentinel_conflicts",
        ["resolution"],
    )


def downgrade() -> None:
    op.drop_table("sentinel_conflicts")
    op.drop_table("sentinel_entities")
