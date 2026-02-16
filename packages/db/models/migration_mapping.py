"""MigrationMapping model — field mapping rules for data import.

Defines how source fields map to LexiBel target tables/fields.
Protected by RLS via tenant_id.
"""
import uuid

from sqlalchemy import ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base, TenantMixin, TimestampMixin


class MigrationMapping(TenantMixin, TimestampMixin, Base):
    __tablename__ = "migration_mappings"

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
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("migration_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_field: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    target_table: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    target_field: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    transform_rule: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Optional transformation: {type: 'date_format', pattern: 'DD/MM/YYYY'}",
    )

    def __repr__(self) -> str:
        return f"<MigrationMapping {self.source_field} -> {self.target_table}.{self.target_field}>"
