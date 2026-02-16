"""Pydantic schemas for DPA endpoints (e-Deposit + JBox)."""

from typing import Optional

from pydantic import BaseModel, Field


# ── e-Deposit schemas ──


class DepositDocument(BaseModel):
    file_name: str
    content_type: str = "application/pdf"
    file_size: int = 0
    sha256_hash: str = ""
    document_type: str = Field("conclusions", pattern="^(conclusions|requete|pieces)$")


class DepositSubmitRequest(BaseModel):
    case_id: str
    court_code: str = Field(..., description="Belgian court code (e.g. BXL, ANT)")
    case_reference: str = ""
    documents: list[DepositDocument] = Field(..., min_length=1)


class DepositSubmitResponse(BaseModel):
    deposit_id: str
    status: str
    court_code: str
    case_reference: str
    submitted_at: str
    documents_count: int
    message: str = ""


class DepositStatusResponse(BaseModel):
    deposit_id: str
    status: str
    court_code: str
    updated_at: str
    message: str = ""
    receipt_url: Optional[str] = None


# ── JBox schemas ──


class JBoxPollRequest(BaseModel):
    since: Optional[str] = Field(
        None, description="ISO datetime — only return messages after this"
    )


class JBoxMessageResponse(BaseModel):
    message_id: str
    sender: str
    subject: str
    body_preview: str
    received_at: str
    case_reference: str = ""
    court_code: str = ""
    has_attachments: bool = False
    attachment_names: list[str] = []
    acknowledged: bool = False


class JBoxListResponse(BaseModel):
    messages: list[JBoxMessageResponse]
    total: int


class JBoxAcknowledgeResponse(BaseModel):
    message_id: str
    acknowledged: bool
    message: str = ""
