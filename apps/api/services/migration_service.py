"""Migration service — orchestrates data import from external systems.

Supports: Forlex, DPA JBox, Outlook, generic CSV.
Batch processing (100 records), duplicate detection, rollback capability.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class MigrationRecord:
    """A single record to import."""

    source_id: str = ""
    source_data: dict = field(default_factory=dict)
    target_table: str = ""
    target_data: dict = field(default_factory=dict)
    error: Optional[str] = None
    imported: bool = False


@dataclass
class MigrationJob:
    """In-memory representation of a migration job."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = ""
    source_system: str = ""
    status: str = "pending"
    total_records: int = 0
    imported_records: int = 0
    failed_records: int = 0
    error_log: list[dict] = field(default_factory=list)
    file_path: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    created_by: str = ""
    records: list[MigrationRecord] = field(default_factory=list)


# ── In-memory job store (replaced by DB in production) ──
_jobs: dict[str, MigrationJob] = {}

BATCH_SIZE = 100
VALID_SOURCES = {"forlex", "dpa_jbox", "outlook", "csv"}


def create_job(
    tenant_id: str,
    source_system: str,
    created_by: str,
    file_path: Optional[str] = None,
) -> MigrationJob:
    """Create a new migration job."""
    if source_system not in VALID_SOURCES:
        raise ValueError(
            f"Invalid source_system: {source_system}. Must be one of {VALID_SOURCES}"
        )

    job = MigrationJob(
        tenant_id=tenant_id,
        source_system=source_system,
        created_by=created_by,
        file_path=file_path,
    )
    _jobs[job.id] = job
    return job


def get_job(job_id: str, tenant_id: str) -> Optional[MigrationJob]:
    """Get a job by ID with tenant check."""
    job = _jobs.get(job_id)
    if job and job.tenant_id == tenant_id:
        return job
    return None


def list_jobs(tenant_id: str) -> list[MigrationJob]:
    """List all jobs for a tenant."""
    return [j for j in _jobs.values() if j.tenant_id == tenant_id]


def preview_import(job_id: str, tenant_id: str, raw_data: list[dict]) -> dict:
    """Parse and preview records before import. Returns preview summary."""
    job = get_job(job_id, tenant_id)
    if not job:
        raise ValueError("Job not found")

    from apps.api.services.importers import get_importer

    importer = get_importer(job.source_system)
    records = importer.parse(raw_data, tenant_id)

    job.records = records
    job.total_records = len(records)
    job.status = "parsing"

    # Duplicate detection
    seen: set[str] = set()
    duplicates = 0
    for r in records:
        key = f"{r.target_table}:{r.source_id}"
        if key in seen:
            duplicates += 1
            r.error = "duplicate"
        seen.add(key)

    return {
        "job_id": job.id,
        "total_records": len(records),
        "duplicates": duplicates,
        "tables": list({r.target_table for r in records}),
        "sample": [
            {
                "source_id": r.source_id,
                "target_table": r.target_table,
                "target_data": r.target_data,
            }
            for r in records[:5]
        ],
    }


def start_import(job_id: str, tenant_id: str) -> MigrationJob:
    """Start importing records in batches."""
    job = get_job(job_id, tenant_id)
    if not job:
        raise ValueError("Job not found")
    if not job.records:
        raise ValueError("No records to import. Run preview first.")

    job.status = "importing"
    job.started_at = datetime.now(timezone.utc).isoformat()
    job.imported_records = 0
    job.failed_records = 0
    job.error_log = []

    # Process in batches
    for i in range(0, len(job.records), BATCH_SIZE):
        batch = job.records[i : i + BATCH_SIZE]
        for record in batch:
            if record.error:
                job.failed_records += 1
                job.error_log.append(
                    {
                        "source_id": record.source_id,
                        "error": record.error,
                    }
                )
                continue

            # Simulate import (in production: actual DB insert)
            record.imported = True
            job.imported_records += 1

    # Validation step
    job.status = "validating"
    if job.failed_records > job.total_records * 0.5:
        job.status = "failed"
        job.error_log.append({"error": "Too many failures (>50%)"})
    else:
        job.status = "completed"

    job.completed_at = datetime.now(timezone.utc).isoformat()
    return job


def rollback_job(job_id: str, tenant_id: str) -> MigrationJob:
    """Rollback an import job."""
    job = get_job(job_id, tenant_id)
    if not job:
        raise ValueError("Job not found")

    # Mark all records as not imported
    for record in job.records:
        record.imported = False

    job.imported_records = 0
    job.status = "pending"
    job.started_at = None
    job.completed_at = None
    job.error_log.append(
        {"action": "rollback", "timestamp": datetime.now(timezone.utc).isoformat()}
    )

    return job


def reset_store() -> None:
    """Reset the in-memory store (for testing)."""
    _jobs.clear()
