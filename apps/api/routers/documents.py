"""Documents router — file upload and download (GED).

POST   /api/v1/events/{event_id}/documents  — upload document to event
GET    /api/v1/documents/{id}/download       — download document by evidence link ID
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_current_tenant, get_db_session
from apps.api.schemas.timeline import EvidenceLinkResponse
from apps.api.services import document_service

router = APIRouter(prefix="/api/v1", tags=["documents"])


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
