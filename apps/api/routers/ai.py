"""AI router — document drafting, summarization, analysis.

POST /api/v1/ai/draft — generate document draft from case context
POST /api/v1/ai/summarize — summarize case timeline
POST /api/v1/ai/analyze — analyze a document
"""

from fastapi import APIRouter, Depends

from apps.api.dependencies import get_current_user
from apps.api.schemas.search import (
    AIAnalyzeRequest,
    AIDraftRequest,
    AIGenerateResponse,
    AISourceItem,
    AISummarizeRequest,
)
from apps.api.services.llm_gateway import (
    ContextChunk,
    SYSTEM_PROMPT_ANALYZE,
    SYSTEM_PROMPT_DRAFT,
    SYSTEM_PROMPT_SUMMARIZE,
)
from apps.api.routers.search import get_llm_gateway, get_search_service

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


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
