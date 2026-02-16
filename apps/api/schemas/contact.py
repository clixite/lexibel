"""Pydantic schemas for Contacts CRUD."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ContactCreate(BaseModel):
    type: str = Field(..., pattern="^(natural|legal)$")
    full_name: str = Field(..., max_length=255)
    bce_number: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=255)
    phone_e164: Optional[str] = Field(None, max_length=20)
    address: Optional[dict] = None
    language: str = Field("fr", max_length=5)


class ContactUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=255)
    bce_number: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=255)
    phone_e164: Optional[str] = Field(None, max_length=20)
    address: Optional[dict] = None
    language: Optional[str] = Field(None, max_length=5)


class ContactResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    type: str
    full_name: str
    bce_number: Optional[str]
    email: Optional[str]
    phone_e164: Optional[str]
    address: Optional[dict]
    language: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ContactListResponse(BaseModel):
    items: list[ContactResponse]
    total: int
    page: int
    per_page: int
