"""Pydantic schemas for ML endpoints."""

from typing import Optional

from pydantic import BaseModel, Field


# ── Email Triage ──


class ClassifyRequest(BaseModel):
    subject: str = ""
    body: str = ""
    sender: str = ""


class ClassifyResponse(BaseModel):
    category: str  # URGENT, NORMAL, INFO_ONLY, SPAM
    confidence: float
    reasons: list[str]
    suggested_priority: int


# ── Case Linkage ──


class CaseForLinkage(BaseModel):
    id: str
    reference: str = ""
    title: str = ""
    description: str = ""
    contacts: list[str] = []
    updated_at: Optional[str] = None


class LinkRequest(BaseModel):
    text: str = Field(..., min_length=1)
    sender: str = ""
    existing_cases: list[CaseForLinkage] = Field(..., min_length=1)


class CaseSuggestionResponse(BaseModel):
    case_id: str
    case_reference: str
    case_title: str
    confidence: float
    match_reasons: list[str]


class LinkResponse(BaseModel):
    suggestions: list[CaseSuggestionResponse]


# ── Deadline Extraction ──


class DeadlineRequest(BaseModel):
    text: str = Field(..., min_length=1)
    reference_date: Optional[str] = Field(
        None, description="ISO date for relative deadline computation"
    )


class DeadlineResponse(BaseModel):
    text: str
    date: Optional[str]
    deadline_type: str
    confidence: float
    source_text: str = ""
    days: Optional[int] = None


class DeadlineListResponse(BaseModel):
    deadlines: list[DeadlineResponse]


# ── Full Pipeline ──


class ProcessEventRequest(BaseModel):
    subject: str = ""
    body: str = ""
    sender: str = ""
    type: str = "email"
    existing_cases: list[CaseForLinkage] = []


class ProcessEventResponse(BaseModel):
    classification: Optional[ClassifyResponse] = None
    suggestions: list[CaseSuggestionResponse] = []
    deadlines: list[DeadlineResponse] = []
