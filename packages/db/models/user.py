"""User model — lawyers, secretaries, admins.

Protected by RLS via tenant_id.
"""

import enum
import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base, TenantMixin, TimestampMixin


class UserRole(str, enum.Enum):
    """RBAC roles as defined in the LexiBel spec."""

    PARTNER = "partner"
    ASSOCIATE = "associate"
    JUNIOR = "junior"
    SECRETARY = "secretary"
    ACCOUNTANT = "accountant"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class User(TenantMixin, TimestampMixin, Base):
    __tablename__ = "users"

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
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Unique per tenant",
    )
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'junior'"),
        comment="RBAC role: partner|associate|junior|secretary|accountant|admin|super_admin",
    )
    auth_provider: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'local'"),
        comment="local | oidc | azure_ad",
    )
    hashed_password: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="bcrypt hash — NULL for OIDC/Azure AD users",
    )
    mfa_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    mfa_secret: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        comment="TOTP secret for MFA (base32-encoded)",
    )
    hourly_rate_cents: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Hourly rate in euro cents for billing",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"
