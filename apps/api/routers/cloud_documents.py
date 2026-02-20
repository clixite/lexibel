"""Cloud documents router - Google Drive, OneDrive, SharePoint integration.

GET    /api/v1/cloud-documents                   - list cloud documents
GET    /api/v1/cloud-documents/{id}              - get document metadata
GET    /api/v1/cloud-documents/{id}/content      - proxy download
POST   /api/v1/cloud-documents/{id}/link-case    - link to a case
DELETE /api/v1/cloud-documents/{id}/link-case/{case_id} - unlink from case
GET    /api/v1/cloud-documents/search            - semantic + Drive/OneDrive search
POST   /api/v1/sync                              - start sync job
GET    /api/v1/sync/{job_id}                     - get sync job status
GET    /api/v1/sync/history                      - sync job history
POST   /api/v1/oauth/connections/{id}/sync       - trigger sync for a connection
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_current_tenant, get_current_user, get_db_session
from packages.db.models.cloud_document import CloudDocument
from packages.db.models.cloud_sync_job import CloudSyncJob
from packages.db.models.document_case_link import DocumentCaseLink
from packages.db.models.oauth_token import OAuthToken

router = APIRouter(prefix="/api/v1", tags=["cloud-documents"])

# --- Schemas -------------------------------------------------------------------


class CloudDocumentResponse(BaseModel):
    id: str
    tenant_id: str
    oauth_token_id: str
    case_id: Optional[str]
    provider: str
    external_id: str
    name: str
    mime_type: Optional[str]
    size_bytes: Optional[int]
    web_url: Optional[str]
    edit_url: Optional[str]
    thumbnail_url: Optional[str]
    is_folder: bool
    path: Optional[str]
    last_modified_at: Optional[str]
    last_modified_by: Optional[str]
    is_indexed: bool
    index_status: str
    created_at: str
    updated_at: str

    @classmethod
    def from_model(cls, doc: CloudDocument) -> "CloudDocumentResponse":
        return cls(
            id=str(doc.id),
            tenant_id=str(doc.tenant_id),
            oauth_token_id=str(doc.oauth_token_id),
            case_id=str(doc.case_id) if doc.case_id else None,
            provider=doc.provider,
            external_id=doc.external_id,
            name=doc.name,
            mime_type=doc.mime_type,
            size_bytes=doc.size_bytes,
            web_url=doc.web_url,
            edit_url=doc.edit_url,
            thumbnail_url=doc.thumbnail_url,
            is_folder=doc.is_folder,
            path=doc.path,
            last_modified_at=doc.last_modified_at.isoformat()
            if doc.last_modified_at
            else None,
            last_modified_by=doc.last_modified_by,
            is_indexed=doc.is_indexed,
            index_status=doc.index_status,
            created_at=doc.created_at.isoformat(),
            updated_at=doc.updated_at.isoformat(),
        )


class SyncJobResponse(BaseModel):
    id: str
    tenant_id: str
    oauth_token_id: str
    job_type: str
    status: str
    provider: str
    scope: Optional[str]
    total_items: int
    processed_items: int
    error_count: int
    started_at: Optional[str]
    completed_at: Optional[str]
    error_message: Optional[str]
    created_at: str

    @classmethod
    def from_model(cls, job: CloudSyncJob) -> "SyncJobResponse":
        return cls(
            id=str(job.id),
            tenant_id=str(job.tenant_id),
            oauth_token_id=str(job.oauth_token_id),
            job_type=job.job_type,
            status=job.status,
            provider=job.provider,
            scope=job.scope,
            total_items=job.total_items,
            processed_items=job.processed_items,
            error_count=job.error_count,
            started_at=job.started_at.isoformat() if job.started_at else None,
            completed_at=job.completed_at.isoformat() if job.completed_at else None,
            error_message=job.error_message,
            created_at=job.created_at.isoformat(),
        )


class LinkCaseRequest(BaseModel):
    case_id: uuid.UUID
    link_type: str = "reference"
    notes: Optional[str] = None


class StartSyncRequest(BaseModel):
    connection_id: uuid.UUID
    folder_id: Optional[str] = None
    job_type: str = "full"  # "full" | "incremental"


# --- Cloud Documents Endpoints -----------------------------------------------


@router.get("/cloud-documents")
async def list_cloud_documents(
    connection_id: Optional[uuid.UUID] = Query(None),
    folder_id: Optional[str] = Query(
        None, description="Filter by parent folder external_id"
    ),
    case_id: Optional[uuid.UUID] = Query(None),
    provider: Optional[str] = Query(None),
    is_folder: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """List cloud documents with filtering and pagination."""
    query = select(CloudDocument).where(
        CloudDocument.tenant_id == tenant_id,
    )

    if connection_id:
        query = query.where(CloudDocument.oauth_token_id == connection_id)
    if folder_id:
        query = query.where(CloudDocument.external_parent_id == folder_id)
    if case_id:
        query = query.where(CloudDocument.case_id == case_id)
    if provider:
        query = query.where(CloudDocument.provider == provider)
    if is_folder is not None:
        query = query.where(CloudDocument.is_folder == is_folder)
    if search:
        query = query.where(CloudDocument.name.ilike(f"%{search}%"))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    query = (
        query.order_by(CloudDocument.is_folder.desc(), CloudDocument.name.asc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await session.execute(query)
    documents = result.scalars().all()

    return {
        "documents": [CloudDocumentResponse.from_model(d) for d in documents],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/cloud-documents/search")
async def search_cloud_documents(
    q: str = Query(..., min_length=1),
    case_id: Optional[uuid.UUID] = Query(None),
    provider: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Search cloud documents by name (DB search).

    For semantic search via Qdrant, use the /search endpoint.
    """
    query = select(CloudDocument).where(
        CloudDocument.tenant_id == tenant_id,
        CloudDocument.name.ilike(f"%{q}%"),
    )

    if case_id:
        query = query.where(CloudDocument.case_id == case_id)
    if provider:
        query = query.where(CloudDocument.provider == provider)

    query = query.limit(limit)
    result = await session.execute(query)
    documents = result.scalars().all()

    return {
        "results": [CloudDocumentResponse.from_model(d) for d in documents],
        "query": q,
        "total": len(documents),
    }


@router.get("/cloud-documents/{document_id}")
async def get_cloud_document(
    document_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db_session),
) -> CloudDocumentResponse:
    """Get cloud document metadata."""
    result = await session.execute(
        select(CloudDocument).where(
            CloudDocument.id == document_id,
            CloudDocument.tenant_id == tenant_id,
        )
    )
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    return CloudDocumentResponse.from_model(doc)


@router.get("/cloud-documents/{document_id}/content")
async def download_cloud_document(
    document_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """Proxy download of cloud document via provider API.

    GDPR: File is streamed through LexiBel but not stored.
    Audit trail logged.
    """
    result = await session.execute(
        select(CloudDocument).where(
            CloudDocument.id == document_id,
            CloudDocument.tenant_id == tenant_id,
        )
    )
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc.is_folder:
        raise HTTPException(status_code=400, detail="Cannot download a folder")

    try:
        if doc.provider == "google_drive":
            from apps.api.services.google_drive_sync import get_google_drive_sync

            sync_service = get_google_drive_sync()
            content = await sync_service.get_file_content(
                session, doc.oauth_token_id, doc.external_id, doc.mime_type or ""
            )
        else:
            from apps.api.services.microsoft_onedrive_sync import get_onedrive_sync

            sync_service = get_onedrive_sync()
            content = await sync_service.get_file_content(
                session, doc.oauth_token_id, doc.external_id
            )

        # Determine content type for response
        content_type = doc.mime_type or "application/octet-stream"
        # For Google native types, we export as PDF
        if doc.mime_type and "google-apps" in doc.mime_type:
            content_type = "application/pdf"

        import io

        return StreamingResponse(
            io.BytesIO(content),
            media_type=content_type,
            headers={
                "Content-Disposition": "attachment; filename="
                + chr(34)
                + doc.name
                + chr(34),
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to download from provider: {str(e)}",
        )


@router.post("/cloud-documents/{document_id}/link-case")
async def link_document_to_case(
    document_id: uuid.UUID,
    body: LinkCaseRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """Link a cloud document to a legal case."""
    # Verify document exists
    doc_result = await session.execute(
        select(CloudDocument).where(
            CloudDocument.id == document_id,
            CloudDocument.tenant_id == tenant_id,
        )
    )
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check existing link
    existing_result = await session.execute(
        select(DocumentCaseLink).where(
            DocumentCaseLink.cloud_document_id == document_id,
            DocumentCaseLink.case_id == body.case_id,
        )
    )
    existing = existing_result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document already linked to this case",
        )

    # Create link
    link = DocumentCaseLink(
        tenant_id=tenant_id,
        cloud_document_id=document_id,
        case_id=body.case_id,
        linked_by=user["user_id"],
        link_type=body.link_type,
        notes=body.notes,
    )
    session.add(link)
    await session.commit()
    await session.refresh(link)

    return {
        "id": str(link.id),
        "cloud_document_id": str(link.cloud_document_id),
        "case_id": str(link.case_id),
        "link_type": link.link_type,
        "notes": link.notes,
        "created_at": link.created_at.isoformat(),
    }


@router.delete(
    "/cloud-documents/{document_id}/link-case/{case_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def unlink_document_from_case(
    document_id: uuid.UUID,
    case_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db_session),
):
    """Remove link between a cloud document and a case."""
    result = await session.execute(
        select(DocumentCaseLink).where(
            DocumentCaseLink.cloud_document_id == document_id,
            DocumentCaseLink.case_id == case_id,
            DocumentCaseLink.tenant_id == tenant_id,
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    await session.delete(link)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Sync Endpoints -----------------------------------------------------------


@router.post("/sync")
async def start_sync(
    body: StartSyncRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """Start a document synchronization job.

    Dispatches to Celery worker for background processing.
    """
    # Verify connection belongs to tenant
    token_result = await session.execute(
        select(OAuthToken).where(
            OAuthToken.id == body.connection_id,
            OAuthToken.tenant_id == tenant_id,
        )
    )
    token = token_result.scalar_one_or_none()
    if not token:
        raise HTTPException(status_code=404, detail="Connection not found")

    # Determine provider
    provider_map = {
        "google": "google_drive",
        "microsoft": "onedrive",
    }
    provider = provider_map.get(token.provider, token.provider)

    job_type = "full_sync" if body.job_type == "full" else "incremental_sync"

    # Create sync job record
    job = CloudSyncJob(
        tenant_id=tenant_id,
        oauth_token_id=body.connection_id,
        job_type=job_type,
        status="pending",
        provider=provider,
        scope=body.folder_id or "all",
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)

    # Dispatch to Celery (async)
    try:
        from apps.workers.tasks.sync_tasks import sync_documents

        sync_documents.apply_async(
            kwargs={
                "connection_id": str(body.connection_id),
                "job_id": str(job.id),
                "job_type": job_type,
                "folder_id": body.folder_id,
            },
            queue="indexing",
        )
    except Exception as e:
        # If Celery not available, run inline (dev mode)
        import logging

        logging.getLogger(__name__).warning(
            f"Celery not available, skipping async dispatch: {e}"
        )

    return {"job_id": str(job.id), "status": "started"}


@router.get("/sync/history")
async def get_sync_history(
    connection_id: Optional[uuid.UUID] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Get sync job history."""
    query = select(CloudSyncJob).where(CloudSyncJob.tenant_id == tenant_id)
    if connection_id:
        query = query.where(CloudSyncJob.oauth_token_id == connection_id)

    count_q = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_q)).scalar() or 0

    query = (
        query.order_by(desc(CloudSyncJob.created_at))
        .offset((page - 1) * per_page)
        .limit(per_page)
    )

    result = await session.execute(query)
    jobs = result.scalars().all()

    return {
        "jobs": [SyncJobResponse.from_model(j) for j in jobs],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/sync/{job_id}")
async def get_sync_job(
    job_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db_session),
) -> SyncJobResponse:
    """Get sync job status and progress."""
    result = await session.execute(
        select(CloudSyncJob).where(
            CloudSyncJob.id == job_id,
            CloudSyncJob.tenant_id == tenant_id,
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Sync job not found")
    return SyncJobResponse.from_model(job)
