"""Forlex importer — parse Forlex CSV/ZIP exports into LexiBel records.

Maps Forlex fields to LexiBel cases, contacts, time_entries, invoices.
"""

import uuid

from apps.api.services.migration_service import MigrationRecord


# Forlex → LexiBel field mappings
CASE_FIELDS = {
    "numero_dossier": "reference",
    "titre": "title",
    "type_matiere": "matter_type",
    "statut": "status",
    "date_ouverture": "opened_at",
    "reference_tribunal": "court_reference",
}

CONTACT_FIELDS = {
    "nom_complet": "full_name",
    "type_personne": "type",
    "email": "email",
    "telephone": "phone_e164",
    "numero_bce": "bce_number",
}

TIME_ENTRY_FIELDS = {
    "date_prestation": "date",
    "description": "description",
    "duree_minutes": "duration_minutes",
    "taux_horaire": "hourly_rate_cents",
}


class ForlexImporter:
    """Parse Forlex exports into MigrationRecords."""

    def parse(self, raw_data: list[dict], tenant_id: str) -> list[MigrationRecord]:
        """Parse raw Forlex data into migration records."""
        records: list[MigrationRecord] = []

        for row in raw_data:
            record_type = row.get("_type", "case")

            if record_type == "case":
                records.append(self._parse_case(row, tenant_id))
            elif record_type == "contact":
                records.append(self._parse_contact(row, tenant_id))
            elif record_type == "time_entry":
                records.append(self._parse_time_entry(row, tenant_id))
            else:
                records.append(self._parse_case(row, tenant_id))

        return records

    def _parse_case(self, row: dict, tenant_id: str) -> MigrationRecord:
        target_data: dict = {"tenant_id": tenant_id}
        for src, dst in CASE_FIELDS.items():
            if src in row:
                target_data[dst] = row[src]

        # Defaults
        target_data.setdefault("status", "open")
        target_data.setdefault("matter_type", "general")

        return MigrationRecord(
            source_id=row.get("numero_dossier", str(uuid.uuid4())),
            source_data=row,
            target_table="cases",
            target_data=target_data,
        )

    def _parse_contact(self, row: dict, tenant_id: str) -> MigrationRecord:
        target_data: dict = {"tenant_id": tenant_id}
        for src, dst in CONTACT_FIELDS.items():
            if src in row:
                target_data[dst] = row[src]

        # Map type
        raw_type = target_data.get("type", "")
        if raw_type in ("PP", "physique", "natural"):
            target_data["type"] = "natural"
        else:
            target_data["type"] = "legal"

        return MigrationRecord(
            source_id=row.get("nom_complet", str(uuid.uuid4())),
            source_data=row,
            target_table="contacts",
            target_data=target_data,
        )

    def _parse_time_entry(self, row: dict, tenant_id: str) -> MigrationRecord:
        target_data: dict = {"tenant_id": tenant_id, "source": "MIGRATION"}
        for src, dst in TIME_ENTRY_FIELDS.items():
            if src in row:
                target_data[dst] = row[src]

        return MigrationRecord(
            source_id=row.get("id", str(uuid.uuid4())),
            source_data=row,
            target_table="time_entries",
            target_data=target_data,
        )
