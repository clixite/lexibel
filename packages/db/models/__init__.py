"""SQLAlchemy models — import all models here so Alembic can discover them."""
from packages.db.base import Base
from packages.db.models.tenant import Tenant
from packages.db.models.user import User
from packages.db.models.audit_log import AuditLog
from packages.db.models.case import Case
from packages.db.models.contact import Contact
from packages.db.models.case_contact import CaseContact
from packages.db.models.interaction_event import InteractionEvent
from packages.db.models.evidence_link import EvidenceLink
from packages.db.models.inbox_item import InboxItem
from packages.db.models.time_entry import TimeEntry
from packages.db.models.invoice import Invoice
from packages.db.models.invoice_line import InvoiceLine
from packages.db.models.third_party_entry import ThirdPartyEntry

__all__ = [
    "Base",
    "Tenant",
    "User",
    "AuditLog",
    "Case",
    "Contact",
    "CaseContact",
    "InteractionEvent",
    "EvidenceLink",
    "InboxItem",
    "TimeEntry",
    "Invoice",
    "InvoiceLine",
    "ThirdPartyEntry",
]
