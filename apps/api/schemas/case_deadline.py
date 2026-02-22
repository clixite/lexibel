"""Pydantic schemas for Case Deadlines and Relations."""

import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Deadlines ──


class DeadlineResponse(BaseModel):
    title: str
    date: date
    legal_basis: str
    days_remaining: int
    urgency: str  # normal | warning | urgent | overdue
    category: str  # prescription | appeal | procedural | custom
    notes: str = ""


class DeadlineReportResponse(BaseModel):
    case_id: str
    matter_type: str
    deadlines: list[DeadlineResponse]
    warnings: list[str]


# ── Case Relations ──


class CaseRelationCreate(BaseModel):
    target_case_id: uuid.UUID
    relation_type: str = Field(
        ...,
        pattern=r"^(appeal|opposition|cassation|joined|split|related|parent)$",
    )
    notes: Optional[str] = None


class CaseRelationResponse(BaseModel):
    id: uuid.UUID
    source_case_id: uuid.UUID
    target_case_id: uuid.UUID
    relation_type: str
    notes: Optional[str]
    created_at: datetime

    # Populated from joined query
    target_reference: Optional[str] = None
    target_title: Optional[str] = None
    target_status: Optional[str] = None

    model_config = {"from_attributes": True}
