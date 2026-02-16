"""Case-Contact junction table.

Links contacts to cases with a role (client, adverse, witness, third_party).
Protected by RLS via tenant_id. Composite primary key on (case_id, contact_id).
"""

import enum
import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base, TenantMixin


class CaseContactRole(str, enum.Enum):
    CLIENT = "client"
    ADVERSE = "adverse"
    WITNESS = "witness"
    THIRD_PARTY = "third_party"


class CaseContact(TenantMixin, Base):
    __tablename__ = "case_contacts"

    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        primary_key=True,
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="client | adverse | witness | third_party",
    )

    def __repr__(self) -> str:
        return f"<CaseContact case={self.case_id} contact={self.contact_id} role={self.role}>"
