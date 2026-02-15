"""Invoices router — CRUD + Peppol + payment.

GET    /api/v1/invoices                      — list (filters: status, case)
POST   /api/v1/invoices                      — create (auto-valorise from time entries)
GET    /api/v1/invoices/{id}                 — get with lines
POST   /api/v1/invoices/{id}/generate-peppol — generate UBL 2.1 XML
POST   /api/v1/invoices/{id}/send            — send via Peppol (stub)
POST   /api/v1/invoices/{id}/mark-paid       — mark as paid
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_current_tenant, get_db_session
from apps.api.schemas.billing import (
    InvoiceCreate,
    InvoiceLineResponse,
    InvoiceListResponse,
    InvoiceResponse,
)
from apps.api.services import invoice_service

router = APIRouter(prefix="/api/v1/invoices", tags=["invoices"])


@router.get("", response_model=InvoiceListResponse)
async def list_invoices(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    case_id: Optional[uuid.UUID] = Query(None),
    session: AsyncSession = Depends(get_db_session),
) -> InvoiceListResponse:
    items, total = await invoice_service.list_invoices(
        session,
        page=page,
        per_page=per_page,
        status=status_filter,
        case_id=case_id,
    )
    return InvoiceListResponse(
        items=[InvoiceResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.post("", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    body: InvoiceCreate,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db_session),
) -> InvoiceResponse:
    lines_data = [l.model_dump() for l in body.lines] if body.lines else None
    inv = await invoice_service.create_invoice(
        session,
        tenant_id,
        invoice_number=body.invoice_number,
        client_contact_id=body.client_contact_id,
        due_date=body.due_date,
        case_id=body.case_id,
        issue_date=body.issue_date,
        vat_rate=body.vat_rate,
        currency=body.currency,
        notes=body.notes,
        lines=lines_data,
        time_entry_ids=body.time_entry_ids or None,
    )
    inv_lines = await invoice_service.get_invoice_lines(session, inv.id)
    resp = InvoiceResponse.model_validate(inv)
    resp.lines = [InvoiceLineResponse.model_validate(l) for l in inv_lines]
    return resp


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> InvoiceResponse:
    inv = await invoice_service.get_invoice(session, invoice_id)
    if inv is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    inv_lines = await invoice_service.get_invoice_lines(session, invoice_id)
    resp = InvoiceResponse.model_validate(inv)
    resp.lines = [InvoiceLineResponse.model_validate(l) for l in inv_lines]
    return resp


@router.post("/{invoice_id}/generate-peppol", response_model=InvoiceResponse)
async def generate_peppol(
    invoice_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> InvoiceResponse:
    inv = await invoice_service.generate_peppol_for_invoice(session, invoice_id)
    if inv is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return InvoiceResponse.model_validate(inv)


@router.post("/{invoice_id}/send", response_model=InvoiceResponse)
async def send_peppol(
    invoice_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> InvoiceResponse:
    inv = await invoice_service.send_peppol(session, invoice_id)
    if inv is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if inv.peppol_status == "generated":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invoice must be generated before sending",
        )
    return InvoiceResponse.model_validate(inv)


@router.post("/{invoice_id}/mark-paid", response_model=InvoiceResponse)
async def mark_paid(
    invoice_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> InvoiceResponse:
    inv = await invoice_service.mark_paid(session, invoice_id)
    if inv is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return InvoiceResponse.model_validate(inv)
