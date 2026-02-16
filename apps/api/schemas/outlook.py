"""Pydantic schemas for Outlook endpoints."""

from typing import Optional

from pydantic import BaseModel, Field


class OutlookSyncRequest(BaseModel):
    user_id: str = Field(..., description="Outlook user mailbox or ID to sync")
    since: Optional[str] = Field(
        None, description="ISO datetime — only sync emails after this"
    )


class OutlookEmailResponse(BaseModel):
    message_id: str
    subject: str
    sender: str
    recipients: list[str]
    body_preview: str
    received_at: str
    has_attachments: bool = False
    matched_case_id: Optional[str] = None
    matched_case_reference: Optional[str] = None


class OutlookSyncResponse(BaseModel):
    status: str
    emails: list[OutlookEmailResponse]
    total_synced: int
    message: str = ""


class OutlookEmailListResponse(BaseModel):
    emails: list[OutlookEmailResponse]
    total: int


class OutlookSendRequest(BaseModel):
    to: list[str] = Field(..., min_length=1)
    subject: str
    body: str
    draft_id: Optional[str] = None


class OutlookSendResponse(BaseModel):
    status: str
    message_id: str = ""
    message: str = ""
