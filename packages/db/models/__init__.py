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
from packages.db.models.migration_job import MigrationJob
from packages.db.models.migration_mapping import MigrationMapping
from packages.db.models.chunk import Chunk
from packages.db.models.oauth_token import OAuthToken
from packages.db.models.calendar_event import CalendarEvent
from packages.db.models.email_thread import EmailThread
from packages.db.models.email_message import EmailMessage
from packages.db.models.call_record import CallRecord
from packages.db.models.transcription import Transcription
from packages.db.models.transcription_segment import TranscriptionSegment

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
    "MigrationJob",
    "MigrationMapping",
    "Chunk",
    "OAuthToken",
    "CalendarEvent",
    "EmailThread",
    "EmailMessage",
    "CallRecord",
    "Transcription",
    "TranscriptionSegment",
]
