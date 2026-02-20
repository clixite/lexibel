"""Contacts router — CRUD + search.

GET    /api/v1/contacts           — paginated list
POST   /api/v1/contacts           — create contact
GET    /api/v1/contacts/search    — search by name/bce/phone/email
GET    /api/v1/contacts/{id}      — get contact
PATCH  /api/v1/contacts/{id}      — update contact
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_current_tenant, get_db_session
from apps.api.schemas.contact import (
    ContactCreate,
    ContactListResponse,
    ContactResponse,
    ContactUpdate,
)
from apps.api.services import contact_service

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
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Get all cases linked to this contact with their roles."""
    from packages.db.models.case import Case
    from packages.db.models.case_contact import CaseContact
    from sqlalchemy import select as sa_select

    result = await session.execute(
        sa_select(Case, CaseContact.role)
        .join(CaseContact, CaseContact.case_id == Case.id)
        .where(CaseContact.contact_id == contact_id)
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
