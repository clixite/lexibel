"""Generic CSV importer — parse CSV-like data into LexiBel records.

Used for generic CSV imports and as fallback for Outlook imports.
"""
import uuid

from apps.api.services.migration_service import MigrationRecord


# Default CSV column → LexiBel field mappings
DEFAULT_CASE_MAPPING = {
    "reference": "reference",
    "title": "title",
    "titre": "title",
    "type": "matter_type",
    "status": "status",
    "statut": "status",
    "date": "opened_at",
}

DEFAULT_CONTACT_MAPPING = {
    "name": "full_name",
    "nom": "full_name",
    "full_name": "full_name",
    "email": "email",
    "phone": "phone_e164",
    "telephone": "phone_e164",
    "type": "type",
}


class CSVImporter:
    """Parse generic CSV data into MigrationRecords."""

    def parse(self, raw_data: list[dict], tenant_id: str) -> list[MigrationRecord]:
        """Parse raw CSV rows into migration records.

        Detects record type from _type field or column heuristics.
        """
        records: list[MigrationRecord] = []

        for row in raw_data:
            record_type = row.get("_type", self._detect_type(row))

            if record_type == "case":
                records.append(self._parse_with_mapping(
                    row, tenant_id, "cases", DEFAULT_CASE_MAPPING
                ))
            elif record_type == "contact":
                records.append(self._parse_with_mapping(
                    row, tenant_id, "contacts", DEFAULT_CONTACT_MAPPING
                ))
            else:
                # Default to case
                records.append(self._parse_with_mapping(
                    row, tenant_id, "cases", DEFAULT_CASE_MAPPING
                ))

        return records

    def _detect_type(self, row: dict) -> str:
        """Detect record type from column names."""
        keys = set(row.keys())
        if keys & {"email", "phone", "telephone", "nom", "full_name"}:
            return "contact"
        return "case"

    def _parse_with_mapping(
        self,
        row: dict,
        tenant_id: str,
        target_table: str,
        mapping: dict[str, str],
    ) -> MigrationRecord:
        target_data: dict = {"tenant_id": tenant_id}
        for src, dst in mapping.items():
            if src in row and row[src]:
                target_data[dst] = row[src]

        source_id = (
            row.get("id")
            or row.get("reference")
            or row.get("name")
            or row.get("nom")
            or str(uuid.uuid4())
        )

        return MigrationRecord(
            source_id=str(source_id),
            source_data=row,
            target_table=target_table,
            target_data=target_data,
        )
