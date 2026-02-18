"""LLM Gateway API routes.

Provides GDPR-compliant LLM completion, streaming, audit, and admin endpoints.
All routes require JWT authentication. Admin routes require super_admin or admin role.
"""

import uuid
from datetime import datetime
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_current_tenant, get_current_user, get_db_session
from apps.api.services.llm.audit_logger import AIAuditLogger
from apps.api.services.llm.data_classifier import DataSensitivity
from apps.api.services.llm.gateway import LLMGateway

router = APIRouter(prefix="/api/v1/llm", tags=["llm"])

# Singleton gateway instance
_gateway: LLMGateway | None = None


def _get_gateway() -> LLMGateway:
    global _gateway
    if _gateway is None:
        _gateway = LLMGateway()
    return _gateway


# ── Request/Response models ──


class LLMCompleteRequest(BaseModel):
    messages: list[dict] = Field(..., description="Chat messages [{role, content}]")
    purpose: str = Field(..., description="case_analysis, document_draft, legal_research, etc.")
    preferred_provider: str | None = Field(None, description="Preferred provider name")
    model: str | None = Field(None, description="Specific model override")
    temperature: float = Field(0.3, ge=0.0, le=2.0)
    max_tokens: int = Field(4096, ge=1, le=128000)
    data_sensitivity: str | None = Field(None, description="Force sensitivity: public, semi, sensitive, critical")
    require_human_validation: bool = Field(False, description="Require human validation (AI Act Art. 14)")


class LLMClassifyRequest(BaseModel):
    text: str = Field(..., description="Text to classify")


class LLMAuditValidateRequest(BaseModel):
    pass  # No body needed, validator comes from JWT


# ── Completion endpoints ──


@router.post("/complete")
async def llm_complete(
    body: LLMCompleteRequest,
    session: AsyncSession = Depends(get_db_session),
    user: dict = Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
):
    """Execute an LLM completion with GDPR-compliant routing.

    The gateway automatically:
    1. Classifies data sensitivity
    2. Routes to the appropriate provider tier
    3. Anonymizes data if needed
    4. Logs everything for AI Act compliance
    """
    gateway = _get_gateway()
    audit_logger = AIAuditLogger(session)

    sensitivity = None
    if body.data_sensitivity:
        try:
            sensitivity = DataSensitivity(body.data_sensitivity)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid sensitivity: {body.data_sensitivity}. "
                f"Valid: public, semi, sensitive, critical",
            )

    try:
        response = await gateway.complete(
            messages=body.messages,
            purpose=body.purpose,
            tenant_id=tenant_id,
            user_id=user["user_id"],
            audit_logger=audit_logger,
            data_sensitivity=sensitivity,
            preferred_provider=body.preferred_provider,
            model=body.model,
            temperature=body.temperature,
            max_tokens=body.max_tokens,
            require_human_validation=body.require_human_validation,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    return {
        "content": response.content,
        "provider": response.provider,
        "model": response.model,
        "sensitivity": response.sensitivity,
        "was_anonymized": response.was_anonymized,
        "tokens": {
            "input": response.token_count_input,
            "output": response.token_count_output,
        },
        "cost_eur": response.cost_estimate_eur,
        "latency_ms": response.latency_ms,
        "audit_id": response.audit_id,
        "require_human_validation": response.require_human_validation,
    }


@router.post("/stream")
async def llm_stream(
    body: LLMCompleteRequest,
    session: AsyncSession = Depends(get_db_session),
    user: dict = Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
):
    """SSE streaming LLM completion with GDPR-compliant routing."""
    gateway = _get_gateway()
    audit_logger = AIAuditLogger(session)

    sensitivity = None
    if body.data_sensitivity:
        try:
            sensitivity = DataSensitivity(body.data_sensitivity)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid sensitivity: {body.data_sensitivity}")

    async def event_generator() -> AsyncIterator[str]:
        try:
            async for chunk in gateway.stream(
                messages=body.messages,
                purpose=body.purpose,
                tenant_id=tenant_id,
                user_id=user["user_id"],
                audit_logger=audit_logger,
                data_sensitivity=sensitivity,
                preferred_provider=body.preferred_provider,
                model=body.model,
                temperature=body.temperature,
                max_tokens=body.max_tokens,
            ):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        except ValueError as e:
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
        except RuntimeError as e:
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Provider status ──


@router.get("/providers")
async def llm_providers(
    user: dict = Depends(get_current_user),
):
    """List all LLM providers with their status, tier, and cost."""
    gateway = _get_gateway()
    statuses = await gateway.get_provider_status()
    return {"providers": statuses}


# ── Classification endpoint ──


@router.post("/classify")
async def llm_classify(
    body: LLMClassifyRequest,
    user: dict = Depends(get_current_user),
):
    """Test data sensitivity classification.

    Returns the detected sensitivity level, allowed providers, and detected entities.
    Useful for debugging and transparency (AI Act Art. 13).
    """
    gateway = _get_gateway()
    result = gateway.classify_text(body.text)
    return result


# ── Audit endpoints ──


def _require_admin(user: dict) -> None:
    """Require admin or super_admin role."""
    if user.get("role") not in ("admin", "super_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")


@router.get("/audit")
async def llm_audit_list(
    page: int = 1,
    per_page: int = 20,
    provider: str | None = None,
    sensitivity: str | None = None,
    purpose: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    session: AsyncSession = Depends(get_db_session),
    user: dict = Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
):
    """Paginated audit log list with filters. Admin only."""
    _require_admin(user)
    audit_logger = AIAuditLogger(session)

    dt_from = datetime.fromisoformat(date_from) if date_from else None
    dt_to = datetime.fromisoformat(date_to) if date_to else None

    logs, total = await audit_logger.get_audit_logs(
        tenant_id=tenant_id,
        page=page,
        per_page=min(per_page, 100),
        provider=provider,
        sensitivity=sensitivity,
        purpose=purpose,
        date_from=dt_from,
        date_to=dt_to,
    )

    return {
        "items": [
            {
                "id": str(log.id),
                "provider": log.provider,
                "model": log.model,
                "data_sensitivity": log.data_sensitivity,
                "was_anonymized": log.was_anonymized,
                "purpose": log.purpose,
                "token_count_input": log.token_count_input,
                "token_count_output": log.token_count_output,
                "latency_ms": log.latency_ms,
                "cost_estimate_eur": float(log.cost_estimate_eur) if log.cost_estimate_eur else None,
                "human_validated": log.human_validated,
                "error": log.error,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/audit/stats")
async def llm_audit_stats(
    days: int = 30,
    session: AsyncSession = Depends(get_db_session),
    user: dict = Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
):
    """Usage statistics. Admin only."""
    _require_admin(user)
    audit_logger = AIAuditLogger(session)
    return await audit_logger.get_usage_stats(tenant_id, days=days)


@router.post("/audit/{audit_id}/validate")
async def llm_audit_validate(
    audit_id: str,
    session: AsyncSession = Depends(get_db_session),
    user: dict = Depends(get_current_user),
):
    """Mark an AI output as validated by a human (AI Act Art. 14)."""
    try:
        log_id = uuid.UUID(audit_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid audit ID")

    audit_logger = AIAuditLogger(session)
    await audit_logger.mark_human_validated(log_id, user["user_id"])
    return {"status": "validated", "audit_id": audit_id, "validator_id": str(user["user_id"])}


@router.get("/audit/dpia-report")
async def llm_dpia_report(
    session: AsyncSession = Depends(get_db_session),
    user: dict = Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
):
    """Export DPIA (Data Protection Impact Assessment) report.

    Required by GDPR Art. 35 for high-risk AI processing.
    Admin only.
    """
    _require_admin(user)
    audit_logger = AIAuditLogger(session)
    return await audit_logger.export_dpia_report(tenant_id)


@router.get("/audit/article30-register")
async def llm_article30_register(
    session: AsyncSession = Depends(get_db_session),
    user: dict = Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
):
    """Export GDPR Article 30 Record of Processing Activities.

    Required by GDPR Art. 30 for all processing activities involving personal data.
    Admin only.
    """
    _require_admin(user)
    audit_logger = AIAuditLogger(session)
    return await audit_logger.export_article30_register(tenant_id)
