"""Case model — dossiers / legal matters.

Protected by RLS via tenant_id. Each case has a unique reference
per tenant and is assigned to a responsible user.
"""
import uuid
from datetime import date, datetime

from sqlalchemy import Date, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base, TenantMixin, TimestampMixin


class Case(TenantMixin, TimestampMixin, Base):
    __tablename__ = "cases"

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
    reference: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Unique case reference per tenant (e.g. 2026/001)",
    )
    court_reference: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Court docket number",
    )
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    matter_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="e.g. civil, penal, social, fiscal, commercial, family",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default=text("'open'"),
        comment="open | in_progress | pending | closed | archived",
    )
    jurisdiction: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Court or jurisdiction name",
    )
    responsible_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Primary responsible lawyer",
    )
    opened_at: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        server_default=text("CURRENT_DATE"),
    )
    closed_at: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        comment="Flexible metadata: tags, custom fields, team members",
    )

    def __repr__(self) -> str:
        return f"<Case {self.reference} {self.title[:30]}>"
