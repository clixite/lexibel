"""Pydantic schemas for Email Templates and Compose."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# ── Email Templates ──


class EmailTemplateCreate(BaseModel):
    name: str = Field(..., max_length=255)
    category: str = Field(
        ...,
        pattern=r"^(mise_en_demeure|convocation|conclusions|accusé_reception|courrier_adverse|demande_pieces|relance|general)$",
    )
    subject_template: str = Field(..., max_length=500)
    body_template: str
    language: str = Field("fr", max_length=5)
    matter_types: list[str] = Field(default_factory=list)


class EmailTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    category: Optional[str] = None
    subject_template: Optional[str] = Field(None, max_length=500)
    body_template: Optional[str] = None
    language: Optional[str] = Field(None, max_length=5)
    matter_types: Optional[list[str]] = None


class EmailTemplateResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    category: str
    subject_template: str
    body_template: str
    language: str
    matter_types: list
    is_system: bool
    created_by: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EmailTemplateRenderRequest(BaseModel):
    template_id: uuid.UUID
    case_id: uuid.UUID
    contact_id: Optional[uuid.UUID] = None
    extra_variables: dict = Field(default_factory=dict)


class EmailTemplateRenderResponse(BaseModel):
    subject: str
    body: str
    template_id: str
    template_name: str


# ── Email Compose ──


class EmailComposeRequest(BaseModel):
    to: list[EmailStr] = Field(..., min_length=1)
    cc: list[EmailStr] = Field(default_factory=list)
    bcc: list[EmailStr] = Field(default_factory=list)
    subject: str = Field(..., max_length=500)
    body_text: str
    body_html: Optional[str] = None
    case_id: Optional[uuid.UUID] = None
    template_id: Optional[uuid.UUID] = None
    in_reply_to: Optional[uuid.UUID] = None


class EmailComposeResponse(BaseModel):
    status: str
    message_id: Optional[str] = None
    provider: str
    case_id: Optional[str] = None


class EmailSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    case_id: Optional[uuid.UUID] = None
    from_email: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    has_attachments: Optional[bool] = None
    page: int = Field(1, ge=1)
    per_page: int = Field(20, ge=1, le=100)
