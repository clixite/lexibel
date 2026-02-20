"""SENTINEL entity model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base, TenantMixin, TimestampMixin


class SentinelEntity(TenantMixin, TimestampMixin, Base):
    """SENTINEL entity enrichment (BCE, LinkedIn) linked to Neo4j."""

    __tablename__ = "sentinel_entities"

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
    entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="'person', 'company'",
    )
    lexibel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Link to Contact or Case",
    )
    neo4j_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        comment="Node ID in Neo4j",
    )
    enrichment_data: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        comment="BCE data, LinkedIn, etc.",
    )
    last_synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    # Relationships
    # No direct relationship to Contact/Case due to polymorphic nature

    def __repr__(self) -> str:
        return f"<SentinelEntity {self.entity_type} neo4j={self.neo4j_id}>"
