"""Pydantic schemas for Inbox items (human-in-the-loop queue)."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class InboxItemResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    source: str
    status: str
    raw_payload: dict
    suggested_case_id: Optional[uuid.UUID]
    confidence: Optional[float]
    validated_by: Optional[uuid.UUID]
    validated_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class InboxValidateRequest(BaseModel):
    case_id: uuid.UUID
    event_type: str = Field(..., max_length=100)
    title: str = Field(..., max_length=500)
    body: Optional[str] = None


class InboxListResponse(BaseModel):
    items: list[InboxItemResponse]
    total: int
    page: int
    per_page: int
