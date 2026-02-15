"""Audit log model — append-only, INSERT only.

Principle P2: Event-Sourced Timeline — no UPDATE, no DELETE.
PostgreSQL GRANT enforces INSERT-only at the database level.
Protected by RLS via tenant_id.
"""
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base, TenantMixin


class AuditLog(TenantMixin, Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="BIGSERIAL — append-only sequence",
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Actor (NULL for system actions)",
    )
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="e.g. CREATE, UPDATE, DELETE, LOGIN, EXPORT",
    )
    resource_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="e.g. case, contact, invoice, user",
    )
    resource_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="ID of the affected resource",
    )
    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        comment="Additional context: IP, user-agent, old/new values",
    )
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=text("now()"),
    )

    def __repr__(self) -> str:
        return f"<AuditLog {self.id} {self.action} {self.resource_type}>"
