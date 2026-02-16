"""Pydantic schemas for Billing: Time Entries, Invoices, Third-Party Account."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


# ── Time Entries ──


class TimeEntryCreate(BaseModel):
    case_id: uuid.UUID
    description: str
    duration_minutes: int = Field(..., gt=0)
    billable: bool = True
    date: date
    rounding_rule: str = Field("6min", pattern="^(6min|10min|15min|none)$")
    source: str = Field(
        "MANUAL",
        pattern="^(MANUAL|TIMER|RINGOVER|PLAUD|OUTLOOK)$",
    )
    hourly_rate_cents: Optional[int] = None


class TimeEntryUpdate(BaseModel):
    description: Optional[str] = None
    duration_minutes: Optional[int] = Field(None, gt=0)
    billable: Optional[bool] = None
    date: Optional[date] = None
    rounding_rule: Optional[str] = Field(None, pattern="^(6min|10min|15min|none)$")
    hourly_rate_cents: Optional[int] = None


class TimeEntryResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    case_id: uuid.UUID
    user_id: uuid.UUID
    description: str
    duration_minutes: int
    billable: bool
    date: date
    rounding_rule: str
    source: str
    status: str
    hourly_rate_cents: Optional[int]
    approved_by: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TimeEntryListResponse(BaseModel):
    items: list[TimeEntryResponse]
    total: int
    page: int
    per_page: int


# ── Invoices ──


class InvoiceLineCreate(BaseModel):
    description: str
    quantity: Decimal = Field(..., gt=0)
    unit_price_cents: int = Field(..., gt=0)
    time_entry_id: Optional[uuid.UUID] = None
    sort_order: int = 0


class InvoiceLineResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    invoice_id: uuid.UUID
    description: str
    quantity: Decimal
    unit_price_cents: int
    total_cents: int
    time_entry_id: Optional[uuid.UUID]
    sort_order: int

    model_config = {"from_attributes": True}


class InvoiceCreate(BaseModel):
    case_id: Optional[uuid.UUID] = None
    invoice_number: str = Field(..., max_length=50)
    client_contact_id: uuid.UUID
    issue_date: Optional[date] = None
    due_date: date
    vat_rate: Decimal = Field(Decimal("21.00"), ge=0, le=100)
    currency: str = Field("EUR", max_length=3)
    notes: Optional[str] = None
    lines: list[InvoiceLineCreate] = Field(default_factory=list)
    time_entry_ids: list[uuid.UUID] = Field(
        default_factory=list,
        description="Auto-valorise: create lines from approved time entries",
    )


class InvoiceResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    case_id: Optional[uuid.UUID]
    invoice_number: str
    client_contact_id: uuid.UUID
    status: str
    issue_date: date
    due_date: date
    subtotal_cents: int
    vat_rate: Decimal
    vat_amount_cents: int
    total_cents: int
    peppol_status: str
    currency: str
    notes: Optional[str]
    lines: list[InvoiceLineResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InvoiceListResponse(BaseModel):
    items: list[InvoiceResponse]
    total: int
    page: int
    per_page: int


# ── Third-Party Account ──


class ThirdPartyEntryCreate(BaseModel):
    entry_type: str = Field(..., pattern="^(deposit|withdrawal|interest)$")
    amount_cents: int = Field(..., gt=0)
    description: str
    reference: str = Field(..., max_length=100)
    entry_date: date


class ThirdPartyEntryResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    case_id: uuid.UUID
    entry_type: str
    amount_cents: int
    description: str
    reference: str
    entry_date: date
    created_by: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class ThirdPartyListResponse(BaseModel):
    items: list[ThirdPartyEntryResponse]
    total: int
    page: int
    per_page: int


class ThirdPartyBalanceResponse(BaseModel):
    case_id: uuid.UUID
    deposits: int
    withdrawals: int
    interest: int
    balance: int
