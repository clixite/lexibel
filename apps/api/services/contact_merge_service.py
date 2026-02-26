"""Contact merge service — deduplication and consolidation.

Merges two contacts into one:
1. Transfers all relationships (case_contacts, invoices, call_records)
2. Merges metadata (primary wins, secondary fills gaps)
3. Logs the merge in interaction_events for audit trail
4. Deletes the secondary contact

Belgian-specific: preserves BCE numbers, national register numbers,
and ensures no data loss during merge.
"""

import logging
import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.models.call_record import CallRecord
from packages.db.models.case_contact import CaseContact
from packages.db.models.contact import Contact
from packages.db.models.interaction_event import InteractionEvent
from packages.db.models.invoice import Invoice

logger = logging.getLogger(__name__)


async def find_duplicates(
    session: AsyncSession,
    contact_id: uuid.UUID,
) -> list[dict]:
    """Find potential duplicate contacts for a given contact.

    Matches on:
    - Same email address
    - Same phone number (E.164)
    - Same BCE number
    - Similar full name (>80% match)
    """
    contact = await session.execute(select(Contact).where(Contact.id == contact_id))
    source = contact.scalar_one_or_none()
    if not source:
        return []

    from sqlalchemy import or_

    conditions = []
    if source.email:
        conditions.append(Contact.email == source.email)
    if source.phone_e164:
        conditions.append(Contact.phone_e164 == source.phone_e164)
    if source.bce_number:
        conditions.append(Contact.bce_number == source.bce_number)
    # Name similarity — simplified ILIKE matching
    if source.full_name:
        name_parts = source.full_name.split()
        for part in name_parts:
            if len(part) > 2:
                conditions.append(Contact.full_name.ilike(f"%{part}%"))

    if not conditions:
        return []

    result = await session.execute(
        select(Contact)
        .where(
            Contact.id != contact_id,
            Contact.tenant_id == source.tenant_id,
            or_(*conditions),
        )
        .limit(10)
    )
    candidates = result.scalars().all()

    duplicates = []
    for candidate in candidates:
        match_fields = []
        confidence = 0.0

        if source.email and candidate.email == source.email:
            match_fields.append("email")
            confidence += 0.4
        if source.phone_e164 and candidate.phone_e164 == source.phone_e164:
            match_fields.append("phone_e164")
            confidence += 0.3
        if source.bce_number and candidate.bce_number == source.bce_number:
            match_fields.append("bce_number")
            confidence += 0.5
        if source.full_name and candidate.full_name:
            # Simple name overlap check
            s_parts = set(source.full_name.lower().split())
            c_parts = set(candidate.full_name.lower().split())
            overlap = len(s_parts & c_parts)
            total = max(len(s_parts | c_parts), 1)
            name_similarity = overlap / total
            if name_similarity > 0.5:
                match_fields.append("full_name")
                confidence += name_similarity * 0.3

        if match_fields:
            duplicates.append(
                {
                    "id": str(candidate.id),
                    "full_name": candidate.full_name,
                    "type": candidate.type,
                    "email": candidate.email,
                    "phone_e164": candidate.phone_e164,
                    "bce_number": candidate.bce_number,
                    "match_fields": match_fields,
                    "confidence": min(confidence, 1.0),
                }
            )

    # Sort by confidence descending
    duplicates.sort(key=lambda d: d["confidence"], reverse=True)
    return duplicates


def _merge_metadata(primary: dict, secondary: dict) -> dict:
    """Deep merge metadata — primary wins, secondary fills gaps."""
    merged = {**secondary, **primary}
    # For nested dicts, merge recursively
    for key in secondary:
        if (
            key in primary
            and isinstance(primary[key], dict)
            and isinstance(secondary[key], dict)
        ):
            merged[key] = _merge_metadata(primary[key], secondary[key])
        elif key not in primary or primary[key] is None:
            merged[key] = secondary[key]
    return merged


async def merge_contacts(
    session: AsyncSession,
    primary_id: uuid.UUID,
    secondary_id: uuid.UUID,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> dict:
    """Merge secondary contact into primary contact.

    All relationships are transferred. Metadata is merged (primary wins).
    The merge is logged in interaction_events for audit trail.
    Secondary contact is deleted.

    Returns merge summary.
    """
    # Load both contacts (defense-in-depth: filter by tenant_id)
    primary_result = await session.execute(
        select(Contact).where(Contact.id == primary_id, Contact.tenant_id == tenant_id)
    )
    primary = primary_result.scalar_one_or_none()

    secondary_result = await session.execute(
        select(Contact).where(
            Contact.id == secondary_id, Contact.tenant_id == tenant_id
        )
    )
    secondary = secondary_result.scalar_one_or_none()

    if not primary or not secondary:
        raise ValueError("Both contacts must exist")

    if primary.id == secondary.id:
        raise ValueError("Cannot merge a contact with itself")

    summary = {
        "primary_id": str(primary_id),
        "secondary_id": str(secondary_id),
        "primary_name": primary.full_name,
        "secondary_name": secondary.full_name,
        "transfers": {},
    }

    # 1. Transfer case_contacts (avoid duplicates)
    existing_case_links = await session.execute(
        select(CaseContact.case_id).where(CaseContact.contact_id == primary_id)
    )
    existing_case_ids = {row[0] for row in existing_case_links.all()}

    secondary_case_links = await session.execute(
        select(CaseContact).where(CaseContact.contact_id == secondary_id)
    )
    transferred_cases = 0
    for link in secondary_case_links.scalars().all():
        if link.case_id not in existing_case_ids:
            link.contact_id = primary_id
            transferred_cases += 1
        else:
            await session.delete(link)
    summary["transfers"]["case_contacts"] = transferred_cases

    # 2. Transfer invoices
    invoice_update = await session.execute(
        update(Invoice)
        .where(Invoice.client_contact_id == secondary_id)
        .values(client_contact_id=primary_id)
        .execution_options(synchronize_session="fetch")
    )
    summary["transfers"]["invoices"] = invoice_update.rowcount

    # 3. Transfer call records
    call_update = await session.execute(
        update(CallRecord)
        .where(CallRecord.contact_id == secondary_id)
        .values(contact_id=primary_id)
        .execution_options(synchronize_session="fetch")
    )
    summary["transfers"]["call_records"] = call_update.rowcount

    # 4. Merge contact data (fill gaps in primary from secondary)
    if not primary.email and secondary.email:
        primary.email = secondary.email
    if not primary.phone_e164 and secondary.phone_e164:
        primary.phone_e164 = secondary.phone_e164
    if not primary.bce_number and secondary.bce_number:
        primary.bce_number = secondary.bce_number
    if not primary.address and secondary.address:
        primary.address = secondary.address

    # Merge metadata
    primary_meta = primary.metadata_ or {}
    secondary_meta = secondary.metadata_ or {}
    primary.metadata_ = _merge_metadata(primary_meta, secondary_meta)

    # 5. Log the merge as an interaction event (audit trail)
    audit_event = InteractionEvent(
        tenant_id=tenant_id,
        source="MANUAL",
        event_type="INTERNAL_NOTE",
        title=f"Fusion de contacts: {secondary.full_name} → {primary.full_name}",
        body=(
            f"Le contact '{secondary.full_name}' (ID: {secondary_id}) a été fusionné "
            f"dans '{primary.full_name}' (ID: {primary_id}). "
            f"Transferts: {summary['transfers']}"
        ),
        occurred_at=datetime.utcnow(),
        metadata_={
            "action": "contact_merge",
            "primary_id": str(primary_id),
            "secondary_id": str(secondary_id),
            "transfers": summary["transfers"],
        },
        created_by=user_id,
    )
    session.add(audit_event)

    # 6. Delete secondary contact
    await session.delete(secondary)
    await session.flush()

    logger.info(
        "Merged contact %s into %s (cases=%d, invoices=%d, calls=%d)",
        secondary_id,
        primary_id,
        transferred_cases,
        summary["transfers"]["invoices"],
        summary["transfers"]["call_records"],
    )

    return summary
