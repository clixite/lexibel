"""Cases router — CRUD + conflict check + deadlines + relations.

GET    /api/v1/cases                         — paginated list with filters
POST   /api/v1/cases                         — create case
GET    /api/v1/cases/{id}                    — get case
PATCH  /api/v1/cases/{id}                    — update case
POST   /api/v1/cases/{id}/conflict-check     — conflict of interest check
GET    /api/v1/cases/{id}/deadlines          — Belgian legal deadlines
GET    /api/v1/cases/{id}/relations          — related cases
POST   /api/v1/cases/{id}/relations          — create case relation
DELETE /api/v1/cases/{id}/relations/{rel_id} — remove case relation
"""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_current_tenant, get_db_session
from apps.api.schemas.case import (
    CaseCreate,
    CaseListResponse,
    CaseResponse,
    CaseUpdate,
)
from apps.api.schemas.case_deadline import (
    CaseRelationCreate,
    DeadlineReportResponse,
    DeadlineResponse,
)
from apps.api.services import case_service
from apps.api.services.case_deadline_service import compute_case_deadlines

logger = logging.getLogger(__name__)


class LinkCaseContactRequest(BaseModel):
    contact_id: uuid.UUID
    role: str = Field("client", pattern=r"^(client|adverse|witness|expert|other)$")


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


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case(
    case_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """Soft-delete a case (sets status to 'archived')."""
    deleted = await case_service.delete_case(session, case_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Case not found")
    await session.commit()


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
    body: LinkCaseContactRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Link a contact to a case."""
    from packages.db.models.case_contact import CaseContact

    try:
        link = CaseContact(
            case_id=case_id,
            contact_id=body.contact_id,
            tenant_id=tenant_id,
            role=body.role,
        )
        session.add(link)
        await session.flush()
    except Exception as e:
        logger.error(
            "Failed to link contact %s to case %s: %s", body.contact_id, case_id, e
        )
        raise HTTPException(status_code=500, detail="Failed to link contact to case")
    return {
        "message": "Contact linked",
        "case_id": str(case_id),
        "contact_id": str(body.contact_id),
        "role": body.role,
    }


@router.delete(
    "/{case_id}/contacts/{contact_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def unlink_case_contact(
    case_id: uuid.UUID,
    contact_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """Unlink a contact from a case."""
    from sqlalchemy import delete as sa_delete

    from packages.db.models.case_contact import CaseContact

    result = await session.execute(
        sa_delete(CaseContact).where(
            CaseContact.case_id == case_id,
            CaseContact.contact_id == contact_id,
        )
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Contact link not found")
    await session.commit()


@router.get("/{case_id}/time-entries")
async def get_case_time_entries(
    case_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """List time entries for a case."""
    from packages.db.models.time_entry import TimeEntry
    from sqlalchemy import select as sa_select

    result = await session.execute(
        sa_select(TimeEntry)
        .where(TimeEntry.case_id == case_id)
        .order_by(TimeEntry.entry_date.desc())
    )
    entries = result.scalars().all()
    return {
        "items": [
            {
                "id": str(e.id),
                "date": e.entry_date.isoformat(),
                "description": e.description,
                "duration_minutes": e.duration_minutes,
                "billable": e.billable,
                "status": e.status,
                "amount": e.billable_amount_cents / 100
                if e.billable_amount_cents
                else None,
            }
            for e in entries
        ]
    }


@router.get("/{case_id}/documents")
async def get_case_documents(
    case_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """List documents linked to a case via its events."""
    from packages.db.models.evidence_link import EvidenceLink
    from packages.db.models.interaction_event import InteractionEvent
    from sqlalchemy import select as sa_select

    result = await session.execute(
        sa_select(EvidenceLink)
        .join(InteractionEvent, InteractionEvent.id == EvidenceLink.event_id)
        .where(InteractionEvent.case_id == case_id)
        .order_by(EvidenceLink.created_at.desc())
    )
    links = result.scalars().all()
    return {
        "items": [
            {
                "id": str(link.id),
                "file_name": link.file_name,
                "mime_type": link.mime_type,
                "file_size_bytes": link.file_size_bytes,
                "sha256": link.sha256,
                "created_at": link.created_at.isoformat(),
            }
            for link in links
        ]
    }


@router.post("/{case_id}/conflict-check")
async def conflict_check(
    case_id: uuid.UUID,
    contact_id: Optional[uuid.UUID] = None,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Check for conflicts of interest on a case or specific contact."""
    result = await case_service.conflict_check(session, case_id, contact_id)
    if result["status"] == "error":
        raise HTTPException(status_code=404, detail=result["detail"])
    return result


# ── Belgian Legal Deadlines ──


@router.get("/{case_id}/deadlines", response_model=DeadlineReportResponse)
async def get_case_deadlines(
    case_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> DeadlineReportResponse:
    """Compute Belgian legal deadlines for a case.

    Calculates prescription, appeal, opposition, cassation, and procedural
    deadlines based on the case's matter type, dates, and metadata.
    References Belgian Code civil, Code judiciaire, and Code pénal.
    """
    case = await case_service.get_case(session, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")

    report = compute_case_deadlines(
        matter_type=case.matter_type,
        opened_at=case.opened_at,
        metadata=case.metadata_,
    )
    report.case_id = str(case_id)

    return DeadlineReportResponse(
        case_id=report.case_id,
        matter_type=report.matter_type,
        deadlines=[
            DeadlineResponse(
                title=d.title,
                date=d.date,
                legal_basis=d.legal_basis,
                days_remaining=d.days_remaining,
                urgency=d.urgency,
                category=d.category,
                notes=d.notes,
            )
            for d in report.deadlines
        ],
        warnings=report.warnings,
    )


# ── Case Relations ──


@router.get("/{case_id}/relations")
async def get_case_relations(
    case_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Get all cases related to this case (appeal, opposition, joined, etc.)."""
    from sqlalchemy import or_, select as sa_select

    from packages.db.models.case import Case
    from packages.db.models.case_relation import CaseRelation

    # Relations where this case is source or target
    result = await session.execute(
        sa_select(CaseRelation, Case)
        .join(
            Case,
            or_(
                (CaseRelation.target_case_id == Case.id)
                & (CaseRelation.source_case_id == case_id),
                (CaseRelation.source_case_id == Case.id)
                & (CaseRelation.target_case_id == case_id),
            ),
        )
        .where(
            or_(
                CaseRelation.source_case_id == case_id,
                CaseRelation.target_case_id == case_id,
            )
        )
    )
    rows = result.all()

    return {
        "items": [
            {
                "id": str(rel.id),
                "source_case_id": str(rel.source_case_id),
                "target_case_id": str(rel.target_case_id),
                "relation_type": rel.relation_type,
                "notes": rel.notes,
                "related_case": {
                    "id": str(case.id),
                    "reference": case.reference,
                    "title": case.title,
                    "status": case.status,
                    "matter_type": case.matter_type,
                },
                "created_at": rel.created_at.isoformat(),
            }
            for rel, case in rows
        ]
    }


@router.post("/{case_id}/relations", status_code=status.HTTP_201_CREATED)
async def create_case_relation(
    case_id: uuid.UUID,
    body: CaseRelationCreate,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Create a relation between two cases.

    Relation types:
    - appeal: appel d'un jugement
    - opposition: opposition à un jugement par défaut
    - cassation: pourvoi en cassation
    - joined: jonction de causes (Art. 30 C.Jud.)
    - split: disjonction
    - related: dossier connexe
    - parent: dossier principal / sous-dossier
    """
    from packages.db.models.case_relation import CaseRelation

    # Verify target case exists
    target = await case_service.get_case(session, body.target_case_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Target case not found")

    if case_id == body.target_case_id:
        raise HTTPException(
            status_code=400, detail="Cannot create relation with itself"
        )

    relation = CaseRelation(
        tenant_id=tenant_id,
        source_case_id=case_id,
        target_case_id=body.target_case_id,
        relation_type=body.relation_type,
        notes=body.notes,
    )
    session.add(relation)
    await session.flush()
    await session.commit()

    return {
        "id": str(relation.id),
        "source_case_id": str(case_id),
        "target_case_id": str(body.target_case_id),
        "relation_type": body.relation_type,
        "notes": body.notes,
    }


@router.delete(
    "/{case_id}/relations/{relation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_case_relation(
    case_id: uuid.UUID,
    relation_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """Remove a case relation."""
    from sqlalchemy import delete as sa_delete

    from packages.db.models.case_relation import CaseRelation

    result = await session.execute(
        sa_delete(CaseRelation).where(
            CaseRelation.id == relation_id,
            CaseRelation.source_case_id == case_id,
        )
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Relation not found")
    await session.commit()
