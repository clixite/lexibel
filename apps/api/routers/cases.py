"""Cases router — CRUD + conflict check.

GET    /api/v1/cases              — paginated list with filters
POST   /api/v1/cases              — create case
GET    /api/v1/cases/{id}         — get case
PATCH  /api/v1/cases/{id}         — update case
POST   /api/v1/cases/{id}/conflict-check — conflict of interest check
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_current_tenant, get_db_session
from apps.api.schemas.case import (
    CaseCreate,
    CaseListResponse,
    CaseResponse,
    CaseUpdate,
)
from apps.api.services import case_service

router = APIRouter(prefix="/api/v1/cases", tags=["cases"])


@router.get("", response_model=CaseListResponse)
async def list_cases(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    matter_type: Optional[str] = Query(None),
    responsible_user_id: Optional[uuid.UUID] = Query(None),
    session: AsyncSession = Depends(get_db_session),
) -> CaseListResponse:
    items, total = await case_service.list_cases(
        session,
        page=page,
        per_page=per_page,
        status=status_filter,
        matter_type=matter_type,
        responsible_user_id=responsible_user_id,
    )
    return CaseListResponse(
        items=[CaseResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.post("", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
async def create_case(
    body: CaseCreate,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db_session),
) -> CaseResponse:
    case = await case_service.create_case(
        session,
        tenant_id=tenant_id,
        reference=body.reference,
        title=body.title,
        matter_type=body.matter_type,
        court_reference=body.court_reference,
        status=body.status,
        jurisdiction=body.jurisdiction,
        responsible_user_id=body.responsible_user_id,
        opened_at=body.opened_at,
        metadata_=body.metadata,
    )
    return CaseResponse.model_validate(case)


@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(
    case_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> CaseResponse:
    case = await case_service.get_case(session, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return CaseResponse.model_validate(case)


@router.patch("/{case_id}", response_model=CaseResponse)
async def update_case(
    case_id: uuid.UUID,
    body: CaseUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> CaseResponse:
    update_data = body.model_dump(exclude_unset=True)
    if "metadata" in update_data:
        update_data["metadata_"] = update_data.pop("metadata")
    case = await case_service.update_case(session, case_id, **update_data)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return CaseResponse.model_validate(case)


@router.get("/{case_id}/contacts")
async def get_case_contacts(
    case_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """List contacts linked to a case via case_contacts junction."""
    from sqlalchemy import select as sa_select

    from packages.db.models.case_contact import CaseContact
    from packages.db.models.contact import Contact

    result = await session.execute(
        sa_select(Contact, CaseContact.role)
        .join(CaseContact, CaseContact.contact_id == Contact.id)
        .where(CaseContact.case_id == case_id)
    )
    rows = result.all()
    return {
        "items": [
            {
                "id": str(contact.id),
                "full_name": contact.full_name,
                "type": contact.type,
                "email": contact.email,
                "phone_e164": contact.phone_e164,
                "role": role,
            }
            for contact, role in rows
        ]
    }


@router.post("/{case_id}/contacts", status_code=status.HTTP_201_CREATED)
async def link_case_contact(
    case_id: uuid.UUID,
    body: dict,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Link a contact to a case."""
    from packages.db.models.case_contact import CaseContact

    contact_id = body.get("contact_id")
    role = body.get("role", "client")
    if not contact_id:
        raise HTTPException(status_code=400, detail="contact_id required")

    link = CaseContact(
        case_id=case_id,
        contact_id=uuid.UUID(contact_id),
        tenant_id=tenant_id,
        role=role,
    )
    session.add(link)
    await session.flush()
    return {
        "message": "Contact linked",
        "case_id": str(case_id),
        "contact_id": contact_id,
        "role": role,
    }


@router.post("/{case_id}/conflict-check")
async def conflict_check(
    case_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    result = await case_service.conflict_check(session, case_id)
    if result["status"] == "error":
        raise HTTPException(status_code=404, detail=result["detail"])
    return result
