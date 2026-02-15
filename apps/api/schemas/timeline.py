"""Pydantic schemas for Timeline (InteractionEvents) and Evidence Links."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class InteractionEventCreate(BaseModel):
    case_id: Optional[uuid.UUID] = None
    source: str = Field(
        ...,
        pattern="^(OUTLOOK|RINGOVER|PLAUD|DPA_DEPOSIT|DPA_JBOX|MANUAL)$",
    )
    event_type: str = Field(..., max_length=100)
    title: str = Field(..., max_length=500)
    body: Optional[str] = None
    occurred_at: datetime
    metadata: dict = Field(default_factory=dict)


class EvidenceLinkResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    interaction_event_id: uuid.UUID
    file_path: str
    file_name: str
    mime_type: str
    file_size_bytes: int
    sha256_hash: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InteractionEventResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    case_id: Optional[uuid.UUID]
    source: str
    event_type: str
    title: str
    body: Optional[str]
    occurred_at: datetime
    metadata: dict
    created_by: Optional[uuid.UUID]
    created_at: datetime
    evidence_links: list[EvidenceLinkResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class TimelineResponse(BaseModel):
    items: list[InteractionEventResponse]
    total: int
    page: int
    per_page: int
