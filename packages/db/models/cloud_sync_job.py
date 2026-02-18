"""Cloud sync job model — tracks document synchronization jobs."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base, TenantMixin, TimestampMixin


class CloudSyncJob(TenantMixin, TimestampMixin, Base):
    """Tracks a document synchronization job (full_sync, incremental_sync, folder_sync)."""

    __tablename__ = "cloud_sync_jobs"

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
    job_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="full_sync | incremental_sync | folder_sync",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'pending'"),
        index=True,
        comment="pending | running | completed | failed",
    )
    provider: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="google_drive | onedrive | sharepoint",
    )
    scope: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Folder ID or 'all'",
    )
    total_items: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )
    processed_items: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )
    error_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    metadata_json: Mapped[dict] = mapped_column(
        "metadata_json",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    def __repr__(self) -> str:
        return f"<CloudSyncJob {self.job_type} {self.status}>"
