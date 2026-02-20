"""Tests for Invoices router — CRUD, generate-peppol, send, mark-paid."""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.auth.jwt import create_access_token
from apps.api.main import app

# -- Test data --

TENANT_A = uuid.uuid4()
TENANT_B = uuid.uuid4()
USER_A = uuid.uuid4()
USER_B = uuid.uuid4()
INVOICE_ID = uuid.uuid4()
CASE_ID = uuid.uuid4()
CONTACT_ID = uuid.uuid4()
LINE_ID = uuid.uuid4()

TOKEN_A = create_access_token(USER_A, TENANT_A, "partner", "alice@alpha.be")
TOKEN_B = create_access_token(USER_B, TENANT_B, "partner", "bob@beta.be")

NOW = datetime(2026, 2, 15, 12, 0, 0, tzinfo=timezone.utc)


def _make_invoice_obj(**overrides):
    """Create a mock Invoice object compatible with InvoiceResponse.model_validate."""
    defaults = {
        "id": INVOICE_ID,
        "tenant_id": TENANT_A,
        "case_id": CASE_ID,
        "invoice_number": "2026/F001",
        "client_contact_id": CONTACT_ID,
        "status": "draft",
        "issue_date": date(2026, 2, 15),
        "due_date": date(2026, 3, 15),
        "subtotal_cents": 100000,
        "vat_rate": Decimal("21.00"),
        "vat_amount_cents": 21000,
        "total_cents": 121000,
        "peppol_status": "none",
        "currency": "EUR",
        "notes": None,
        "created_at": NOW,
        "updated_at": NOW,
    }
    defaults.update(overrides)

    class MockInvoice:
        pass

    obj = MockInvoice()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _make_invoice_line_obj(**overrides):
    """Create a mock InvoiceLine object."""
    defaults = {
        "id": LINE_ID,
        "tenant_id": TENANT_A,
        "invoice_id": INVOICE_ID,
        "description": "Consultation juridique - 2h",
        "quantity": Decimal("2.0"),
        "unit_price_cents": 50000,
        "total_cents": 100000,
        "time_entry_id": None,
        "sort_order": 0,
    }
    defaults.update(overrides)

    class MockLine:
        pass

    obj = MockLine()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _patch_db():
    mock_session = AsyncMock()

    async def override_db(tenant_id=None):
        yield mock_session

    return mock_session, override_db


# -- Tests: GET /invoices --


@pytest.mark.asyncio
async def test_list_invoices():
    """GET /api/v1/invoices returns paginated invoices."""
    mock_session, override_db = _patch_db()
    inv = _make_invoice_obj()

    with patch("apps.api.routers.invoices.invoice_service") as mock_svc:
        mock_svc.list_invoices = AsyncMock(return_value=([inv], 1))

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/v1/invoices?page=1&per_page=20",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["invoice_number"] == "2026/F001"
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_list_invoices_empty():
    """GET /api/v1/invoices returns empty list."""
    mock_session, override_db = _patch_db()

    with patch("apps.api.routers.invoices.invoice_service") as mock_svc:
        mock_svc.list_invoices = AsyncMock(return_value=([], 0))

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/v1/invoices",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    assert resp.json()["total"] == 0
    assert resp.json()["items"] == []


@pytest.mark.asyncio
async def test_list_invoices_with_status_filter():
    """GET /api/v1/invoices?status=draft passes filter to service."""
    mock_session, override_db = _patch_db()

    with patch("apps.api.routers.invoices.invoice_service") as mock_svc:
        mock_svc.list_invoices = AsyncMock(return_value=([], 0))

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/v1/invoices?status=draft",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    call_kwargs = mock_svc.list_invoices.call_args
    assert call_kwargs.kwargs.get("status") == "draft"


# -- Tests: POST /invoices --


@pytest.mark.asyncio
async def test_create_invoice():
    """POST /api/v1/invoices creates a new invoice."""
    mock_session, override_db = _patch_db()
    inv = _make_invoice_obj()
    line = _make_invoice_line_obj()

    with patch("apps.api.routers.invoices.invoice_service") as mock_svc:
        mock_svc.create_invoice = AsyncMock(return_value=inv)
        mock_svc.get_invoice_lines = AsyncMock(return_value=[line])

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/invoices",
                json={
                    "invoice_number": "2026/F001",
                    "client_contact_id": str(CONTACT_ID),
                    "due_date": "2026-03-15",
                    "case_id": str(CASE_ID),
                    "lines": [
                        {
                            "description": "Consultation juridique - 2h",
                            "quantity": "2.0",
                            "unit_price_cents": 50000,
                        }
                    ],
                },
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 201
    data = resp.json()
    assert data["invoice_number"] == "2026/F001"
    assert data["status"] == "draft"
    assert len(data["lines"]) == 1


@pytest.mark.asyncio
async def test_create_invoice_validation_error():
    """POST /api/v1/invoices with missing fields returns 422."""
    mock_session, override_db = _patch_db()

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/v1/invoices",
            json={"notes": "Missing required fields"},
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 422


# -- Tests: GET /invoices/{id} --


@pytest.mark.asyncio
async def test_get_invoice():
    """GET /api/v1/invoices/{id} returns invoice with lines."""
    mock_session, override_db = _patch_db()
    inv = _make_invoice_obj()
    line = _make_invoice_line_obj()

    with patch("apps.api.routers.invoices.invoice_service") as mock_svc:
        mock_svc.get_invoice = AsyncMock(return_value=inv)
        mock_svc.get_invoice_lines = AsyncMock(return_value=[line])

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                f"/api/v1/invoices/{INVOICE_ID}",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(INVOICE_ID)
    assert len(data["lines"]) == 1


@pytest.mark.asyncio
async def test_get_invoice_not_found():
    """GET /api/v1/invoices/{id} returns 404 for unknown invoice."""
    mock_session, override_db = _patch_db()

    with patch("apps.api.routers.invoices.invoice_service") as mock_svc:
        mock_svc.get_invoice = AsyncMock(return_value=None)

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                f"/api/v1/invoices/{uuid.uuid4()}",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 404


# -- Tests: PATCH /invoices/{id} --


@pytest.mark.asyncio
async def test_update_invoice():
    """PATCH /api/v1/invoices/{id} updates a draft invoice."""
    mock_session, override_db = _patch_db()
    inv = _make_invoice_obj()
    updated_inv = _make_invoice_obj(notes="Updated notes")

    with patch("apps.api.routers.invoices.invoice_service") as mock_svc:
        mock_svc.get_invoice = AsyncMock(return_value=inv)
        mock_svc.update_invoice = AsyncMock(return_value=updated_inv)

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.patch(
                f"/api/v1/invoices/{INVOICE_ID}",
                json={
                    "invoice_number": "2026/F001",
                    "client_contact_id": str(CONTACT_ID),
                    "due_date": "2026-03-15",
                    "notes": "Updated notes",
                },
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    assert resp.json()["notes"] == "Updated notes"


@pytest.mark.asyncio
async def test_update_invoice_not_draft():
    """PATCH /api/v1/invoices/{id} returns 409 for non-draft invoice."""
    mock_session, override_db = _patch_db()
    inv = _make_invoice_obj(status="sent")

    with patch("apps.api.routers.invoices.invoice_service") as mock_svc:
        mock_svc.get_invoice = AsyncMock(return_value=inv)

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.patch(
                f"/api/v1/invoices/{INVOICE_ID}",
                json={
                    "invoice_number": "2026/F001",
                    "client_contact_id": str(CONTACT_ID),
                    "due_date": "2026-03-15",
                    "notes": "Try update",
                },
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_update_invoice_not_found():
    """PATCH /api/v1/invoices/{id} returns 404 for unknown invoice."""
    mock_session, override_db = _patch_db()

    with patch("apps.api.routers.invoices.invoice_service") as mock_svc:
        mock_svc.get_invoice = AsyncMock(return_value=None)

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.patch(
                f"/api/v1/invoices/{uuid.uuid4()}",
                json={
                    "invoice_number": "2026/F001",
                    "client_contact_id": str(CONTACT_ID),
                    "due_date": "2026-03-15",
                },
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 404


# -- Tests: DELETE /invoices/{id} --


@pytest.mark.asyncio
async def test_cancel_invoice():
    """DELETE /api/v1/invoices/{id} cancels (soft-deletes) an invoice."""
    mock_session, override_db = _patch_db()
    inv = _make_invoice_obj(status="cancelled")

    with patch("apps.api.routers.invoices.invoice_service") as mock_svc:
        mock_svc.cancel_invoice = AsyncMock(return_value=inv)

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.delete(
                f"/api/v1/invoices/{INVOICE_ID}",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_cancel_invoice_not_found():
    """DELETE /api/v1/invoices/{id} returns 404 for unknown invoice."""
    mock_session, override_db = _patch_db()

    with patch("apps.api.routers.invoices.invoice_service") as mock_svc:
        mock_svc.cancel_invoice = AsyncMock(return_value=None)

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.delete(
                f"/api/v1/invoices/{uuid.uuid4()}",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 404


# -- Tests: POST /invoices/{id}/generate-peppol --


@pytest.mark.asyncio
async def test_generate_peppol():
    """POST /api/v1/invoices/{id}/generate-peppol generates UBL XML."""
    mock_session, override_db = _patch_db()
    inv = _make_invoice_obj(peppol_status="generated")

    with patch("apps.api.routers.invoices.invoice_service") as mock_svc:
        mock_svc.generate_peppol_for_invoice = AsyncMock(return_value=inv)

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/v1/invoices/{INVOICE_ID}/generate-peppol",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    assert resp.json()["peppol_status"] == "generated"


@pytest.mark.asyncio
async def test_generate_peppol_not_found():
    """POST /api/v1/invoices/{id}/generate-peppol returns 404."""
    mock_session, override_db = _patch_db()

    with patch("apps.api.routers.invoices.invoice_service") as mock_svc:
        mock_svc.generate_peppol_for_invoice = AsyncMock(return_value=None)

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/v1/invoices/{uuid.uuid4()}/generate-peppol",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 404


# -- Tests: POST /invoices/{id}/send --


@pytest.mark.asyncio
async def test_send_peppol():
    """POST /api/v1/invoices/{id}/send sends invoice via Peppol."""
    mock_session, override_db = _patch_db()
    inv = _make_invoice_obj(peppol_status="sent")

    with patch("apps.api.routers.invoices.invoice_service") as mock_svc:
        mock_svc.send_peppol = AsyncMock(return_value=inv)

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/v1/invoices/{INVOICE_ID}/send",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    assert resp.json()["peppol_status"] == "sent"


@pytest.mark.asyncio
async def test_send_peppol_not_found():
    """POST /api/v1/invoices/{id}/send returns 404 for unknown invoice."""
    mock_session, override_db = _patch_db()

    with patch("apps.api.routers.invoices.invoice_service") as mock_svc:
        mock_svc.send_peppol = AsyncMock(return_value=None)

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/v1/invoices/{uuid.uuid4()}/send",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_send_peppol_not_generated():
    """POST /api/v1/invoices/{id}/send returns 409 if not yet generated."""
    mock_session, override_db = _patch_db()
    inv = _make_invoice_obj(peppol_status="generated")

    with patch("apps.api.routers.invoices.invoice_service") as mock_svc:
        mock_svc.send_peppol = AsyncMock(return_value=inv)

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/v1/invoices/{INVOICE_ID}/send",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 409


# -- Tests: POST /invoices/{id}/mark-paid --


@pytest.mark.asyncio
async def test_mark_paid():
    """POST /api/v1/invoices/{id}/mark-paid marks invoice as paid."""
    mock_session, override_db = _patch_db()
    inv = _make_invoice_obj(status="paid")

    with patch("apps.api.routers.invoices.invoice_service") as mock_svc:
        mock_svc.mark_paid = AsyncMock(return_value=inv)

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/v1/invoices/{INVOICE_ID}/mark-paid",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    assert resp.json()["status"] == "paid"


@pytest.mark.asyncio
async def test_mark_paid_not_found():
    """POST /api/v1/invoices/{id}/mark-paid returns 404."""
    mock_session, override_db = _patch_db()

    with patch("apps.api.routers.invoices.invoice_service") as mock_svc:
        mock_svc.mark_paid = AsyncMock(return_value=None)

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/v1/invoices/{uuid.uuid4()}/mark-paid",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 404
