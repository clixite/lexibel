"""AI router — document drafting, summarization, analysis, audio transcription, and legal RAG.

POST /api/v1/ai/draft — generate document draft from case context
POST /api/v1/ai/summarize — summarize case timeline
POST /api/v1/ai/analyze — analyze a document
POST /api/v1/ai/transcribe — transcribe audio with AI insights
POST /api/v1/ai/transcribe/stream — stream transcription word-by-word

Legal RAG endpoints:
GET /api/v1/ai/legal-search — advanced legal semantic search
POST /api/v1/ai/legal-chat — legal AI assistant chat
POST /api/v1/ai/explain-article — explain legal article in simple terms
POST /api/v1/ai/predict-jurisprudence — predict case outcome
POST /api/v1/ai/detect-conflicts — detect conflicts between laws
GET /api/v1/ai/legal-timeline — get law modification timeline
"""

import json
from typing import AsyncIterator

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse

from apps.api.dependencies import get_current_user
from apps.api.schemas.agents import (
    ActionItemResponse,
    CompleteTranscriptionResponse,
    ExtractedDecisionResponse,
    ExtractedReferenceResponse,
    SpeakerSegmentResponse,
    TranscriptInsightsResponse,
    TranscriptionResponse,
)
from apps.api.schemas.search import (
    AIAnalyzeRequest,
    AIDraftRequest,
    AIGenerateResponse,
    AISourceItem,
    AISummarizeRequest,
)
from apps.api.schemas.legal_rag import (
    DetectConflictsRequest,
    ConflictDetectionResponse,
    ExplainArticleRequest,
    ExplainArticleResponse,
    LegalChatRequest,
    LegalChatResponse,
    LegalChatMessage,
    LegalSearchRequest,
    LegalSearchResponse,
    LegalSearchResultItem,
    LegalEntityResponse,
    LegalTimelineRequest,
    LegalTimelineResponse,
    LegalTimelineEvent,
    PredictJurisprudenceRequest,
    JurisprudencePrediction,
)
from apps.api.services.action_extraction_service import ActionExtractionService
from apps.api.services.llm_gateway import (
    ContextChunk,
    SYSTEM_PROMPT_ANALYZE,
    SYSTEM_PROMPT_DRAFT,
    SYSTEM_PROMPT_SUMMARIZE,
)
from apps.api.services.transcription_service import (
    TranscriptionService,
    validate_audio_format,
)
from apps.api.routers.search import get_llm_gateway, get_search_service, get_vector_service
from apps.api.services.rag_service import LegalRAGService

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])

# ── Service Instances ──

_legal_rag_service: LegalRAGService | None = None
_transcription_service: TranscriptionService | None = None
_action_extraction_service: ActionExtractionService | None = None


def get_legal_rag_service() -> LegalRAGService:
    """Get or create Legal RAG service instance."""
    global _legal_rag_service
    if _legal_rag_service is None:
        _legal_rag_service = LegalRAGService(get_vector_service())
    return _legal_rag_service


def get_transcription_service() -> TranscriptionService:
    """Get or create Transcription service instance."""
    global _transcription_service
    if _transcription_service is None:
        _transcription_service = TranscriptionService()
    return _transcription_service


def get_action_extraction_service() -> ActionExtractionService:
    """Get or create Action Extraction service instance."""
    global _action_extraction_service
    if _action_extraction_service is None:
        _action_extraction_service = ActionExtractionService(get_llm_gateway())
    return _action_extraction_service


@router.post("/draft", response_model=AIGenerateResponse)
async def ai_draft(
    body: AIDraftRequest,
    current_user: dict = Depends(get_current_user),
) -> AIGenerateResponse:
    """Generate a document draft from case context."""
    tenant_id = str(current_user["tenant_id"])

    # Fetch context from case
    svc = get_search_service()
    results = svc.vector_search(
        query=f"rédaction {body.draft_type} dossier",
        tenant_id=tenant_id,
        case_id=str(body.case_id),
        top_k=8,
    )
    context_chunks = [
        ContextChunk(
            content=r.chunk_text,
            document_id=r.document_id,
            evidence_link_id=r.evidence_link_id,
            case_id=r.case_id,
            page_number=r.page_number,
        )
        for r in results
    ]

    prompt = f"Rédige un brouillon de {body.draft_type} pour ce dossier."
    if body.instructions:
        prompt += f"\nInstructions supplémentaires : {body.instructions}"

    gateway = get_llm_gateway()
    response = await gateway.generate(
        prompt=prompt,
        context_chunks=context_chunks,
        system_prompt=SYSTEM_PROMPT_DRAFT,
        tenant_id=tenant_id,
        max_tokens=body.max_tokens,
    )

    return AIGenerateResponse(
        text=response.text,
        sources=[
            AISourceItem(
                document_id=s.document_id,
                evidence_link_id=s.evidence_link_id,
                case_id=s.case_id,
                chunk_text=s.chunk_text,
                page_number=s.page_number,
            )
            for s in response.sources
        ],
        model=response.model,
        tokens_used=response.tokens_used,
        has_uncited_claims=response.has_uncited_claims,
    )


@router.post("/summarize", response_model=AIGenerateResponse)
async def ai_summarize(
    body: AISummarizeRequest,
    current_user: dict = Depends(get_current_user),
) -> AIGenerateResponse:
    """Summarize a case timeline."""
    tenant_id = str(current_user["tenant_id"])

    svc = get_search_service()
    results = svc.vector_search(
        query="résumé chronologique événements dossier",
        tenant_id=tenant_id,
        case_id=str(body.case_id),
        top_k=10,
    )
    context_chunks = [
        ContextChunk(
            content=r.chunk_text,
            document_id=r.document_id,
            evidence_link_id=r.evidence_link_id,
            case_id=r.case_id,
            page_number=r.page_number,
        )
        for r in results
    ]

    gateway = get_llm_gateway()
    response = await gateway.generate(
        prompt="Fais un résumé structuré de ce dossier.",
        context_chunks=context_chunks,
        system_prompt=SYSTEM_PROMPT_SUMMARIZE,
        tenant_id=tenant_id,
        max_tokens=body.max_tokens,
    )

    return AIGenerateResponse(
        text=response.text,
        sources=[
            AISourceItem(
                document_id=s.document_id,
                evidence_link_id=s.evidence_link_id,
                case_id=s.case_id,
                chunk_text=s.chunk_text,
                page_number=s.page_number,
            )
            for s in response.sources
        ],
        model=response.model,
        tokens_used=response.tokens_used,
        has_uncited_claims=response.has_uncited_claims,
    )


@router.post("/analyze", response_model=AIGenerateResponse)
async def ai_analyze(
    body: AIAnalyzeRequest,
    current_user: dict = Depends(get_current_user),
) -> AIGenerateResponse:
    """Analyze a document."""
    tenant_id = str(current_user["tenant_id"])

    # Search for the specific document chunks
    svc = get_search_service()
    results = svc.vector_search(
        query="analyse document complet",
        tenant_id=tenant_id,
        case_id=str(body.case_id) if body.case_id else None,
        top_k=10,
    )
    # Filter to the specific document if possible
    doc_id = str(body.document_id)
    doc_results = [r for r in results if r.document_id == doc_id]
    if not doc_results:
        doc_results = results  # Fallback to all results

    context_chunks = [
        ContextChunk(
            content=r.chunk_text,
            document_id=r.document_id,
            evidence_link_id=r.evidence_link_id,
            case_id=r.case_id,
            page_number=r.page_number,
        )
        for r in doc_results
    ]

    gateway = get_llm_gateway()
    response = await gateway.generate(
        prompt="Analyse ce document en identifiant les parties, obligations, délais et risques.",
        context_chunks=context_chunks,
        system_prompt=SYSTEM_PROMPT_ANALYZE,
        tenant_id=tenant_id,
        max_tokens=body.max_tokens,
    )

    return AIGenerateResponse(
        text=response.text,
        sources=[
            AISourceItem(
                document_id=s.document_id,
                evidence_link_id=s.evidence_link_id,
                case_id=s.case_id,
                chunk_text=s.chunk_text,
                page_number=s.page_number,
            )
            for s in response.sources
        ],
        model=response.model,
        tokens_used=response.tokens_used,
        has_uncited_claims=response.has_uncited_claims,
    )


# ── Audio Transcription Endpoints ──


@router.post("/transcribe", response_model=CompleteTranscriptionResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str | None = Form(None),
    enable_diarization: bool = Form(True),
    extract_insights: bool = Form(True),
    case_id: str | None = Form(None),
    current_user: dict = Depends(get_current_user),
) -> CompleteTranscriptionResponse:
    """Transcribe audio file with optional AI insights extraction.

    Supports: mp3, wav, m4a, ogg, webm, flac
    Max file size: 25MB

    Features:
    - Automatic language detection (FR/NL/EN)
    - Speaker diarization (who said what)
    - AI-powered action item extraction
    - Sentiment analysis
    - Reference detection (cases, contacts, documents)

    Returns:
        Transcript + insights with action items, decisions, references
    """
    tenant_id = str(current_user["tenant_id"])

    # Validate file format
    if not file.content_type or not validate_audio_format(file.content_type):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported audio format: {file.content_type}. "
            f"Supported: mp3, wav, m4a, ogg, webm, flac",
        )

    # Check file size (25MB limit for Whisper API)
    file_size = 0
    content = await file.read()
    file_size = len(content)
    if file_size > 25 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large. Maximum size is 25MB",
        )

    # Reset file pointer
    await file.seek(0)

    # Transcribe audio
    transcription_svc = get_transcription_service()
    try:
        result = await transcription_svc.transcribe_audio(
            audio_file=file.file,
            filename=file.filename or "audio.mp3",
            language=language,
            enable_diarization=enable_diarization,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transcription failed: {str(e)}",
        )

    # Build transcription response
    transcription_response = TranscriptionResponse(
        transcript_id=result.transcript_id,
        full_text=result.full_text,
        language=result.language,
        duration_seconds=result.duration_seconds,
        segments=[
            SpeakerSegmentResponse(
                speaker_id=seg.speaker_id,
                start_time=seg.start_time,
                end_time=seg.end_time,
                text=seg.text,
                confidence=seg.confidence,
            )
            for seg in result.segments
        ],
        confidence_score=result.confidence_score,
        processing_time_seconds=result.processing_time_seconds,
        model=result.model,
    )

    # Extract insights if requested
    insights_response = None
    if extract_insights and result.full_text:
        extraction_svc = get_action_extraction_service()
        try:
            insights = await extraction_svc.extract_insights(
                transcript_text=result.full_text,
                transcript_id=result.transcript_id,
                tenant_id=tenant_id,
                segments=result.segments,
            )

            insights_response = TranscriptInsightsResponse(
                transcript_id=insights.transcript_id,
                summary=insights.summary,
                action_items=[
                    ActionItemResponse(
                        action_id=action.action_id,
                        text=action.text,
                        assignee=action.assignee,
                        deadline=action.deadline.isoformat() if action.deadline else None,
                        priority=action.priority,
                        status=action.status,
                        confidence=action.confidence,
                        source_timestamp=action.source_segment_start,
                    )
                    for action in insights.action_items
                ],
                decisions=[
                    ExtractedDecisionResponse(
                        decision_id=dec.decision_id,
                        text=dec.text,
                        decided_by=dec.decided_by,
                        timestamp=dec.timestamp,
                        confidence=dec.confidence,
                    )
                    for dec in insights.decisions
                ],
                references=[
                    ExtractedReferenceResponse(
                        ref_id=ref.ref_id,
                        ref_type=ref.ref_type,
                        text=ref.text,
                        context=ref.context,
                        confidence=ref.confidence,
                        timestamp=ref.timestamp,
                    )
                    for ref in insights.references
                ],
                key_topics=insights.key_topics,
                sentiment_score=insights.sentiment_score,
                urgency_level=insights.urgency_level,
                suggested_next_actions=insights.suggested_next_actions,
                extracted_dates=insights.extracted_dates,
            )
        except Exception as e:
            # Don't fail the entire request if insights extraction fails
            # Log the error and continue
            pass

    return CompleteTranscriptionResponse(
        transcription=transcription_response,
        insights=insights_response,
    )


@router.post("/transcribe/stream")
async def transcribe_audio_stream(
    file: UploadFile = File(...),
    language: str | None = Form(None),
    current_user: dict = Depends(get_current_user),
) -> StreamingResponse:
    """Stream transcription results word-by-word.

    Returns NDJSON stream of words with timestamps:
    {"word": "Bonjour", "start": 0.5, "end": 1.2, "confidence": 0.95}
    {"word": "monsieur", "start": 1.3, "end": 1.8, "confidence": 0.92}
    ...
    """
    # Validate file format
    if not file.content_type or not validate_audio_format(file.content_type):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported audio format: {file.content_type}",
        )

    async def stream_words() -> AsyncIterator[str]:
        """Generate word stream."""
        transcription_svc = get_transcription_service()
        try:
            async for word in transcription_svc.transcribe_streaming(
                audio_file=file.file,
                filename=file.filename or "audio.mp3",
                language=language,
            ):
                # Yield NDJSON (newline-delimited JSON)
                word_json = {
                    "word": word.word,
                    "start": word.start_time,
                    "end": word.end_time,
                    "confidence": word.confidence,
                }
                yield json.dumps(word_json) + "\n"
        except Exception as e:
            error_json = {"error": str(e)}
            yield json.dumps(error_json) + "\n"

    return StreamingResponse(
        stream_words(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
