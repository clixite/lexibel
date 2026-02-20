"""SENTINEL conflict model."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base, TenantMixin, TimestampMixin


class SentinelConflict(TenantMixin, TimestampMixin, Base):
    """SENTINEL conflict detection via Neo4j graph."""

    __tablename__ = "sentinel_conflicts"

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
    trigger_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Contact or Case who triggered conflict detection",
    )
    trigger_entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="'contact', 'case'",
    )
    conflict_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="'direct_adversary', 'indirect_ownership', 'director_overlap'",
    )
    severity_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        comment="0-100",
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    conflicting_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    conflicting_entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="'contact', 'case'",
    )
    conflicting_case_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=True,
    )
    graph_path: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        comment="Path in Neo4j graph",
    )
    auto_resolved: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    resolution: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        comment="'refused', 'waiver_obtained', 'false_positive'",
    )
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    # conflicting_case: Mapped["Case"] = relationship("Case")
    # resolver: Mapped["User"] = relationship("User", foreign_keys=[resolved_by])

    def __repr__(self) -> str:
        return f"<SentinelConflict {self.conflict_type} severity={self.severity_score}>"
