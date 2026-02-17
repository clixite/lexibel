"""Chunk model for RAG/vector storage."""

import uuid
from sqlalchemy import Column, String, Text, ForeignKey, Index, LargeBinary
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from packages.db.base import Base, TenantMixin, TimestampMixin


class Chunk(Base, TenantMixin, TimestampMixin):
    """Document chunk for semantic search and RAG."""

    __tablename__ = "chunks"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
    )
    case_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("evidence_links.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    content = Column(Text, nullable=False)
    # Embedding stored as binary data
    embedding = Column(LargeBinary, nullable=True)

    # Metadata: page_number, chunk_index, source_type, etc.
    metadata_ = Column(
        "metadata", JSONB, nullable=False, default=dict, server_default="{}"
    )

    # Relationships
    case = relationship("Case", back_populates="chunks")
    document = relationship("EvidenceLink", back_populates="chunks")

    __table_args__ = (Index("idx_chunks_tenant_case", "tenant_id", "case_id"),)
