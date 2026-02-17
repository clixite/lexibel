"""Documents router — file upload and download (GED).

GET    /api/v1/documents                     — list all documents
POST   /api/v1/events/{event_id}/documents  — upload document to event
GET    /api/v1/documents/{id}/download       — download document by evidence link ID
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, Query, status
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_current_tenant, get_db_session
from apps.api.schemas.timeline import EvidenceLinkResponse
from apps.api.services import document_service
from packages.db.models.evidence_link import EvidenceLink

router = APIRouter(prefix="/api/v1", tags=["documents"])


@router.get("/documents")
async def list_documents(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    case_id: uuid.UUID | None = Query(None),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db_session),
):
    """List all documents with pagination."""
    query = select(EvidenceLink).where(EvidenceLink.tenant_id == tenant_id)

    if case_id:
        # Join with interaction_events to filter by case
        from packages.db.models.interaction_event import InteractionEvent

        query = query.join(InteractionEvent).where(InteractionEvent.case_id == case_id)

    query = query.order_by(EvidenceLink.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await session.execute(query)
    documents = result.scalars().all()

    # Count total
    count_query = (
        select(func.count())
        .select_from(EvidenceLink)
        .where(EvidenceLink.tenant_id == tenant_id)
    )
    if case_id:
        count_query = count_query.join(InteractionEvent).where(
            InteractionEvent.case_id == case_id
        )

    total_result = await session.execute(count_query)
    total = total_result.scalar()

    return {
        "documents": [
            {
                "id": str(doc.id),
                "file_name": doc.file_name,
                "mime_type": doc.mime_type,
                "file_size_bytes": doc.file_size_bytes,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
            }
            for doc in documents
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.post(
    "/events/{event_id}/documents",
    response_model=EvidenceLinkResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    event_id: uuid.UUID,
    file: UploadFile,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db_session),
) -> EvidenceLinkResponse:
    file_data = await file.read()
    if len(file_data) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file",
        )

    link = await document_service.upload_file(
        session,
        tenant_id,
        event_id,
        file_name=file.filename or "unnamed",
        file_data=file_data,
        mime_type=file.content_type or "application/octet-stream",
    )
    return EvidenceLinkResponse.model_validate(link)


@router.get("/documents/{link_id}/download")
async def download_document(
    link_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    link, file_data = await document_service.download_file(session, link_id)
    if link is None:
        raise HTTPException(status_code=404, detail="Document not found")

    return Response(
        content=file_data,
        media_type=link.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{link.file_name}"',
        },
    )
