"""AuditExportService — export audit logs for compliance (GDPR Art. 30, DORA).

Supports CSV and JSON export with date filtering, user filtering,
action type filtering, and GDPR anonymization option.
"""
import csv
import io
import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class AuditEntry:
    """A single audit log entry."""
    id: str
    tenant_id: str
    user_id: str
    user_email: str
    action: str
    resource_type: str
    resource_id: str
    timestamp: str
    metadata: dict = field(default_factory=dict)


@dataclass
class AuditExportResult:
    """Result of an audit export."""
    format: str  # csv, json
    record_count: int
    content: str
    anonymized: bool = False
    exported_at: str = ""


# ── Email anonymization pattern ──
_EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")


class AuditExportService:
    """Export audit logs for compliance reporting."""

    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []

    def add_entry(self, entry: AuditEntry) -> None:
        """Add an audit entry (for testing)."""
        self._entries.append(entry)

    def export(
        self,
        tenant_id: str,
        format: str = "json",
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        user_id: Optional[str] = None,
        action_type: Optional[str] = None,
        anonymize: bool = False,
    ) -> AuditExportResult:
        """Export audit log entries.

        Args:
            tenant_id: Filter by tenant
            format: Output format (json, csv)
            date_from: Start date (ISO format)
            date_to: End date (ISO format)
            user_id: Filter by specific user
            action_type: Filter by action (GET, POST, PUT, DELETE)
            anonymize: GDPR anonymization (hash emails, redact PII)

        Returns:
            AuditExportResult with formatted content
        """
        # Filter entries
        filtered = [e for e in self._entries if e.tenant_id == tenant_id]

        if date_from:
            filtered = [e for e in filtered if e.timestamp >= date_from]
        if date_to:
            filtered = [e for e in filtered if e.timestamp <= date_to]
        if user_id:
            filtered = [e for e in filtered if e.user_id == user_id]
        if action_type:
            filtered = [e for e in filtered if e.action == action_type]

        # Anonymize if requested
        if anonymize:
            filtered = [self._anonymize_entry(e) for e in filtered]

        # Format output
        if format == "csv":
            content = self._to_csv(filtered)
        else:
            content = self._to_json(filtered)

        return AuditExportResult(
            format=format,
            record_count=len(filtered),
            content=content,
            anonymized=anonymize,
            exported_at=datetime.now(timezone.utc).isoformat(),
        )

    def _anonymize_entry(self, entry: AuditEntry) -> AuditEntry:
        """Anonymize PII in an audit entry for GDPR compliance."""
        anon_email = self._hash_email(entry.user_email) if entry.user_email else ""

        # Anonymize metadata values
        anon_metadata = {}
        for k, v in entry.metadata.items():
            if isinstance(v, str):
                v = _EMAIL_PATTERN.sub("[REDACTED]", v)
            anon_metadata[k] = v

        return AuditEntry(
            id=entry.id,
            tenant_id=entry.tenant_id,
            user_id="anonymized",
            user_email=anon_email,
            action=entry.action,
            resource_type=entry.resource_type,
            resource_id=entry.resource_id,
            timestamp=entry.timestamp,
            metadata=anon_metadata,
        )

    @staticmethod
    def _hash_email(email: str) -> str:
        """Hash email for anonymization."""
        import hashlib
        return hashlib.sha256(email.encode()).hexdigest()[:16] + "@anonymized"

    def _to_json(self, entries: list[AuditEntry]) -> str:
        """Convert entries to JSON string."""
        data = []
        for e in entries:
            data.append({
                "id": e.id,
                "tenant_id": e.tenant_id,
                "user_id": e.user_id,
                "user_email": e.user_email,
                "action": e.action,
                "resource_type": e.resource_type,
                "resource_id": e.resource_id,
                "timestamp": e.timestamp,
                "metadata": e.metadata,
            })
        return json.dumps(data, indent=2, ensure_ascii=False)

    def _to_csv(self, entries: list[AuditEntry]) -> str:
        """Convert entries to CSV string."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "tenant_id", "user_id", "user_email", "action",
                         "resource_type", "resource_id", "timestamp"])
        for e in entries:
            writer.writerow([
                e.id, e.tenant_id, e.user_id, e.user_email,
                e.action, e.resource_type, e.resource_id, e.timestamp,
            ])
        return output.getvalue()
