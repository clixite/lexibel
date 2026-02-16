"""ML router — classification, linkage, deadline extraction, full pipeline.

POST /api/v1/ml/classify  — email triage
POST /api/v1/ml/link      — case linkage ranking
POST /api/v1/ml/deadlines — extract deadlines from text
POST /api/v1/ml/process   — full ML pipeline
"""
from datetime import date

from fastapi import APIRouter, Depends

from apps.api.dependencies import get_current_user
from apps.api.schemas.ml import (
    ClassifyRequest,
    ClassifyResponse,
    LinkRequest,
    LinkResponse,
    CaseSuggestionResponse,
    DeadlineRequest,
    DeadlineListResponse,
    DeadlineResponse,
    ProcessEventRequest,
    ProcessEventResponse,
)
from apps.api.services.ml import MLPipeline

router = APIRouter(prefix="/api/v1/ml", tags=["ml"])

# Singleton pipeline
_pipeline = MLPipeline()


@router.post("/classify", response_model=ClassifyResponse)
async def classify_email(
    body: ClassifyRequest,
    current_user: dict = Depends(get_current_user),
) -> ClassifyResponse:
    """Classify an email by urgency category."""
    result = _pipeline.triage.classify(
        subject=body.subject,
        body=body.body,
        sender=body.sender,
    )
    return ClassifyResponse(
        category=result.category,
        confidence=result.confidence,
        reasons=result.reasons,
        suggested_priority=result.suggested_priority,
    )


@router.post("/link", response_model=LinkResponse)
async def link_to_case(
    body: LinkRequest,
    current_user: dict = Depends(get_current_user),
) -> LinkResponse:
    """Rank which case an event most likely belongs to."""
    suggestions = _pipeline.linker.rank(
        text=body.text,
        sender=body.sender,
        existing_cases=[c.model_dump() for c in body.existing_cases],
    )
    return LinkResponse(
        suggestions=[
            CaseSuggestionResponse(
                case_id=s.case_id,
                case_reference=s.case_reference,
                case_title=s.case_title,
                confidence=s.confidence,
                match_reasons=s.match_reasons,
            )
            for s in suggestions
        ],
    )


@router.post("/deadlines", response_model=DeadlineListResponse)
async def extract_deadlines(
    body: DeadlineRequest,
    current_user: dict = Depends(get_current_user),
) -> DeadlineListResponse:
    """Extract dates and deadlines from legal text."""
    ref_date = None
    if body.reference_date:
        try:
            ref_date = date.fromisoformat(body.reference_date)
        except ValueError:
            pass

    deadlines = _pipeline.deadlines.extract(body.text, reference_date=ref_date)
    return DeadlineListResponse(
        deadlines=[
            DeadlineResponse(
                text=d.text,
                date=d.date,
                deadline_type=d.deadline_type,
                confidence=d.confidence,
                source_text=d.source_text,
                days=d.days,
            )
            for d in deadlines
        ],
    )


@router.post("/process", response_model=ProcessEventResponse)
async def process_event(
    body: ProcessEventRequest,
    current_user: dict = Depends(get_current_user),
) -> ProcessEventResponse:
    """Run full ML pipeline on an event."""
    event = {
        "subject": body.subject,
        "body": body.body,
        "sender": body.sender,
        "type": body.type,
        "existing_cases": [c.model_dump() for c in body.existing_cases],
    }
    result = _pipeline.process_event(event)

    classification = None
    if result.classification:
        classification = ClassifyResponse(
            category=result.classification.category,
            confidence=result.classification.confidence,
            reasons=result.classification.reasons,
            suggested_priority=result.classification.suggested_priority,
        )

    return ProcessEventResponse(
        classification=classification,
        suggestions=[
            CaseSuggestionResponse(
                case_id=s.case_id,
                case_reference=s.case_reference,
                case_title=s.case_title,
                confidence=s.confidence,
                match_reasons=s.match_reasons,
            )
            for s in result.case_suggestions
        ],
        deadlines=[
            DeadlineResponse(
                text=d.text,
                date=d.date,
                deadline_type=d.deadline_type,
                confidence=d.confidence,
                source_text=d.source_text,
                days=d.days,
            )
            for d in result.deadlines
        ],
    )
