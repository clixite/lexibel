"""Tests for LXB-044-045: DPA e-Deposit + JBox integration."""
import uuid

import pytest
from fastapi.testclient import TestClient

from apps.api.services.dpa_service import (
    submit_deposit,
    check_deposit_status,
    poll_jbox,
    get_jbox_messages,
    acknowledge_jbox,
    reset_store,
    VALID_COURT_CODES,
)
from apps.api.services.outlook_service import (
    extract_references,
    match_email_to_case,
    send_email as outlook_send,
    create_draft,
    reset_store as reset_outlook,
)
from apps.api.main import app


TENANT_ID = str(uuid.uuid4())
USER_ID = str(uuid.uuid4())


def _auth_headers() -> dict:
    return {
        "X-Tenant-ID": TENANT_ID,
        "X-User-ID": USER_ID,
        "X-User-Role": "super_admin",
        "X-User-Email": "test@lexibel.be",
    }


# ── DPA Service unit tests ──


class TestDPAService:
    def setup_method(self):
        reset_store()

    @pytest.mark.asyncio
    async def test_submit_deposit(self):
        result = await submit_deposit(
            tenant_id=TENANT_ID,
            case_id="case-1",
            documents=[{"file_name": "conclusions.pdf", "content_type": "application/pdf"}],
            court_code="BXL",
            case_reference="2026/001/A",
        )
        assert result.status == "submitted"
        assert result.court_code == "BXL"
        assert result.documents_count == 1
        assert result.case_reference == "2026/001/A"

    @pytest.mark.asyncio
    async def test_submit_deposit_invalid_court(self):
        with pytest.raises(ValueError, match="Invalid court_code"):
            await submit_deposit(
                tenant_id=TENANT_ID,
                case_id="case-1",
                documents=[{"file_name": "doc.pdf"}],
                court_code="INVALID",
            )

    @pytest.mark.asyncio
    async def test_submit_deposit_no_documents(self):
        with pytest.raises(ValueError, match="At least one document"):
            await submit_deposit(
                tenant_id=TENANT_ID,
                case_id="case-1",
                documents=[],
                court_code="BXL",
            )

    @pytest.mark.asyncio
    async def test_check_deposit_status(self):
        result = await submit_deposit(
            tenant_id=TENANT_ID,
            case_id="case-1",
            documents=[{"file_name": "conclusions.pdf"}],
            court_code="ANT",
        )
        status = await check_deposit_status(result.deposit_id)
        assert status.deposit_id == result.deposit_id
        assert status.status == "submitted"
        assert status.court_code == "ANT"

    @pytest.mark.asyncio
    async def test_check_deposit_status_not_found(self):
        with pytest.raises(ValueError, match="not found"):
            await check_deposit_status("nonexistent-id")

    @pytest.mark.asyncio
    async def test_poll_jbox(self):
        messages = await poll_jbox(TENANT_ID)
        assert len(messages) >= 1
        assert messages[0].sender  # Not empty
        assert messages[0].subject

    @pytest.mark.asyncio
    async def test_poll_jbox_with_since(self):
        messages = await poll_jbox(TENANT_ID, since="2026-02-16T00:00:00Z")
        # All messages should be before this date in the seed data
        assert isinstance(messages, list)

    @pytest.mark.asyncio
    async def test_get_jbox_messages(self):
        messages = await get_jbox_messages(TENANT_ID)
        assert len(messages) >= 2  # Seeded messages

    @pytest.mark.asyncio
    async def test_acknowledge_jbox(self):
        messages = await poll_jbox(TENANT_ID)
        assert len(messages) > 0

        msg = messages[0]
        ack = await acknowledge_jbox(msg.message_id, TENANT_ID)
        assert ack.acknowledged is True

        # Second ack should fail
        with pytest.raises(ValueError, match="already acknowledged"):
            await acknowledge_jbox(msg.message_id, TENANT_ID)

    @pytest.mark.asyncio
    async def test_acknowledge_jbox_not_found(self):
        with pytest.raises(ValueError, match="not found"):
            await acknowledge_jbox("nonexistent-id", TENANT_ID)

    def test_valid_court_codes(self):
        assert "BXL" in VALID_COURT_CODES
        assert "ANT" in VALID_COURT_CODES
        assert "CC_FR" in VALID_COURT_CODES
        assert len(VALID_COURT_CODES) >= 10


# ── Outlook Service unit tests ──


class TestOutlookService:
    def setup_method(self):
        reset_outlook()

    def test_extract_references(self):
        refs = extract_references("Dossier 42 et RG 2026/123 concernant DOS-001")
        assert "Dossier 42" in refs
        assert "RG 2026/123" in refs
        assert "DOS-001" in refs

    def test_extract_references_court_format(self):
        refs = extract_references("Affaire 2026/001/A")
        assert "2026/001/A" in refs

    def test_match_email_to_case(self):
        cases = [
            {"reference": "2026/001/A", "title": "Test Case"},
            {"reference": "2025/002/B", "title": "Other Case"},
        ]
        match = match_email_to_case(
            subject="RE: Dossier 2026/001/A",
            body_preview="Veuillez trouver ci-joint",
            sender="avocat@test.be",
            existing_cases=cases,
        )
        assert match is not None
        assert match["reference"] == "2026/001/A"

    def test_match_email_no_match(self):
        match = match_email_to_case(
            subject="Hello",
            body_preview="No case reference here",
            sender="test@test.be",
            existing_cases=[{"reference": "2026/001", "title": "T"}],
        )
        assert match is None

    @pytest.mark.asyncio
    async def test_send_email(self):
        result = await outlook_send(
            tenant_id=TENANT_ID,
            to=["recipient@test.be"],
            subject="Test",
            body_text="Hello",
        )
        assert result["status"] == "sent"
        assert result["message_id"]

    @pytest.mark.asyncio
    async def test_send_email_no_recipient(self):
        with pytest.raises(ValueError, match="At least one recipient"):
            await outlook_send(
                tenant_id=TENANT_ID,
                to=[],
                subject="Test",
                body_text="Hello",
            )

    @pytest.mark.asyncio
    async def test_create_draft(self):
        draft = await create_draft(
            tenant_id=TENANT_ID,
            to=["test@test.be"],
            subject="Draft",
            body="Body",
        )
        assert draft["status"] == "draft"
        assert draft["message_id"]


# ── DPA API endpoint tests ──


class TestDPAEndpoints:
    def setup_method(self):
        reset_store()

    def test_submit_deposit_endpoint(self):
        client = TestClient(app)
        r = client.post(
            "/api/v1/dpa/deposit",
            json={
                "case_id": "case-1",
                "court_code": "BXL",
                "case_reference": "2026/001",
                "documents": [{"file_name": "conclusions.pdf"}],
            },
            headers=_auth_headers(),
        )
        assert r.status_code == 201
        data = r.json()
        assert data["status"] == "submitted"
        assert data["court_code"] == "BXL"

    def test_submit_deposit_invalid_court(self):
        client = TestClient(app)
        r = client.post(
            "/api/v1/dpa/deposit",
            json={
                "case_id": "case-1",
                "court_code": "INVALID",
                "documents": [{"file_name": "doc.pdf"}],
            },
            headers=_auth_headers(),
        )
        assert r.status_code == 422

    def test_deposit_status_endpoint(self):
        client = TestClient(app)
        # Submit first
        cr = client.post(
            "/api/v1/dpa/deposit",
            json={
                "case_id": "case-1",
                "court_code": "ANT",
                "documents": [{"file_name": "doc.pdf"}],
            },
            headers=_auth_headers(),
        )
        deposit_id = cr.json()["deposit_id"]

        # Check status
        r = client.get(
            f"/api/v1/dpa/deposit/{deposit_id}/status",
            headers=_auth_headers(),
        )
        assert r.status_code == 200
        assert r.json()["status"] == "submitted"

    def test_jbox_poll_endpoint(self):
        client = TestClient(app)
        r = client.post(
            "/api/v1/dpa/jbox/poll",
            json={},
            headers=_auth_headers(),
        )
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    def test_jbox_messages_endpoint(self):
        client = TestClient(app)
        r = client.get(
            "/api/v1/dpa/jbox/messages",
            headers=_auth_headers(),
        )
        assert r.status_code == 200
        assert r.json()["total"] >= 2

    def test_jbox_acknowledge_endpoint(self):
        client = TestClient(app)
        # Poll to get messages
        poll_r = client.post(
            "/api/v1/dpa/jbox/poll",
            json={},
            headers=_auth_headers(),
        )
        messages = poll_r.json()["messages"]
        assert len(messages) > 0

        # Acknowledge first message
        msg_id = messages[0]["message_id"]
        r = client.post(
            f"/api/v1/dpa/jbox/{msg_id}/acknowledge",
            headers=_auth_headers(),
        )
        assert r.status_code == 200
        assert r.json()["acknowledged"] is True

    def test_requires_auth(self):
        client = TestClient(app)
        r = client.post("/api/v1/dpa/deposit", json={})
        assert r.status_code == 401


# ── Outlook API endpoint tests ──


class TestOutlookEndpoints:
    def setup_method(self):
        reset_outlook()

    def test_sync_endpoint(self):
        client = TestClient(app)
        r = client.post(
            "/api/v1/outlook/sync",
            json={"user_id": "user@test.be"},
            headers=_auth_headers(),
        )
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_emails_list_endpoint(self):
        client = TestClient(app)
        r = client.get(
            "/api/v1/outlook/emails",
            headers=_auth_headers(),
        )
        assert r.status_code == 200
        assert "emails" in r.json()

    def test_send_endpoint(self):
        client = TestClient(app)
        r = client.post(
            "/api/v1/outlook/send",
            json={
                "to": ["recipient@test.be"],
                "subject": "Test",
                "body": "Hello world",
            },
            headers=_auth_headers(),
        )
        assert r.status_code == 200
        assert r.json()["status"] == "sent"
