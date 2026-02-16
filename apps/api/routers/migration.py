"""Migration router — data import pipeline.

POST /api/v1/migration/jobs — create a migration job
GET  /api/v1/migration/jobs — list migration jobs
GET  /api/v1/migration/jobs/:id — get job details
POST /api/v1/migration/jobs/:id/preview — preview import data
POST /api/v1/migration/jobs/:id/start — start import
POST /api/v1/migration/jobs/:id/rollback — rollback import
"""

from fastapi import APIRouter, Depends, HTTPException, status

from apps.api.dependencies import get_current_user
from apps.api.schemas.migration import (
    MigrationJobCreate,
    MigrationJobListResponse,
    MigrationJobResponse,
    MigrationPreviewRequest,
    MigrationPreviewResponse,
)
from apps.api.services import migration_service

router = APIRouter(prefix="/api/v1/migration", tags=["migration"])


def _job_to_response(job: migration_service.MigrationJob) -> MigrationJobResponse:
    return MigrationJobResponse(
        id=job.id,
        tenant_id=job.tenant_id,
        source_system=job.source_system,
        status=job.status,
        total_records=job.total_records,
        imported_records=job.imported_records,
        failed_records=job.failed_records,
        error_log=job.error_log,
        file_path=job.file_path,
        started_at=job.started_at,
        completed_at=job.completed_at,
        created_by=job.created_by,
    )


@router.post(
    "/jobs", response_model=MigrationJobResponse, status_code=status.HTTP_201_CREATED
)
async def create_job(
    body: MigrationJobCreate,
    current_user: dict = Depends(get_current_user),
) -> MigrationJobResponse:
    """Create a new migration job."""
    job = migration_service.create_job(
        tenant_id=str(current_user["tenant_id"]),
        source_system=body.source_system,
        created_by=str(current_user["user_id"]),
    )
    return _job_to_response(job)


@router.get("/jobs", response_model=MigrationJobListResponse)
async def list_jobs(
    current_user: dict = Depends(get_current_user),
) -> MigrationJobListResponse:
    """List all migration jobs for the tenant."""
    jobs = migration_service.list_jobs(str(current_user["tenant_id"]))
    return MigrationJobListResponse(
        items=[_job_to_response(j) for j in jobs],
        total=len(jobs),
    )


@router.get("/jobs/{job_id}", response_model=MigrationJobResponse)
async def get_job(
    job_id: str,
    current_user: dict = Depends(get_current_user),
) -> MigrationJobResponse:
    """Get migration job details."""
    job = migration_service.get_job(job_id, str(current_user["tenant_id"]))
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_to_response(job)


@router.post("/jobs/{job_id}/preview", response_model=MigrationPreviewResponse)
async def preview_import(
    job_id: str,
    body: MigrationPreviewRequest,
    current_user: dict = Depends(get_current_user),
) -> MigrationPreviewResponse:
    """Preview import data before starting."""
    try:
        result = migration_service.preview_import(
            job_id, str(current_user["tenant_id"]), body.data
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return MigrationPreviewResponse(**result)


@router.post("/jobs/{job_id}/start", response_model=MigrationJobResponse)
async def start_import(
    job_id: str,
    current_user: dict = Depends(get_current_user),
) -> MigrationJobResponse:
    """Start the import process."""
    try:
        job = migration_service.start_import(job_id, str(current_user["tenant_id"]))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return _job_to_response(job)


@router.post("/jobs/{job_id}/rollback", response_model=MigrationJobResponse)
async def rollback_import(
    job_id: str,
    current_user: dict = Depends(get_current_user),
) -> MigrationJobResponse:
    """Rollback an import job."""
    try:
        job = migration_service.rollback_job(job_id, str(current_user["tenant_id"]))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return _job_to_response(job)
