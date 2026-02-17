"""Chunk model for RAG/vector storage."""
from sqlalchemy import Column, String, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB, VECTOR
from sqlalchemy.orm import relationship
from packages.db.base import Base
from packages.db.mixins import TenantMixin, TimestampMixin


class Chunk(Base, TenantMixin, TimestampMixin):
    """Document chunk for semantic search and RAG."""

    __tablename__ = "chunks"

    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=True, index=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("evidence_links.id", ondelete="CASCADE"), nullable=True, index=True)

    content = Column(Text, nullable=False)
    # OpenAI text-embedding-3-large has 3072 dimensions, but we use 1536 for compatibility
    embedding = Column(VECTOR(1536), nullable=True)

    # Metadata: page_number, chunk_index, source_type, etc.
    metadata = Column(JSONB, nullable=False, default=dict, server_default='{}')

    # Relationships
    case = relationship("Case", back_populates="chunks")
    document = relationship("EvidenceLink", back_populates="chunks")

    __table_args__ = (
        Index('idx_chunks_tenant_case', 'tenant_id', 'case_id'),
        Index('idx_chunks_embedding', 'embedding', postgresql_using='ivfflat'),  # For vector similarity search
    )
