"""LXB-017: Create cloud_documents, cloud_sync_jobs, document_case_links tables.

Also adds display_name, avatar_url, last_sync_at, sync_status, sync_error
columns to oauth_tokens.

This implements the Document & Email Integration Engine for Google Workspace
and Microsoft 365 integration (GDPR-compliant: metadata only, no file copies).

Revision ID: 017
Revises: 016
Create Date: 2026-02-18
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


revision: str = "017"
down_revision: Union[str, None] = "016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Add columns to oauth_tokens ────────────────────────────────────
    op.add_column(
        "oauth_tokens",
        sa.Column("display_name", sa.String(255), nullable=True),
    )
    op.add_column(
        "oauth_tokens",
        sa.Column("avatar_url", sa.String(500), nullable=True),
    )
    op.add_column(
        "oauth_tokens",
        sa.Column(
            "last_sync_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Last successful sync timestamp",
        ),
    )
    op.add_column(
        "oauth_tokens",
        sa.Column(
            "sync_status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'idle'"),
            comment="idle | syncing | error",
        ),
    )
    op.add_column(
        "oauth_tokens",
        sa.Column("sync_error", sa.Text, nullable=True),
    )

    # -- 2. Create cloud_documents
    op.create_table(
        "cloud_documents",
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
            "oauth_token_id",
            UUID(as_uuid=True),
            sa.ForeignKey("oauth_tokens.id", ondelete="CASCADE"),
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
        sa.Column("provider", sa.String(20), nullable=False, index=True),
        sa.Column("external_id", sa.String(500), nullable=False),
        sa.Column("external_parent_id", sa.String(500), nullable=True),
        sa.Column("name", sa.String(1000), nullable=False),
        sa.Column("mime_type", sa.String(255), nullable=True),
        sa.Column("size_bytes", sa.BigInteger, nullable=True),
        sa.Column("web_url", sa.String(2000), nullable=True),
        sa.Column("edit_url", sa.String(2000), nullable=True),
        sa.Column("thumbnail_url", sa.String(2000), nullable=True),
        sa.Column(
            "is_folder",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("path", sa.Text, nullable=True),
        sa.Column("last_modified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_modified_by", sa.String(255), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column(
            "is_indexed",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "index_status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column(
            "cached_locally",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("cache_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "metadata_json",
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
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "provider",
            "external_id",
            name="uq_cloud_documents_tenant_provider_external",
        ),
    )

    op.execute("ALTER TABLE cloud_documents ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON cloud_documents
        USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid)
        """
    )
    op.create_index(
        "idx_cloud_documents_tenant_provider",
        "cloud_documents",
        ["tenant_id", "provider"],
    )
    op.create_index(
        "idx_cloud_documents_tenant_case",
        "cloud_documents",
        ["tenant_id", "case_id"],
    )
    op.create_index(
        "idx_cloud_documents_tenant_indexed",
        "cloud_documents",
        ["tenant_id", "is_indexed"],
    )

    # -- 3. Create cloud_sync_jobs
    op.create_table(
        "cloud_sync_jobs",
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
            "oauth_token_id",
            UUID(as_uuid=True),
            sa.ForeignKey("oauth_tokens.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("job_type", sa.String(50), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'pending'"),
            index=True,
        ),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("scope", sa.Text, nullable=True),
        sa.Column(
            "total_items",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "processed_items",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "error_count",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "metadata_json",
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
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.execute("ALTER TABLE cloud_sync_jobs ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON cloud_sync_jobs
        USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid)
        """
    )

    op.create_index(
        "idx_cloud_sync_jobs_tenant_status",
        "cloud_sync_jobs",
        ["tenant_id", "status"],
    )

    # -- 4. Create document_case_links
    op.create_table(
        "document_case_links",
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
            "cloud_document_id",
            UUID(as_uuid=True),
            sa.ForeignKey("cloud_documents.id", ondelete="CASCADE"),
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
            "linked_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "link_type",
            sa.String(50),
            nullable=False,
            server_default=sa.text("'reference'"),
        ),
        sa.Column("notes", sa.Text, nullable=True),
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
        sa.UniqueConstraint(
            "cloud_document_id",
            "case_id",
            name="uq_document_case_links_doc_case",
        ),
    )

    op.execute("ALTER TABLE document_case_links ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON document_case_links
        USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid)
        """
    )

    op.create_index(
        "idx_document_case_links_tenant_case",
        "document_case_links",
        ["tenant_id", "case_id"],
    )


def downgrade() -> None:
    op.drop_table("document_case_links")
    op.drop_table("cloud_sync_jobs")
    op.drop_table("cloud_documents")
    op.drop_column("oauth_tokens", "sync_error")
    op.drop_column("oauth_tokens", "sync_status")
    op.drop_column("oauth_tokens", "last_sync_at")
    op.drop_column("oauth_tokens", "avatar_url")
    op.drop_column("oauth_tokens", "display_name")
