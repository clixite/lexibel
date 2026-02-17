"""BRAIN memory model for vector storage metadata."""
import uuid

from sqlalchemy import Float, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base, TenantMixin, TimestampMixin


class BrainMemory(TenantMixin, TimestampMixin, Base):
    """BRAIN memory for RAG (metadata, actual vectors in Qdrant)."""

    __tablename__ = "brain_memories"

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
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    memory_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="'fact', 'preference', 'pattern', 'learning'",
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    qdrant_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        comment="ID in Qdrant",
    )
    source_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)),
        nullable=False,
        server_default=text("'{}'::uuid[]"),
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="0.0-1.0",
    )

    # Relationships
    # case: Mapped["Case"] = relationship("Case")

    def __repr__(self) -> str:
        return f"<BrainMemory {self.memory_type} {self.qdrant_id[:20]}>"
