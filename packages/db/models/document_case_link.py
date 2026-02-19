"""Document-Case link model — links cloud documents to legal cases."""

import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base, TenantMixin, TimestampMixin


class DocumentCaseLink(TenantMixin, TimestampMixin, Base):
    """Links a cloud document to a legal case (dossier).

    One document can be linked to multiple cases, and one case
    can have multiple documents.
    """

    __tablename__ = "document_case_links"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    cloud_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cloud_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    linked_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    link_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default=text("'reference'"),
        comment="reference | evidence | contract | correspondence | other",
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "cloud_document_id",
            "case_id",
            name="uq_document_case_links_doc_case",
        ),
    )

    def __repr__(self) -> str:
        return f"<DocumentCaseLink doc={self.cloud_document_id} case={self.case_id}>"
