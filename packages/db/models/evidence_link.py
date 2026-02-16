"""EvidenceLink model — file references attached to interaction events.

Each evidence link points to a file in MinIO/S3, identified by SHA-256 hash.
Protected by RLS via tenant_id.
"""

import uuid

from sqlalchemy import BigInteger, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base, TenantMixin, TimestampMixin


class EvidenceLink(TenantMixin, TimestampMixin, Base):
    __tablename__ = "evidence_links"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    interaction_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interaction_events.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    file_path: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
        comment="S3/MinIO object path: /{tenant_id}/{case_id}/{filename}",
    )
    file_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Original file name",
    )
    mime_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    file_size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    sha256_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="SHA-256 hex digest of file contents",
    )

    def __repr__(self) -> str:
        return f"<EvidenceLink {self.file_name} ({self.mime_type})>"
