"""Tests for security: rate limiting, security headers, backup, audit export."""
import uuid

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.middleware.rate_limit import reset_rate_store, _rate_store, ROLE_LIMITS
from apps.api.services.backup_service import BackupService
from apps.api.services.audit_export_service import AuditExportService, AuditEntry


TENANT_ID = str(uuid.uuid4())
USER_ID = str(uuid.uuid4())


def _auth_headers() -> dict:
    return {
        "X-Tenant-ID": TENANT_ID,
        "X-User-ID": USER_ID,
        "X-User-Role": "super_admin",
        "X-User-Email": "admin@lexibel.be",
    }


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def clean_rate_store():
    reset_rate_store()
    yield
    reset_rate_store()


# ── Security Headers ──


class TestSecurityHeaders:

    def test_x_content_type_options(self, client):
        resp = client.get("/api/v1/health")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options(self, client):
        resp = client.get("/api/v1/health")
        assert resp.headers.get("X-Frame-Options") == "DENY"

    def test_strict_transport_security(self, client):
        resp = client.get("/api/v1/health")
        assert "max-age" in resp.headers.get("Strict-Transport-Security", "")

    def test_content_security_policy(self, client):
        resp = client.get("/api/v1/health")
        csp = resp.headers.get("Content-Security-Policy", "")
        assert "default-src" in csp
        assert "frame-ancestors 'none'" in csp

    def test_x_request_id(self, client):
        resp = client.get("/api/v1/health")
        assert resp.headers.get("X-Request-ID") is not None
        # Validate UUID format
        uuid.UUID(resp.headers["X-Request-ID"])

    def test_x_request_id_forwarded(self, client):
        custom_id = str(uuid.uuid4())
        resp = client.get("/api/v1/health", headers={"X-Request-ID": custom_id})
        assert resp.headers.get("X-Request-ID") == custom_id

    def test_referrer_policy(self, client):
        resp = client.get("/api/v1/health")
        assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


# ── Rate Limiting ──


class TestRateLimiting:

    def test_rate_limit_headers_present(self, client):
        resp = client.get("/api/v1/admin/health", headers=_auth_headers())
        assert "X-RateLimit-Limit" in resp.headers
        assert "X-RateLimit-Remaining" in resp.headers

    def test_rate_limit_decreases(self, client):
        resp1 = client.get("/api/v1/admin/health", headers=_auth_headers())
        remaining1 = int(resp1.headers["X-RateLimit-Remaining"])

        resp2 = client.get("/api/v1/admin/health", headers=_auth_headers())
        remaining2 = int(resp2.headers["X-RateLimit-Remaining"])

        assert remaining2 < remaining1

    def test_health_exempt_from_rate_limit(self, client):
        # Health endpoint should not have rate limit headers
        # (it's in _EXEMPT_PATHS)
        resp = client.get("/api/v1/health")
        # Public health endpoint is exempt
        assert "X-RateLimit-Limit" not in resp.headers

    def test_role_based_limits(self):
        assert ROLE_LIMITS["super_admin"] > ROLE_LIMITS["junior"]
        assert ROLE_LIMITS["lawyer"] >= ROLE_LIMITS["secretary"]


# ── Backup Service ──


class TestBackupService:

    def setup_method(self):
        self.service = BackupService()

    def test_create_backup(self):
        backup = self.service.create_backup()
        assert backup.status == "completed"
        assert backup.retention_type == "daily"
        assert "lexibel_backup_" in backup.filename

    def test_create_weekly_backup(self):
        backup = self.service.create_backup(retention_type="weekly")
        assert backup.retention_type == "weekly"

    def test_list_backups(self):
        self.service.create_backup()
        self.service.create_backup(retention_type="weekly")
        all_backups = self.service.list_backups()
        assert len(all_backups) == 2

    def test_list_backups_filtered(self):
        self.service.create_backup()
        self.service.create_backup(retention_type="weekly")
        daily = self.service.list_backups(retention_type="daily")
        assert len(daily) == 1

    def test_get_backup(self):
        backup = self.service.create_backup()
        found = self.service.get_backup(backup.id)
        assert found is not None
        assert found.id == backup.id

    def test_get_nonexistent_backup(self):
        assert self.service.get_backup("nonexistent") is None

    def test_restore_backup(self):
        backup = self.service.create_backup()
        result = self.service.restore_backup(backup.id)
        assert result["status"] == "restore_initiated"

    def test_restore_nonexistent_backup(self):
        result = self.service.restore_backup("nonexistent")
        assert result["status"] == "error"

    def test_retention_policy(self):
        # Create some backups
        for _ in range(5):
            self.service.create_backup()
        result = self.service.apply_retention_policy()
        assert "removed" in result
        assert "remaining" in result


# ── Audit Export Service ──


class TestAuditExportService:

    def setup_method(self):
        self.service = AuditExportService()
        # Add sample entries
        for i in range(5):
            self.service.add_entry(AuditEntry(
                id=str(uuid.uuid4()),
                tenant_id=TENANT_ID,
                user_id=USER_ID,
                user_email="admin@lexibel.be",
                action="GET" if i % 2 == 0 else "POST",
                resource_type="api_request",
                resource_id=f"/api/v1/cases/{i}",
                timestamp=f"2026-02-{10 + i:02d}T10:00:00+00:00",
            ))

    def test_export_json(self):
        result = self.service.export(TENANT_ID, format="json")
        assert result.format == "json"
        assert result.record_count == 5
        assert '"action"' in result.content

    def test_export_csv(self):
        result = self.service.export(TENANT_ID, format="csv")
        assert result.format == "csv"
        assert result.record_count == 5
        assert "id,tenant_id" in result.content

    def test_export_filter_by_action(self):
        result = self.service.export(TENANT_ID, action_type="GET")
        assert result.record_count == 3  # indices 0, 2, 4

    def test_export_filter_by_date_range(self):
        result = self.service.export(
            TENANT_ID,
            date_from="2026-02-12T00:00:00+00:00",
            date_to="2026-02-14T23:59:59+00:00",
        )
        assert result.record_count == 3  # indices 2, 3, 4

    def test_export_filter_by_user(self):
        # Add entry for different user
        self.service.add_entry(AuditEntry(
            id=str(uuid.uuid4()),
            tenant_id=TENANT_ID,
            user_id="other-user",
            user_email="other@test.be",
            action="GET",
            resource_type="api_request",
            resource_id="/api/v1/health",
            timestamp="2026-02-10T10:00:00+00:00",
        ))
        result = self.service.export(TENANT_ID, user_id=USER_ID)
        assert result.record_count == 5  # only original user

    def test_export_anonymized(self):
        result = self.service.export(TENANT_ID, anonymize=True)
        assert result.anonymized is True
        assert result.record_count == 5
        # Email should be hashed
        assert "admin@lexibel.be" not in result.content
        assert "@anonymized" in result.content

    def test_export_wrong_tenant(self):
        result = self.service.export("other-tenant-id")
        assert result.record_count == 0

    def test_export_empty_with_date_filter(self):
        result = self.service.export(TENANT_ID, date_from="2027-01-01T00:00:00+00:00")
        assert result.record_count == 0
