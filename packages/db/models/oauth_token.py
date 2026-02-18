"""OAuth token model for Google/Microsoft integrations."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base, TenantMixin, TimestampMixin


class OAuthToken(TenantMixin, TimestampMixin, Base):
    """Encrypted OAuth tokens for third-party integrations."""

    __tablename__ = "oauth_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Provider: 'google', 'microsoft', 'ringover', 'plaud'
    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="OAuth provider identifier",
    )

    # Encrypted tokens (use Fernet encryption in service layer)
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)

    token_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default=text("'Bearer'"),
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Space-separated scopes
    scope: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Token status: 'active', 'expired', 'revoked'
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'active'"),
        index=True,
        comment="Token status: active, expired, revoked",
    )

    # Email address associated with this OAuth token
    email_address: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Email address associated with this OAuth token",
    )

    __table_args__ = (
        # Unique constraint: one token per user per provider
        UniqueConstraint("user_id", "provider", name="uq_oauth_token_user_provider"),
    )
