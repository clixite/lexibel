"""Contacts router — CRUD + search + activity + merge + financial.

GET    /api/v1/contacts                   — paginated list
POST   /api/v1/contacts                   — create contact
GET    /api/v1/contacts/search            — search by name/bce/phone/email
GET    /api/v1/contacts/{id}              — get contact
PATCH  /api/v1/contacts/{id}              — update contact
DELETE /api/v1/contacts/{id}              — delete contact
GET    /api/v1/contacts/{id}/cases        — linked cases
GET    /api/v1/contacts/{id}/activity     — unified activity timeline
GET    /api/v1/contacts/{id}/financial    — financial summary
GET    /api/v1/contacts/{id}/duplicates   — find potential duplicates
POST   /api/v1/contacts/merge             — merge two contacts
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_current_tenant, get_current_user, get_db_session
from apps.api.schemas.contact import (
    ContactCreate,
    ContactListResponse,
    ContactResponse,
    ContactUpdate,
)
from apps.api.schemas.contact_activity import (
    ContactActivityResponse,
    ContactDuplicateResponse,
    ContactFinancialResponse,
    ContactMergeRequest,
    ContactMergeResponse,
)
from apps.api.services import contact_service
from apps.api.services.contact_activity_service import (
    get_contact_activity,
    get_contact_financial_summary,
)
from apps.api.services.contact_merge_service import find_duplicates, merge_contacts

router = APIRouter(prefix="/api/v1/contacts", tags=["contacts"])


@router.get("", response_model=ContactListResponse)
async def list_contacts(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
) -> ContactListResponse:
    items, total = await contact_service.list_contacts(
        session, page=page, per_page=per_page
    )
    return ContactListResponse(
        items=[ContactResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.post("", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
async def create_contact(
    body: ContactCreate,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Create contact with duplicate detection warning."""
    contact = await contact_service.create_contact(
        session,
        tenant_id=tenant_id,
        type=body.type,
        full_name=body.full_name,
        bce_number=body.bce_number,
        email=body.email,
        phone_e164=body.phone_e164,
        address=body.address,
        language=body.language,
        metadata_=body.metadata,
    )
    response = ContactResponse.model_validate(contact).model_dump()

    # Add duplicate warning if found
    if hasattr(contact, "_duplicate_warning"):
        response["duplicate_warning"] = contact._duplicate_warning

    await session.commit()
    return response


@router.get("/search", response_model=ContactListResponse)
async def search_contacts(
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
) -> ContactListResponse:
    items, total = await contact_service.search_contacts(
        session, q=q, page=page, per_page=per_page
    )
    return ContactListResponse(
        items=[ContactResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        per_page=per_page,
    )


# ── Merge endpoint (before {contact_id} routes) ──


@router.post("/merge", response_model=ContactMergeResponse)
async def merge_contacts_endpoint(
    body: ContactMergeRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ContactMergeResponse:
    """Merge two contacts into one.

    The secondary contact is absorbed into the primary:
    - All case links, invoices, and call records are transferred
    - Metadata is merged (primary wins, secondary fills gaps)
    - An audit event is created
    - The secondary contact is deleted
    """
    try:
        result = await merge_contacts(
            session,
            primary_id=body.primary_id,
            secondary_id=body.secondary_id,
            user_id=current_user["user_id"],
            tenant_id=tenant_id,
        )
        await session.commit()
        return ContactMergeResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{contact_id}", response_model=ContactResponse)
async def get_contact(
    contact_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> ContactResponse:
    contact = await contact_service.get_contact(session, contact_id)
    if contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    return ContactResponse.model_validate(contact)


@router.get("/{contact_id}/cases")
async def get_contact_cases(
    contact_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Get all cases linked to this contact with their roles."""
    from sqlalchemy import select as sa_select

    from packages.db.models.case import Case
    from packages.db.models.case_contact import CaseContact

    result = await session.execute(
        sa_select(Case, CaseContact.role)
        .join(CaseContact, CaseContact.case_id == Case.id)
        .where(
            CaseContact.contact_id == contact_id,
            CaseContact.tenant_id == tenant_id,
        )
        .order_by(Case.created_at.desc())
    )
    rows = result.all()
    return {
        "items": [
            {
                "id": str(case.id),
                "reference": case.reference,
                "title": case.title,
                "status": case.status,
                "matter_type": case.matter_type,
                "role": role,
            }
            for case, role in rows
        ]
    }


# ── Activity Timeline ──


@router.get("/{contact_id}/activity", response_model=ContactActivityResponse)
async def get_contact_activity_endpoint(
    contact_id: uuid.UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> ContactActivityResponse:
    """Get unified activity timeline for a contact.

    Aggregates emails, calls, invoices, case events, and case links
    into a single chronological feed.
    """
    offset = (page - 1) * per_page
    items, total = await get_contact_activity(
        session, contact_id, limit=per_page, offset=offset
    )
    return ContactActivityResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
    )


# ── Financial Summary ──


@router.get("/{contact_id}/financial", response_model=ContactFinancialResponse)
async def get_contact_financial(
    contact_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> ContactFinancialResponse:
    """Get financial summary for a client contact.

    Returns total invoiced, paid, outstanding, overdue amounts,
    and the last payment date.
    """
    result = await get_contact_financial_summary(session, contact_id)
    return ContactFinancialResponse(**result)


# ── Duplicates ──


@router.get("/{contact_id}/duplicates", response_model=list[ContactDuplicateResponse])
async def get_contact_duplicates(
    contact_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> list[ContactDuplicateResponse]:
    """Find potential duplicate contacts.

    Matches on email, phone, BCE number, and name similarity.
    Returns candidates sorted by confidence score.
    """
    duplicates = await find_duplicates(session, contact_id)
    return [ContactDuplicateResponse(**d) for d in duplicates]


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(
    contact_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """Delete a contact."""
    deleted = await contact_service.delete_contact(session, contact_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Contact not found")
    await session.commit()


@router.patch("/{contact_id}", response_model=ContactResponse)
async def update_contact(
    contact_id: uuid.UUID,
    body: ContactUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> ContactResponse:
    update_data = body.model_dump(exclude_unset=True)
    # Map schema field 'metadata' to model attribute 'metadata_'
    if "metadata" in update_data:
        update_data["metadata_"] = update_data.pop("metadata")
    contact = await contact_service.update_contact(session, contact_id, **update_data)
    if contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    return ContactResponse.model_validate(contact)
