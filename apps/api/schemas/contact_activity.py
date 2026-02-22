"""Pydantic schemas for Contact Activity and Merge."""

import uuid
from typing import Optional

from pydantic import BaseModel, Field


# ── Activity Timeline ──


class ContactActivityItem(BaseModel):
    type: str  # email | call | invoice | event | case_link
    title: str
    description: str
    occurred_at: str
    metadata: dict = Field(default_factory=dict)


class ContactActivityResponse(BaseModel):
    items: list[ContactActivityItem]
    total: int
    page: int
    per_page: int


# ── Financial Summary ──


class ContactFinancialResponse(BaseModel):
    total_invoiced_cents: int
    total_paid_cents: int
    total_outstanding_cents: int
    total_overdue_cents: int
    invoice_count: int
    last_payment_date: Optional[str] = None


# ── Contact Merge ──


class ContactDuplicateResponse(BaseModel):
    id: str
    full_name: str
    type: str
    email: Optional[str]
    phone_e164: Optional[str]
    bce_number: Optional[str]
    match_fields: list[str]
    confidence: float


class ContactMergeRequest(BaseModel):
    primary_id: uuid.UUID
    secondary_id: uuid.UUID


class ContactMergeResponse(BaseModel):
    primary_id: str
    secondary_id: str
    primary_name: str
    secondary_name: str
    transfers: dict
