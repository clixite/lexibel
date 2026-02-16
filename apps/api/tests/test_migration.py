"""Tests for LXB-041-043: Migration pipeline."""
import uuid

import pytest
from fastapi.testclient import TestClient

from apps.api.services.migration_service import (
    create_job,
    get_job,
    list_jobs,
    preview_import,
    start_import,
    rollback_job,
    reset_store,
    VALID_SOURCES,
)
from apps.api.services.importers.forlex_importer import ForlexImporter
from apps.api.services.importers.dpa_importer import DPAImporter
from apps.api.services.importers.csv_importer import CSVImporter
from apps.api.main import app


TENANT_ID = str(uuid.uuid4())
OTHER_TENANT = str(uuid.uuid4())
USER_ID = str(uuid.uuid4())


def _auth_headers() -> dict:
    return {
        "X-Tenant-ID": TENANT_ID,
        "X-User-ID": USER_ID,
        "X-User-Role": "super_admin",
        "X-User-Email": "test@lexibel.be",
    }


# ── Service unit tests ──


class TestMigrationService:
    def setup_method(self):
        reset_store()

    def test_create_job(self):
        job = create_job(TENANT_ID, "forlex", USER_ID)
        assert job.source_system == "forlex"
        assert job.status == "pending"
        assert job.tenant_id == TENANT_ID

    def test_create_job_invalid_source(self):
        with pytest.raises(ValueError, match="Invalid source_system"):
            create_job(TENANT_ID, "invalid", USER_ID)

    def test_get_job_tenant_isolation(self):
        job = create_job(TENANT_ID, "csv", USER_ID)
        assert get_job(job.id, TENANT_ID) is not None
        assert get_job(job.id, OTHER_TENANT) is None

    def test_list_jobs(self):
        create_job(TENANT_ID, "forlex", USER_ID)
        create_job(TENANT_ID, "csv", USER_ID)
        create_job(OTHER_TENANT, "forlex", USER_ID)

        jobs = list_jobs(TENANT_ID)
        assert len(jobs) == 2

    def test_preview_import(self):
        job = create_job(TENANT_ID, "csv", USER_ID)
        raw_data = [
            {"reference": "DOS-001", "title": "Test Case", "_type": "case"},
            {"reference": "DOS-002", "title": "Another Case", "_type": "case"},
        ]
        result = preview_import(job.id, TENANT_ID, raw_data)
        assert result["total_records"] == 2
        assert result["duplicates"] == 0
        assert "cases" in result["tables"]

    def test_preview_detects_duplicates(self):
        job = create_job(TENANT_ID, "csv", USER_ID)
        raw_data = [
            {"reference": "DOS-001", "title": "Test", "_type": "case"},
            {"reference": "DOS-001", "title": "Duplicate", "_type": "case"},
        ]
        result = preview_import(job.id, TENANT_ID, raw_data)
        assert result["duplicates"] == 1

    def test_start_import(self):
        job = create_job(TENANT_ID, "csv", USER_ID)
        raw_data = [
            {"reference": "DOS-001", "title": "Test", "_type": "case"},
            {"reference": "DOS-002", "title": "Test 2", "_type": "case"},
        ]
        preview_import(job.id, TENANT_ID, raw_data)
        result = start_import(job.id, TENANT_ID)
        assert result.status == "completed"
        assert result.imported_records == 2
        assert result.failed_records == 0

    def test_start_import_without_preview(self):
        job = create_job(TENANT_ID, "csv", USER_ID)
        with pytest.raises(ValueError, match="No records"):
            start_import(job.id, TENANT_ID)

    def test_rollback(self):
        job = create_job(TENANT_ID, "csv", USER_ID)
        preview_import(job.id, TENANT_ID, [{"reference": "X", "_type": "case"}])
        start_import(job.id, TENANT_ID)
        assert job.status == "completed"

        rolled_back = rollback_job(job.id, TENANT_ID)
        assert rolled_back.status == "pending"
        assert rolled_back.imported_records == 0

    def test_import_with_duplicates_handles_errors(self):
        job = create_job(TENANT_ID, "csv", USER_ID)
        raw_data = [
            {"reference": "A", "_type": "case"},
            {"reference": "A", "_type": "case"},  # duplicate
            {"reference": "B", "_type": "case"},
        ]
        preview_import(job.id, TENANT_ID, raw_data)
        result = start_import(job.id, TENANT_ID)
        assert result.imported_records == 2
        assert result.failed_records == 1


# ── Importer unit tests ──


class TestForlexImporter:
    def test_parse_case(self):
        importer = ForlexImporter()
        records = importer.parse(
            [{"numero_dossier": "FL-001", "titre": "Test", "type_matiere": "civil", "_type": "case"}],
            TENANT_ID,
        )
        assert len(records) == 1
        assert records[0].target_table == "cases"
        assert records[0].target_data["reference"] == "FL-001"
        assert records[0].target_data["title"] == "Test"

    def test_parse_contact(self):
        importer = ForlexImporter()
        records = importer.parse(
            [{"nom_complet": "Jean Dupont", "type_personne": "PP", "email": "j@test.be", "_type": "contact"}],
            TENANT_ID,
        )
        assert len(records) == 1
        assert records[0].target_table == "contacts"
        assert records[0].target_data["type"] == "natural"

    def test_parse_time_entry(self):
        importer = ForlexImporter()
        records = importer.parse(
            [{"date_prestation": "2026-01-15", "description": "Rdv client", "duree_minutes": 60, "_type": "time_entry"}],
            TENANT_ID,
        )
        assert len(records) == 1
        assert records[0].target_table == "time_entries"
        assert records[0].target_data["source"] == "MIGRATION"


class TestDPAImporter:
    def test_parse_document(self):
        importer = DPAImporter()
        records = importer.parse(
            [{"document_id": "d1", "filename": "conclusions.pdf", "_type": "document"}],
            TENANT_ID,
        )
        assert len(records) == 1
        assert records[0].target_table == "evidence_links"
        assert records[0].target_data["file_name"] == "conclusions.pdf"


class TestCSVImporter:
    def test_detect_contact(self):
        importer = CSVImporter()
        records = importer.parse(
            [{"nom": "Test User", "email": "t@test.be", "phone": "+32123456"}],
            TENANT_ID,
        )
        assert len(records) == 1
        assert records[0].target_table == "contacts"

    def test_detect_case(self):
        importer = CSVImporter()
        records = importer.parse(
            [{"reference": "DOS-001", "title": "Test Case"}],
            TENANT_ID,
        )
        assert len(records) == 1
        assert records[0].target_table == "cases"


# ── API endpoint tests ──


class TestMigrationEndpoints:
    def setup_method(self):
        reset_store()

    def test_create_job_endpoint(self):
        client = TestClient(app)
        r = client.post(
            "/api/v1/migration/jobs",
            json={"source_system": "csv"},
            headers=_auth_headers(),
        )
        assert r.status_code == 201
        data = r.json()
        assert data["source_system"] == "csv"
        assert data["status"] == "pending"

    def test_create_job_invalid_source(self):
        client = TestClient(app)
        r = client.post(
            "/api/v1/migration/jobs",
            json={"source_system": "invalid"},
            headers=_auth_headers(),
        )
        assert r.status_code == 422

    def test_list_jobs_endpoint(self):
        client = TestClient(app)
        client.post("/api/v1/migration/jobs", json={"source_system": "csv"}, headers=_auth_headers())
        r = client.get("/api/v1/migration/jobs", headers=_auth_headers())
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    def test_preview_endpoint(self):
        client = TestClient(app)
        create_r = client.post("/api/v1/migration/jobs", json={"source_system": "csv"}, headers=_auth_headers())
        job_id = create_r.json()["id"]

        r = client.post(
            f"/api/v1/migration/jobs/{job_id}/preview",
            json={"data": [{"reference": "X", "title": "Y", "_type": "case"}]},
            headers=_auth_headers(),
        )
        assert r.status_code == 200
        assert r.json()["total_records"] == 1

    def test_full_flow(self):
        client = TestClient(app)
        # Create
        cr = client.post("/api/v1/migration/jobs", json={"source_system": "forlex"}, headers=_auth_headers())
        job_id = cr.json()["id"]

        # Preview
        pr = client.post(
            f"/api/v1/migration/jobs/{job_id}/preview",
            json={"data": [
                {"numero_dossier": "FL-001", "titre": "Test", "_type": "case"},
                {"numero_dossier": "FL-002", "titre": "Test2", "_type": "case"},
            ]},
            headers=_auth_headers(),
        )
        assert pr.status_code == 200

        # Start
        sr = client.post(f"/api/v1/migration/jobs/{job_id}/start", headers=_auth_headers())
        assert sr.status_code == 200
        assert sr.json()["status"] == "completed"
        assert sr.json()["imported_records"] == 2

        # Rollback
        rr = client.post(f"/api/v1/migration/jobs/{job_id}/rollback", headers=_auth_headers())
        assert rr.status_code == 200
        assert rr.json()["status"] == "pending"

    def test_job_not_found(self):
        client = TestClient(app)
        r = client.get(f"/api/v1/migration/jobs/{uuid.uuid4()}", headers=_auth_headers())
        assert r.status_code == 404

    def test_requires_auth(self):
        client = TestClient(app)
        r = client.post("/api/v1/migration/jobs", json={"source_system": "csv"})
        assert r.status_code == 401
