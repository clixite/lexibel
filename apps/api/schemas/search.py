"""Pydantic schemas for Search and AI endpoints."""

import uuid
from typing import Optional

from pydantic import BaseModel, Field


# ── Search schemas ──


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    case_id: Optional[uuid.UUID] = None
    top_k: int = Field(10, ge=1, le=100)


class SearchResultItem(BaseModel):
    chunk_text: str
    document_id: Optional[str] = None
    case_id: Optional[str] = None
    evidence_link_id: Optional[str] = None
    score: float
    page_number: Optional[int] = None
    source_type: str = "hybrid"

    model_config = {"from_attributes": True}


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultItem]
    total: int


# ── AI generation schemas ──


class AIGenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=5000)
    case_id: Optional[uuid.UUID] = None
    max_tokens: int = Field(2000, ge=100, le=8000)


class AISourceItem(BaseModel):
    document_id: Optional[str] = None
    evidence_link_id: Optional[str] = None
    case_id: Optional[str] = None
    chunk_text: str = ""
    page_number: Optional[int] = None


class AIGenerateResponse(BaseModel):
    text: str
    sources: list[AISourceItem] = []
    model: str = ""
    tokens_used: int = 0
    has_uncited_claims: bool = False


class AIDraftRequest(BaseModel):
    case_id: uuid.UUID
    draft_type: str = Field("courrier", pattern="^(courrier|conclusions|requete|memo)$")
    instructions: str = Field("", max_length=2000)
    max_tokens: int = Field(3000, ge=100, le=8000)


class AISummarizeRequest(BaseModel):
    case_id: uuid.UUID
    max_tokens: int = Field(2000, ge=100, le=8000)


class AIAnalyzeRequest(BaseModel):
    document_id: uuid.UUID
    case_id: Optional[uuid.UUID] = None
    max_tokens: int = Field(2000, ge=100, le=8000)
