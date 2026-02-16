"""Pydantic schemas for Migration endpoints."""

from typing import Optional

from pydantic import BaseModel, Field


class MigrationJobCreate(BaseModel):
    source_system: str = Field(..., pattern="^(forlex|dpa_jbox|outlook|csv)$")


class MigrationJobResponse(BaseModel):
    id: str
    tenant_id: str
    source_system: str
    status: str
    total_records: int
    imported_records: int
    failed_records: int
    error_log: list[dict] = []
    file_path: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    created_by: str


class MigrationJobListResponse(BaseModel):
    items: list[MigrationJobResponse]
    total: int


class MigrationPreviewRequest(BaseModel):
    data: list[dict] = Field(..., min_length=1)


class MigrationPreviewResponse(BaseModel):
    job_id: str
    total_records: int
    duplicates: int
    tables: list[str]
    sample: list[dict]
