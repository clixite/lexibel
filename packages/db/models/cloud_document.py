"""Cloud document model — files from Google Drive, OneDrive, SharePoint.

Stores metadata only (GDPR: files remain on provider servers).
Protected by RLS via tenant_id.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base, TenantMixin, TimestampMixin


class CloudDocument(TenantMixin, TimestampMixin, Base):
    """Metadata of a cloud file from Google Drive, OneDrive, or SharePoint.

    Files are NOT copied to our servers (GDPR / secret professionnel Art. 458 C.P. belge).
    Only metadata + optional search index (Qdrant embeddings) are stored.
    """

    __tablename__ = "cloud_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    oauth_token_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("oauth_tokens.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    case_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Linked legal case (nullable — may not be linked yet)",
    )
    # Provider: google_drive, onedrive, sharepoint
    provider: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        comment="google_drive | onedrive | sharepoint",
    )
    # External IDs from provider
    external_id: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="File ID from the provider (Drive file ID, OneDrive item ID, etc.)",
    )
    external_parent_id: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Parent folder ID",
    )
    # File metadata
    name: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )
    mime_type: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    size_bytes: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )
    web_url: Mapped[str | None] = mapped_column(
        String(2000),
        nullable=True,
        comment="URL to view the file in browser",
    )
    edit_url: Mapped[str | None] = mapped_column(
        String(2000),
        nullable=True,
        comment="URL to edit the file in Google Docs / Word Online",
    )
    thumbnail_url: Mapped[str | None] = mapped_column(
        String(2000),
        nullable=True,
    )
    is_folder: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    path: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Full path: /dossier/sous-dossier/fichier.pdf",
    )
    last_modified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_modified_by: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    content_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="MD5/SHA256 to detect changes",
    )
    # Indexation in Qdrant for semantic search
    is_indexed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    index_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'pending'"),
        comment="pending | indexing | indexed | error",
    )
    # Local cache options (GDPR: encrypted, TTL-controlled)
    cached_locally: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    cache_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    metadata_json: Mapped[dict] = mapped_column(
        "metadata_json",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        comment="Flexible metadata from provider (permissions, labels, etc.)",
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "provider",
            "external_id",
            name="uq_cloud_documents_tenant_provider_external",
        ),
    )

    def __repr__(self) -> str:
        return f"<CloudDocument {self.provider}:{self.name}>"
