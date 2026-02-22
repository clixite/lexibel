"""Email template model — reusable templates for Belgian legal correspondence.

Templates are tenant-scoped and support variable interpolation
for case/contact fields: {case.reference}, {contact.full_name}, etc.
"""

import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base, TenantMixin, TimestampMixin


class EmailTemplate(TenantMixin, TimestampMixin, Base):
    """Reusable email template for legal correspondence."""

    __tablename__ = "email_templates"

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
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Template display name",
    )
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="mise_en_demeure | convocation | conclusions | accusé_reception | courrier_adverse | demande_pieces | relance | general",
    )
    subject_template: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Subject with {variable} placeholders",
    )
    body_template: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="HTML body with {variable} placeholders",
    )
    language: Mapped[str] = mapped_column(
        String(5),
        nullable=False,
        server_default=text("'fr'"),
        comment="fr | nl | de",
    )
    matter_types: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
        comment="Applicable matter types (empty = all)",
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
        comment="System-provided template (not editable by tenant)",
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<EmailTemplate {self.name} [{self.category}]>"
