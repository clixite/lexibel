"""DPA JBox importer — parse DPA JBox exports into LexiBel records.

Handles PDF metadata and document listings from JBox exports.
"""
import uuid

from apps.api.services.migration_service import MigrationRecord


class DPAImporter:
    """Parse DPA JBox exports into MigrationRecords."""

    def parse(self, raw_data: list[dict], tenant_id: str) -> list[MigrationRecord]:
        """Parse raw DPA JBox data into migration records."""
        records: list[MigrationRecord] = []

        for row in raw_data:
            record_type = row.get("_type", "document")

            if record_type == "case":
                records.append(self._parse_case(row, tenant_id))
            elif record_type == "document":
                records.append(self._parse_document(row, tenant_id))
            else:
                records.append(self._parse_document(row, tenant_id))

        return records

    def _parse_case(self, row: dict, tenant_id: str) -> MigrationRecord:
        return MigrationRecord(
            source_id=row.get("reference", str(uuid.uuid4())),
            source_data=row,
            target_table="cases",
            target_data={
                "tenant_id": tenant_id,
                "reference": row.get("reference", ""),
                "title": row.get("titre", row.get("title", "")),
                "matter_type": row.get("type_matiere", "general"),
                "status": "open",
            },
        )

    def _parse_document(self, row: dict, tenant_id: str) -> MigrationRecord:
        return MigrationRecord(
            source_id=row.get("document_id", str(uuid.uuid4())),
            source_data=row,
            target_table="evidence_links",
            target_data={
                "tenant_id": tenant_id,
                "file_name": row.get("filename", row.get("file_name", "")),
                "mime_type": row.get("mime_type", "application/pdf"),
                "file_path": row.get("path", ""),
            },
        )
