"""Pydantic schemas for Contacts CRUD."""

import re
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class ContactCreate(BaseModel):
    type: str = Field(..., pattern="^(natural|legal)$")
    full_name: str = Field(..., max_length=255)
    bce_number: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    phone_e164: Optional[str] = Field(None, max_length=20)
    address: Optional[dict] = None
    language: str = Field("fr", max_length=5)

    @field_validator("bce_number")
    @classmethod
    def validate_bce(cls, v: Optional[str]) -> Optional[str]:
        """Validate Belgian BCE number format: 0xxx.xxx.xxx"""
        if v is None:
            return v
        # Remove spaces and dots for validation
        clean = v.replace(".", "").replace(" ", "")
        if not re.match(r"^0\d{9}$", clean):
            raise ValueError("BCE number must be in format 0xxx.xxx.xxx")
        # Normalize to dotted format
        return f"{clean[0:4]}.{clean[4:7]}.{clean[7:10]}"

    @field_validator("phone_e164")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """Validate Belgian E.164 phone format: +32..."""
        if v is None:
            return v
        # Remove spaces and dashes for validation
        clean = v.replace(" ", "").replace("-", "")
        if not re.match(r"^\+32\d{8,9}$", clean):
            raise ValueError("Phone must be in Belgian E.164 format: +32xxxxxxxxx")
        return clean


class ContactUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=255)
    bce_number: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    phone_e164: Optional[str] = Field(None, max_length=20)
    address: Optional[dict] = None
    language: Optional[str] = Field(None, max_length=5)

    @field_validator("bce_number")
    @classmethod
    def validate_bce(cls, v: Optional[str]) -> Optional[str]:
        """Validate Belgian BCE number format: 0xxx.xxx.xxx"""
        if v is None:
            return v
        clean = v.replace(".", "").replace(" ", "")
        if not re.match(r"^0\d{9}$", clean):
            raise ValueError("BCE number must be in format 0xxx.xxx.xxx")
        return f"{clean[0:4]}.{clean[4:7]}.{clean[7:10]}"

    @field_validator("phone_e164")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """Validate Belgian E.164 phone format: +32..."""
        if v is None:
            return v
        clean = v.replace(" ", "").replace("-", "")
        if not re.match(r"^\+32\d{8,9}$", clean):
            raise ValueError("Phone must be in Belgian E.164 format: +32xxxxxxxxx")
        return clean


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
