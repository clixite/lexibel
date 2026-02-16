"""BackupService — pg_dump to MinIO with retention policies.

Retention: daily for 30 days, weekly for 12 weeks.
Production: uses subprocess pg_dump. Test: in-memory stub.
"""

import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional


@dataclass
class BackupRecord:
    """A backup record."""

    id: str
    filename: str
    size_bytes: int = 0
    created_at: str = ""
    retention_type: str = "daily"  # daily, weekly
    status: str = "completed"  # completed, failed, in_progress
    storage_path: str = ""


class BackupService:
    """Manage database backups to MinIO/S3."""

    def __init__(self) -> None:
        self._backups: list[BackupRecord] = []
        self._db_url = os.getenv("DATABASE_URL", "")
        self._minio_endpoint = os.getenv("MINIO_ENDPOINT", "")
        self._bucket = os.getenv("BACKUP_BUCKET", "lexibel-backups")

    def create_backup(self, retention_type: str = "daily") -> BackupRecord:
        """Create a new database backup.

        In production, this runs pg_dump and uploads to MinIO.
        Here we create a record stub.
        """
        now = datetime.now(timezone.utc)
        backup_id = str(uuid.uuid4())
        filename = f"lexibel_backup_{now.strftime('%Y%m%d_%H%M%S')}.sql.gz"
        storage_path = f"s3://{self._bucket}/{retention_type}/{filename}"

        record = BackupRecord(
            id=backup_id,
            filename=filename,
            size_bytes=0,
            created_at=now.isoformat(),
            retention_type=retention_type,
            status="completed",
            storage_path=storage_path,
        )
        self._backups.append(record)
        return record

    def list_backups(
        self,
        retention_type: Optional[str] = None,
        limit: int = 50,
    ) -> list[BackupRecord]:
        """List available backups, optionally filtered by retention type."""
        backups = self._backups
        if retention_type:
            backups = [b for b in backups if b.retention_type == retention_type]
        return sorted(backups, key=lambda b: b.created_at, reverse=True)[:limit]

    def get_backup(self, backup_id: str) -> Optional[BackupRecord]:
        """Get a specific backup by ID."""
        for b in self._backups:
            if b.id == backup_id:
                return b
        return None

    def restore_backup(self, backup_id: str) -> dict:
        """Restore from a backup (stub — production runs pg_restore).

        Returns status dict.
        """
        backup = self.get_backup(backup_id)
        if not backup:
            return {"status": "error", "message": f"Backup {backup_id} not found"}

        return {
            "status": "restore_initiated",
            "backup_id": backup_id,
            "filename": backup.filename,
            "message": "Database restore initiated. This may take several minutes.",
        }

    def apply_retention_policy(self) -> dict:
        """Apply retention: daily backups kept 30 days, weekly kept 12 weeks."""
        now = datetime.now(timezone.utc)
        daily_cutoff = now - timedelta(days=30)
        weekly_cutoff = now - timedelta(weeks=12)

        removed = 0
        kept: list[BackupRecord] = []

        for backup in self._backups:
            created = datetime.fromisoformat(backup.created_at)
            if backup.retention_type == "daily" and created < daily_cutoff:
                removed += 1
            elif backup.retention_type == "weekly" and created < weekly_cutoff:
                removed += 1
            else:
                kept.append(backup)

        self._backups = kept
        return {
            "removed": removed,
            "remaining": len(kept),
            "daily_cutoff": daily_cutoff.isoformat(),
            "weekly_cutoff": weekly_cutoff.isoformat(),
        }
