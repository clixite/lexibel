"""Tenant-level configuration stored in DB instead of .env files.

Enables in-app setup wizard so admins never need SSH/.env access.
Sensitive values (API keys, secrets) are encrypted at rest via Fernet (AES-128-CBC).
"""

import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID

from packages.db.base import Base


class TenantSetting(Base):
    __tablename__ = "tenant_settings"
    __table_args__ = (
        UniqueConstraint("tenant_id", "key", name="uq_tenant_setting_key"),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default="gen_random_uuid()",
    )
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Setting identity
    category = Column(String(50), nullable=False, index=True)
    key = Column(String(100), nullable=False)

    # Value (encrypted if sensitive)
    value = Column(Text, nullable=False)
    is_encrypted = Column(Boolean, default=False, server_default="false")

    # Metadata for the wizard UI
    label = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    is_required = Column(Boolean, default=False, server_default="false")

    # Audit
    updated_by = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at = Column(DateTime, nullable=False, server_default="now()")
    updated_at = Column(DateTime, nullable=False, server_default="now()")
