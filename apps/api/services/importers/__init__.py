"""Importers — data parsers for external systems."""

from apps.api.services.importers.forlex_importer import ForlexImporter
from apps.api.services.importers.dpa_importer import DPAImporter
from apps.api.services.importers.csv_importer import CSVImporter


_IMPORTERS = {
    "forlex": ForlexImporter(),
    "dpa_jbox": DPAImporter(),
    "csv": CSVImporter(),
    "outlook": CSVImporter(),  # Outlook uses CSV-like format for initial import
}


def get_importer(source_system: str):
    """Get the importer for a given source system."""
    importer = _IMPORTERS.get(source_system)
    if not importer:
        raise ValueError(f"No importer for source: {source_system}")
    return importer
