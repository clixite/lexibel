"""Tenant model — cabinets / law firms.

No RLS on this table: access is restricted to super_admin via application logic.
"""

import uuid

from sqlalchemy import String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base, TimestampMixin


class Tenant(TimestampMixin, Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Official cabinet name",
    )
    slug: Mapped[str] = mapped_column(
        String(63),
        nullable=False,
        unique=True,
        index=True,
        comment="URL-safe identifier",
    )
    plan: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'solo'"),
        comment="Subscription plan: solo | team | enterprise",
    )
    locale: Mapped[str] = mapped_column(
        String(5),
        nullable=False,
        server_default=text("'fr-BE'"),
        comment="Default locale (fr-BE, nl-BE, de-BE)",
    )
    config: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        comment="Tenant config: BYOK keys, thresholds, feature flags",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'active'"),
        comment="active | suspended | archived",
    )

    def __repr__(self) -> str:
        return f"<Tenant {self.slug}>"
