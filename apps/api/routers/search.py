"""Search router — hybrid search and AI generation.

POST /api/v1/search — hybrid search (vector + keyword)
POST /api/v1/ai/generate — AI generation with citations
"""
from fastapi import APIRouter, Depends, HTTPException, status

from apps.api.dependencies import get_current_user
from apps.api.schemas.search import (
    AIGenerateRequest,
    AIGenerateResponse,
    AISourceItem,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
)
from apps.api.services.llm_gateway import (
    ContextChunk,
    LLMGateway,
    StubLLMGateway,
)
from apps.api.services.search_service import SearchService
from apps.api.services.vector_service import InMemoryVectorService, VectorService

router = APIRouter(prefix="/api/v1", tags=["search"])

# ── Service instances (swappable for testing via dependency_overrides) ──

_vector_service: VectorService | None = None
_search_service: SearchService | None = None
_llm_gateway: LLMGateway | None = None


def get_vector_service() -> VectorService:
    global _vector_service
    if _vector_service is None:
        _vector_service = InMemoryVectorService()
    return _vector_service


def get_search_service() -> SearchService:
    global _search_service
    if _search_service is None:
        _search_service = SearchService(get_vector_service())
    return _search_service


def get_llm_gateway() -> LLMGateway:
    global _llm_gateway
    if _llm_gateway is None:
        _llm_gateway = StubLLMGateway()
    return _llm_gateway


@router.post("/search", response_model=SearchResponse)
async def search(
    body: SearchRequest,
    current_user: dict = Depends(get_current_user),
) -> SearchResponse:
    """Hybrid search: vector similarity + keyword scoring."""
    svc = get_search_service()
    result = svc.search(
        query=body.query,
        tenant_id=str(current_user["tenant_id"]),
        case_id=str(body.case_id) if body.case_id else None,
        top_k=body.top_k,
    )

    return SearchResponse(
        query=result.query,
        results=[
            SearchResultItem(
                chunk_text=r.chunk_text,
                document_id=r.document_id,
                case_id=r.case_id,
                evidence_link_id=r.evidence_link_id,
                score=r.score,
                page_number=r.page_number,
                source_type=r.source_type,
            )
            for r in result.results
        ],
        total=result.total,
    )


@router.post("/ai/generate", response_model=AIGenerateResponse)
async def ai_generate(
    body: AIGenerateRequest,
    current_user: dict = Depends(get_current_user),
) -> AIGenerateResponse:
    """AI text generation with context and citation validation (P3)."""
    tenant_id = str(current_user["tenant_id"])

    # If case_id provided, search for relevant context chunks
    context_chunks: list[ContextChunk] = []
    if body.case_id:
        svc = get_search_service()
        results = svc.vector_search(
            query=body.prompt,
            tenant_id=tenant_id,
            case_id=str(body.case_id),
            top_k=5,
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
        prompt=body.prompt,
        context_chunks=context_chunks,
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
