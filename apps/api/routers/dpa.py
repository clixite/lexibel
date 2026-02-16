"""DPA router — e-Deposit + JBox endpoints.

POST /api/v1/dpa/deposit              — submit e-Deposit
GET  /api/v1/dpa/deposit/{id}/status  — check deposit status
POST /api/v1/dpa/jbox/poll            — poll JBox for new messages
GET  /api/v1/dpa/jbox/messages        — list all JBox messages
POST /api/v1/dpa/jbox/{id}/acknowledge — acknowledge a JBox message
"""

from fastapi import APIRouter, Depends, HTTPException

from apps.api.dependencies import get_current_user
from apps.api.schemas.dpa import (
    DepositSubmitRequest,
    DepositSubmitResponse,
    DepositStatusResponse,
    JBoxPollRequest,
    JBoxListResponse,
    JBoxMessageResponse,
    JBoxAcknowledgeResponse,
)
from apps.api.services import dpa_service

router = APIRouter(prefix="/api/v1/dpa", tags=["dpa"])


@router.post("/deposit", response_model=DepositSubmitResponse, status_code=201)
async def submit_deposit(
    body: DepositSubmitRequest,
    current_user: dict = Depends(get_current_user),
) -> DepositSubmitResponse:
    """Submit documents to a Belgian court via e-Deposit."""
    try:
        result = await dpa_service.submit_deposit(
            tenant_id=str(current_user["tenant_id"]),
            case_id=body.case_id,
            documents=[d.model_dump() for d in body.documents],
            court_code=body.court_code,
            case_reference=body.case_reference,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return DepositSubmitResponse(
        deposit_id=result.deposit_id,
        status=result.status,
        court_code=result.court_code,
        case_reference=result.case_reference,
        submitted_at=result.submitted_at,
        documents_count=result.documents_count,
        message=result.message,
    )


@router.get("/deposit/{deposit_id}/status", response_model=DepositStatusResponse)
async def get_deposit_status(
    deposit_id: str,
    current_user: dict = Depends(get_current_user),
) -> DepositStatusResponse:
    """Check the status of an e-Deposit submission."""
    try:
        status = await dpa_service.check_deposit_status(deposit_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return DepositStatusResponse(
        deposit_id=status.deposit_id,
        status=status.status,
        court_code=status.court_code,
        updated_at=status.updated_at,
        message=status.message,
        receipt_url=status.receipt_url,
    )


@router.post("/jbox/poll", response_model=JBoxListResponse)
async def poll_jbox(
    body: JBoxPollRequest,
    current_user: dict = Depends(get_current_user),
) -> JBoxListResponse:
    """Poll JBox for new judicial communications."""
    messages = await dpa_service.poll_jbox(
        tenant_id=str(current_user["tenant_id"]),
        since=body.since,
    )
    return JBoxListResponse(
        messages=[
            JBoxMessageResponse(
                message_id=m.message_id,
                sender=m.sender,
                subject=m.subject,
                body_preview=m.body_preview,
                received_at=m.received_at,
                case_reference=m.case_reference,
                court_code=m.court_code,
                has_attachments=m.has_attachments,
                attachment_names=m.attachment_names,
                acknowledged=m.acknowledged,
            )
            for m in messages
        ],
        total=len(messages),
    )


@router.get("/jbox/messages", response_model=JBoxListResponse)
async def list_jbox_messages(
    current_user: dict = Depends(get_current_user),
) -> JBoxListResponse:
    """List all JBox messages."""
    messages = await dpa_service.get_jbox_messages(
        tenant_id=str(current_user["tenant_id"]),
    )
    return JBoxListResponse(
        messages=[
            JBoxMessageResponse(
                message_id=m.message_id,
                sender=m.sender,
                subject=m.subject,
                body_preview=m.body_preview,
                received_at=m.received_at,
                case_reference=m.case_reference,
                court_code=m.court_code,
                has_attachments=m.has_attachments,
                attachment_names=m.attachment_names,
                acknowledged=m.acknowledged,
            )
            for m in messages
        ],
        total=len(messages),
    )


@router.post("/jbox/{message_id}/acknowledge", response_model=JBoxAcknowledgeResponse)
async def acknowledge_jbox_message(
    message_id: str,
    current_user: dict = Depends(get_current_user),
) -> JBoxAcknowledgeResponse:
    """Acknowledge a JBox message."""
    try:
        msg = await dpa_service.acknowledge_jbox(
            message_id=message_id,
            tenant_id=str(current_user["tenant_id"]),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return JBoxAcknowledgeResponse(
        message_id=msg.message_id,
        acknowledged=True,
        message=f"Message '{msg.subject}' acknowledged",
    )
