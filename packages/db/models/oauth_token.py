"""OAuth token model for Google/Microsoft integrations."""

import uuid
from sqlalchemy import Column, String, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from packages.db.base import Base, TenantMixin, TimestampMixin


class OAuthToken(Base, TenantMixin, TimestampMixin):
    """Encrypted OAuth tokens for third-party integrations."""

    __tablename__ = "oauth_tokens"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Provider: 'google', 'microsoft', 'ringover', 'plaud'
    provider = Column(String(50), nullable=False, index=True)

    # Encrypted tokens (use Fernet encryption in service layer)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)

    token_type = Column(String(50), nullable=False, default="Bearer")
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Space-separated scopes
    scope = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", back_populates="oauth_tokens")

    __table_args__ = (
        # Unique constraint: one token per user per provider
        {"unique_constraint": ("user_id", "provider")},
    )
