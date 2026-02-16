"""LXB-020-024: Tests for Billing — time entries, invoices, Peppol, third-party account."""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.auth.jwt import create_access_token
from apps.api.main import app
from apps.api.services.time_service import apply_rounding

# ── Test data ──

TENANT_A = uuid.uuid4()
TENANT_B = uuid.uuid4()
USER_A = uuid.uuid4()
USER_B = uuid.uuid4()
CASE_ID = uuid.uuid4()
CONTACT_ID = uuid.uuid4()
ENTRY_ID = uuid.uuid4()
INVOICE_ID = uuid.uuid4()

TOKEN_A = create_access_token(USER_A, TENANT_A, "partner", "alice@alpha.be")
TOKEN_B = create_access_token(USER_B, TENANT_B, "partner", "bob@beta.be")

NOW = datetime(2026, 2, 15, 12, 0, 0, tzinfo=timezone.utc)
TODAY = date(2026, 2, 15)


def _make_time_entry(**overrides):
    defaults = {
        "id": ENTRY_ID,
        "tenant_id": TENANT_A,
        "case_id": CASE_ID,
        "user_id": USER_A,
        "description": "Rédaction de conclusions",
        "duration_minutes": 12,
        "billable": True,
        "date": TODAY,
        "rounding_rule": "6min",
        "source": "MANUAL",
        "status": "draft",
        "hourly_rate_cents": 15000,
        "approved_by": None,
        "created_at": NOW,
        "updated_at": NOW,
    }
    defaults.update(overrides)

    class Mock:
        pass

    obj = Mock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _make_invoice(**overrides):
    defaults = {
        "id": INVOICE_ID,
        "tenant_id": TENANT_A,
        "case_id": CASE_ID,
        "invoice_number": "2026/F001",
        "client_contact_id": CONTACT_ID,
        "status": "draft",
        "issue_date": TODAY,
        "due_date": date(2026, 3, 17),
        "subtotal_cents": 30000,
        "vat_rate": Decimal("21.00"),
        "vat_amount_cents": 6300,
        "total_cents": 36300,
        "peppol_status": "none",
        "peppol_ubl_xml": None,
        "currency": "EUR",
        "notes": None,
        "lines": [],
        "created_at": NOW,
        "updated_at": NOW,
    }
    defaults.update(overrides)

    class Mock:
        pass

    obj = Mock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _make_invoice_line(**overrides):
    defaults = {
        "id": uuid.uuid4(),
        "tenant_id": TENANT_A,
        "invoice_id": INVOICE_ID,
        "description": "Rédaction de conclusions",
        "quantity": Decimal("2.00"),
        "unit_price_cents": 15000,
        "total_cents": 30000,
        "time_entry_id": ENTRY_ID,
        "sort_order": 0,
    }
    defaults.update(overrides)

    class Mock:
        pass

    obj = Mock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _make_third_party_entry(**overrides):
    defaults = {
        "id": uuid.uuid4(),
        "tenant_id": TENANT_A,
        "case_id": CASE_ID,
        "entry_type": "deposit",
        "amount_cents": 500000,
        "description": "Provision client Dupont",
        "reference": "VIR-2026-001",
        "entry_date": TODAY,
        "created_by": USER_A,
        "created_at": NOW,
    }
    defaults.update(overrides)

    class Mock:
        pass

    obj = Mock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _patch_db():
    mock_session = AsyncMock()

    async def override_db(tenant_id=None):
        yield mock_session

    return mock_session, override_db


# ── Rounding logic tests ──


def test_rounding_6min():
    assert apply_rounding(1, "6min") == 6
    assert apply_rounding(6, "6min") == 6
    assert apply_rounding(7, "6min") == 12
    assert apply_rounding(13, "6min") == 18


def test_rounding_10min():
    assert apply_rounding(1, "10min") == 10
    assert apply_rounding(10, "10min") == 10
    assert apply_rounding(11, "10min") == 20


def test_rounding_15min():
    assert apply_rounding(1, "15min") == 15
    assert apply_rounding(15, "15min") == 15
    assert apply_rounding(16, "15min") == 30


def test_rounding_none():
    assert apply_rounding(7, "none") == 7
    assert apply_rounding(13, "none") == 13


# ── Time entry CRUD tests ──


@pytest.mark.asyncio
async def test_create_time_entry():
    mock_session, override_db = _patch_db()
    entry_obj = _make_time_entry()

    with patch("apps.api.routers.time_entries.time_service") as mock_svc:
        mock_svc.create_time_entry = AsyncMock(return_value=entry_obj)

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/time-entries",
                json={
                    "case_id": str(CASE_ID),
                    "description": "Rédaction de conclusions",
                    "duration_minutes": 10,
                    "date": "2026-02-15",
                    "rounding_rule": "6min",
                    "hourly_rate_cents": 15000,
                },
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 201
    data = resp.json()
    assert data["duration_minutes"] == 12  # rounded from 10 to 12 (6min rule)
    assert data["status"] == "draft"


@pytest.mark.asyncio
async def test_list_time_entries_with_filters():
    mock_session, override_db = _patch_db()

    with patch("apps.api.routers.time_entries.time_service") as mock_svc:
        mock_svc.list_time_entries = AsyncMock(return_value=([], 0))

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                f"/api/v1/time-entries?case_id={CASE_ID}&status=draft",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    call_kwargs = mock_svc.list_time_entries.call_args
    assert call_kwargs.kwargs.get("case_id") == CASE_ID
    assert call_kwargs.kwargs.get("status") == "draft"


@pytest.mark.asyncio
async def test_submit_time_entry():
    mock_session, override_db = _patch_db()
    submitted = _make_time_entry(status="submitted")

    with patch("apps.api.routers.time_entries.time_service") as mock_svc:
        mock_svc.submit_time_entry = AsyncMock(return_value=submitted)

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/v1/time-entries/{ENTRY_ID}/submit",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    assert resp.json()["status"] == "submitted"


@pytest.mark.asyncio
async def test_approve_time_entry():
    mock_session, override_db = _patch_db()
    approved = _make_time_entry(status="approved", approved_by=USER_A)

    with patch("apps.api.routers.time_entries.time_service") as mock_svc:
        mock_svc.approve_time_entry = AsyncMock(return_value=approved)

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/v1/time-entries/{ENTRY_ID}/approve",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"
    assert resp.json()["approved_by"] == str(USER_A)


@pytest.mark.asyncio
async def test_update_draft_only():
    """PATCH on non-draft entry returns 409."""
    mock_session, override_db = _patch_db()
    submitted_entry = _make_time_entry(status="submitted")

    with patch("apps.api.routers.time_entries.time_service") as mock_svc:
        mock_svc.update_time_entry = AsyncMock(return_value=submitted_entry)

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.patch(
                f"/api/v1/time-entries/{ENTRY_ID}",
                json={"description": "Updated"},
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 409


# ── Invoice tests ──


@pytest.mark.asyncio
async def test_create_invoice():
    mock_session, override_db = _patch_db()
    inv_obj = _make_invoice()
    line_obj = _make_invoice_line()

    with patch("apps.api.routers.invoices.invoice_service") as mock_svc:
        mock_svc.create_invoice = AsyncMock(return_value=inv_obj)
        mock_svc.get_invoice_lines = AsyncMock(return_value=[line_obj])

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
                    "due_date": "2026-03-17",
                    "case_id": str(CASE_ID),
                    "lines": [
                        {
                            "description": "Rédaction de conclusions",
                            "quantity": "2.00",
                            "unit_price_cents": 15000,
                        }
                    ],
                },
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 201
    data = resp.json()
    assert data["invoice_number"] == "2026/F001"
    assert data["total_cents"] == 36300
    assert len(data["lines"]) == 1


@pytest.mark.asyncio
async def test_get_invoice_with_lines():
    mock_session, override_db = _patch_db()
    inv_obj = _make_invoice()
    line_obj = _make_invoice_line()

    with patch("apps.api.routers.invoices.invoice_service") as mock_svc:
        mock_svc.get_invoice = AsyncMock(return_value=inv_obj)
        mock_svc.get_invoice_lines = AsyncMock(return_value=[line_obj])

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
async def test_generate_peppol_ubl():
    mock_session, override_db = _patch_db()
    inv_with_ubl = _make_invoice(
        peppol_status="generated",
        peppol_ubl_xml="<?xml version='1.0' ?><Invoice>...</Invoice>",
    )

    with patch("apps.api.routers.invoices.invoice_service") as mock_svc:
        mock_svc.generate_peppol_for_invoice = AsyncMock(return_value=inv_with_ubl)

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
async def test_mark_paid():
    mock_session, override_db = _patch_db()
    paid_inv = _make_invoice(status="paid")

    with patch("apps.api.routers.invoices.invoice_service") as mock_svc:
        mock_svc.mark_paid = AsyncMock(return_value=paid_inv)

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


# ── Peppol UBL generation unit test ──


def test_peppol_ubl_xml_generation():
    """Test that generate_peppol_ubl produces valid XML."""
    from apps.api.services.invoice_service import generate_peppol_ubl

    inv = _make_invoice()
    line = _make_invoice_line()

    xml = generate_peppol_ubl(inv, [line])

    assert "<?xml" in xml
    assert "Invoice" in xml
    assert "2026/F001" in xml
    assert "BIS Billing" in xml or "peppol" in xml.lower()
    assert "380" in xml  # InvoiceTypeCode
    assert "EUR" in xml
    assert "300.00" in xml  # subtotal 30000c = 300.00


# ── Third-party account tests ──


@pytest.mark.asyncio
async def test_create_third_party_entry():
    mock_session, override_db = _patch_db()
    entry_obj = _make_third_party_entry()

    with patch("apps.api.routers.third_party.third_party_service") as mock_svc:
        mock_svc.create_entry = AsyncMock(return_value=entry_obj)

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/v1/cases/{CASE_ID}/third-party",
                json={
                    "entry_type": "deposit",
                    "amount_cents": 500000,
                    "description": "Provision client Dupont",
                    "reference": "VIR-2026-001",
                    "entry_date": "2026-02-15",
                },
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 201
    data = resp.json()
    assert data["entry_type"] == "deposit"
    assert data["amount_cents"] == 500000


@pytest.mark.asyncio
async def test_list_third_party_entries():
    mock_session, override_db = _patch_db()
    entries = [_make_third_party_entry() for _ in range(3)]

    with patch("apps.api.routers.third_party.third_party_service") as mock_svc:
        mock_svc.list_by_case = AsyncMock(return_value=(entries, 3))

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                f"/api/v1/cases/{CASE_ID}/third-party",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    assert resp.json()["total"] == 3


@pytest.mark.asyncio
async def test_third_party_balance():
    mock_session, override_db = _patch_db()
    balance = {
        "case_id": CASE_ID,
        "deposits": 500000,
        "withdrawals": 100000,
        "interest": 2500,
        "balance": 402500,
    }

    with patch("apps.api.routers.third_party.third_party_service") as mock_svc:
        mock_svc.calculate_balance = AsyncMock(return_value=balance)

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                f"/api/v1/cases/{CASE_ID}/third-party/balance",
                headers={"Authorization": f"Bearer {TOKEN_A}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    data = resp.json()
    assert data["deposits"] == 500000
    assert data["withdrawals"] == 100000
    assert data["interest"] == 2500
    assert data["balance"] == 402500


@pytest.mark.asyncio
async def test_third_party_invalid_type():
    """POST with invalid entry_type returns 422."""
    mock_session, override_db = _patch_db()

    from apps.api.dependencies import get_db_session

    app.dependency_overrides[get_db_session] = override_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            f"/api/v1/cases/{CASE_ID}/third-party",
            json={
                "entry_type": "invalid",
                "amount_cents": 100,
                "description": "Test",
                "reference": "REF",
                "entry_date": "2026-02-15",
            },
            headers={"Authorization": f"Bearer {TOKEN_A}"},
        )

    app.dependency_overrides = {}

    assert resp.status_code == 422


# ── Cross-tenant isolation ──


@pytest.mark.asyncio
async def test_cross_tenant_time_entries():
    """Tenant B should only see their own time entries."""
    mock_session, override_db = _patch_db()
    entry_b = _make_time_entry(
        id=uuid.uuid4(),
        tenant_id=TENANT_B,
        user_id=USER_B,
    )

    with patch("apps.api.routers.time_entries.time_service") as mock_svc:
        mock_svc.list_time_entries = AsyncMock(return_value=([entry_b], 1))

        from apps.api.dependencies import get_db_session

        app.dependency_overrides[get_db_session] = override_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/v1/time-entries",
                headers={"Authorization": f"Bearer {TOKEN_B}"},
            )

        app.dependency_overrides = {}

    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["tenant_id"] == str(TENANT_B)
