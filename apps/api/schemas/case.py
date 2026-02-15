"""Pydantic schemas for Cases CRUD."""
import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class CaseCreate(BaseModel):
    reference: str = Field(..., max_length=50)
    title: str = Field(..., max_length=500)
    matter_type: str = Field(..., max_length=100)
    court_reference: Optional[str] = Field(None, max_length=100)
    status: str = Field("open", max_length=50)
    jurisdiction: Optional[str] = Field(None, max_length=100)
    responsible_user_id: uuid.UUID
    opened_at: Optional[date] = None
    metadata: dict = Field(default_factory=dict)


class CaseUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=500)
    court_reference: Optional[str] = Field(None, max_length=100)
    matter_type: Optional[str] = Field(None, max_length=100)
    status: Optional[str] = Field(None, max_length=50)
    jurisdiction: Optional[str] = None
    responsible_user_id: Optional[uuid.UUID] = None
    closed_at: Optional[date] = None
    metadata: Optional[dict] = None


class CaseResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    reference: str
    court_reference: Optional[str]
    title: str
    matter_type: str
    status: str
    jurisdiction: Optional[str]
    responsible_user_id: uuid.UUID
    opened_at: date
    closed_at: Optional[date]
    metadata: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CaseListResponse(BaseModel):
    items: list[CaseResponse]
    total: int
    page: int
    per_page: int
