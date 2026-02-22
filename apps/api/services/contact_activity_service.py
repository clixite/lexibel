"""Contact activity service — aggregated timeline across all interactions.

Merges data from:
- InteractionEvent (emails, notes, meetings, status changes)
- CallRecord (phone calls)
- Invoice (billing)
- EmailMessage (direct email messages)
- CaseContact (case involvement)

Provides a unified chronological view of all interactions with a contact.
"""

import uuid
from dataclasses import dataclass, field

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.models.call_record import CallRecord
from packages.db.models.case import Case
from packages.db.models.case_contact import CaseContact
from packages.db.models.contact import Contact
from packages.db.models.email_message import EmailMessage
from packages.db.models.interaction_event import InteractionEvent
from packages.db.models.invoice import Invoice


@dataclass
class ActivityItem:
    """Single activity in the unified timeline."""

    type: str  # email | call | invoice | event | case_link
    title: str
    description: str
    occurred_at: str  # ISO datetime
    metadata: dict = field(default_factory=dict)


@dataclass
class ContactFinancialSummary:
    """Financial overview for a client contact."""

    total_invoiced_cents: int = 0
    total_paid_cents: int = 0
    total_outstanding_cents: int = 0
    total_overdue_cents: int = 0
    invoice_count: int = 0
    last_payment_date: str | None = None


async def get_contact_activity(
    session: AsyncSession,
    contact_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """Get unified activity timeline for a contact.

    Returns (items, total_count).
    """
    contact = await session.execute(select(Contact).where(Contact.id == contact_id))
    contact_obj = contact.scalar_one_or_none()
    if not contact_obj:
        return [], 0

    activities: list[dict] = []

    # 1. Cases linked to this contact
    case_result = await session.execute(
        select(Case, CaseContact.role)
        .join(CaseContact, CaseContact.case_id == Case.id)
        .where(CaseContact.contact_id == contact_id)
        .order_by(Case.created_at.desc())
    )
    for case, role in case_result.all():
        activities.append(
            {
                "type": "case_link",
                "title": f"Dossier {case.reference} — {role}",
                "description": case.title,
                "occurred_at": case.created_at.isoformat(),
                "metadata": {
                    "case_id": str(case.id),
                    "case_reference": case.reference,
                    "role": role,
                    "status": case.status,
                    "matter_type": case.matter_type,
                },
            }
        )

    # 2. Interaction events from cases linked to this contact
    linked_case_ids = select(CaseContact.case_id).where(
        CaseContact.contact_id == contact_id
    )
    event_result = await session.execute(
        select(InteractionEvent)
        .where(InteractionEvent.case_id.in_(linked_case_ids))
        .order_by(InteractionEvent.occurred_at.desc())
        .limit(100)
    )
    for event in event_result.scalars().all():
        activities.append(
            {
                "type": "event",
                "title": event.title,
                "description": event.body[:200] if event.body else "",
                "occurred_at": event.occurred_at.isoformat(),
                "metadata": {
                    "event_type": event.event_type,
                    "source": event.source,
                    "case_id": str(event.case_id) if event.case_id else None,
                },
            }
        )

    # 3. Calls linked to this contact
    call_result = await session.execute(
        select(CallRecord)
        .where(CallRecord.contact_id == contact_id)
        .order_by(CallRecord.started_at.desc())
        .limit(50)
    )
    for call in call_result.scalars().all():
        duration_min = (call.duration_seconds or 0) // 60
        activities.append(
            {
                "type": "call",
                "title": f"Appel {call.direction} — {call.call_type}",
                "description": f"Durée: {duration_min}min"
                if call.duration_seconds
                else "Manqué",
                "occurred_at": call.started_at.isoformat() if call.started_at else "",
                "metadata": {
                    "call_id": str(call.id),
                    "direction": call.direction,
                    "call_type": call.call_type,
                    "duration_seconds": call.duration_seconds,
                    "caller": call.caller_number,
                    "callee": call.callee_number,
                },
            }
        )

    # 4. Emails from/to this contact's email address
    if contact_obj.email:
        email_pattern = f"%{contact_obj.email}%"
        email_result = await session.execute(
            select(EmailMessage)
            .where(
                or_(
                    EmailMessage.from_address.ilike(email_pattern),
                    EmailMessage.to_addresses.op("@>")(f'["{contact_obj.email}"]'),
                )
            )
            .order_by(EmailMessage.received_at.desc())
            .limit(50)
        )
        for email in email_result.scalars().all():
            activities.append(
                {
                    "type": "email",
                    "title": email.subject or "(Sans objet)",
                    "description": (email.body_text or "")[:200],
                    "occurred_at": email.received_at.isoformat()
                    if email.received_at
                    else "",
                    "metadata": {
                        "email_id": str(email.id),
                        "from": email.from_address,
                        "thread_id": str(email.thread_id),
                        "is_read": email.is_read,
                    },
                }
            )

    # 5. Invoices for this contact
    invoice_result = await session.execute(
        select(Invoice)
        .where(Invoice.client_contact_id == contact_id)
        .order_by(Invoice.issue_date.desc())
        .limit(20)
    )
    for inv in invoice_result.scalars().all():
        amount = (inv.total_cents or 0) / 100
        activities.append(
            {
                "type": "invoice",
                "title": f"Facture {inv.invoice_number} — {amount:.2f} EUR",
                "description": f"Statut: {inv.status}",
                "occurred_at": inv.issue_date.isoformat() if inv.issue_date else "",
                "metadata": {
                    "invoice_id": str(inv.id),
                    "invoice_number": inv.invoice_number,
                    "status": inv.status,
                    "total_cents": inv.total_cents,
                    "case_id": str(inv.case_id) if inv.case_id else None,
                },
            }
        )

    # Sort by date descending
    activities.sort(
        key=lambda a: a["occurred_at"] or "",
        reverse=True,
    )

    total = len(activities)
    paginated = activities[offset : offset + limit]

    return paginated, total


async def get_contact_financial_summary(
    session: AsyncSession,
    contact_id: uuid.UUID,
) -> dict:
    """Get financial summary for a contact (invoices, payments, outstanding)."""
    # Total invoiced
    invoiced = await session.execute(
        select(
            func.count(Invoice.id).label("count"),
            func.coalesce(func.sum(Invoice.total_cents), 0).label("total"),
        ).where(
            Invoice.client_contact_id == contact_id,
            Invoice.status != "cancelled",
        )
    )
    row = invoiced.one()
    total_invoiced = row.total
    invoice_count = row.count

    # Paid
    paid = await session.execute(
        select(func.coalesce(func.sum(Invoice.total_cents), 0)).where(
            Invoice.client_contact_id == contact_id,
            Invoice.status == "paid",
        )
    )
    total_paid = paid.scalar_one()

    # Overdue
    overdue = await session.execute(
        select(func.coalesce(func.sum(Invoice.total_cents), 0)).where(
            Invoice.client_contact_id == contact_id,
            Invoice.status == "overdue",
        )
    )
    total_overdue = overdue.scalar_one()

    # Last payment date
    last_payment = await session.execute(
        select(Invoice.updated_at)
        .where(
            Invoice.client_contact_id == contact_id,
            Invoice.status == "paid",
        )
        .order_by(Invoice.updated_at.desc())
        .limit(1)
    )
    last_date = last_payment.scalar_one_or_none()

    outstanding = total_invoiced - total_paid

    return {
        "total_invoiced_cents": total_invoiced,
        "total_paid_cents": total_paid,
        "total_outstanding_cents": outstanding,
        "total_overdue_cents": total_overdue,
        "invoice_count": invoice_count,
        "last_payment_date": last_date.isoformat() if last_date else None,
    }
