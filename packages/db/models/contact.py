"""Contact model — natural and legal persons.

Protected by RLS via tenant_id. Contacts can be linked to cases
via the case_contacts junction table.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base, TenantMixin, TimestampMixin


class ContactType(str, enum.Enum):
    NATURAL = "natural"
    LEGAL = "legal"


class Contact(TenantMixin, TimestampMixin, Base):
    __tablename__ = "contacts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    type: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="natural | legal",
    )
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    bce_number: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Belgian BCE/KBO enterprise number (legal persons)",
    )
    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    phone_e164: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Phone in E.164 format (e.g. +32470123456)",
    )
    address: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Structured address: street, city, zip, country",
    )
    language: Mapped[str] = mapped_column(
        String(5),
        nullable=False,
        server_default=text("'fr'"),
        comment="Preferred language: fr, nl, de, en",
    )

    def __repr__(self) -> str:
        return f"<Contact {self.full_name}>"
