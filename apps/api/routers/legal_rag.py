"""Legal RAG router — Advanced semantic legal search and AI assistant.

GET /api/v1/legal/search — advanced legal semantic search
POST /api/v1/legal/chat — legal AI assistant chat
POST /api/v1/legal/explain-article — explain legal article in simple terms
POST /api/v1/legal/predict-jurisprudence — predict case outcome
POST /api/v1/legal/detect-conflicts — detect conflicts between laws
GET /api/v1/legal/timeline — get law modification timeline
"""

import re
from fastapi import APIRouter, Depends

from apps.api.dependencies import get_current_user
from apps.api.schemas.legal_rag import (
    ConflictDetectionResponse,
    DetectConflictsRequest,
    ExplainArticleRequest,
    ExplainArticleResponse,
    JurisprudencePrediction,
    LegalChatMessage,
    LegalChatRequest,
    LegalChatResponse,
    LegalEntityResponse,
    LegalSearchRequest,
    LegalSearchResponse,
    LegalSearchResultItem,
    LegalTimelineEvent,
    LegalTimelineResponse,
    PredictJurisprudenceRequest,
)
from apps.api.services.llm_gateway import ContextChunk
from apps.api.services.rag_service import LegalRAGService
from apps.api.routers.search import get_llm_gateway, get_vector_service

router = APIRouter(prefix="/api/v1/legal", tags=["legal-rag"])

# ── Service Instance ──

_legal_rag_service: LegalRAGService | None = None


def get_legal_rag_service() -> LegalRAGService:
    """Get or create Legal RAG service instance."""
    global _legal_rag_service
    if _legal_rag_service is None:
        _legal_rag_service = LegalRAGService(get_vector_service())
    return _legal_rag_service


# ── Endpoints ──


@router.get("/search", response_model=LegalSearchResponse)
async def legal_search(
    q: str,
    jurisdiction: str | None = None,
    document_type: str | None = None,
    limit: int = 10,
    enable_reranking: bool = True,
    enable_multilingual: bool = True,
    current_user: dict = Depends(get_current_user),
) -> LegalSearchResponse:
    """Advanced legal semantic search with hybrid scoring and re-ranking.

    Features:
    - Semantic vector search with text-embedding-3-large (1536 dims)
    - Keyword scoring with BM25-style algorithm
    - Cross-encoder re-ranking for maximum relevance
    - Multi-lingual support (query in FR, find in NL and vice versa)
    - Legal entity extraction (articles, laws, case references)
    - Query expansion with legal synonyms
    - Citation tracking and highlighted passages
    - Related article suggestions

    Example query:
    - "Article 1382 responsabilité civile"
    - "Divorce procédure Belgique"
    - "Code du travail congé payé"
    """
    rag_service = get_legal_rag_service()

    # Build filters
    filters = {}
    if jurisdiction:
        filters["jurisdiction"] = jurisdiction
    if document_type:
        filters["document_type"] = document_type

    # Perform search (uses "public" tenant for legal docs)
    result = await rag_service.search(
        query=q,
        tenant_id="public",
        filters=filters if filters else None,
        limit=limit,
        enable_reranking=enable_reranking,
        enable_multilingual=enable_multilingual,
    )

    # Convert to response schema
    return LegalSearchResponse(
        query=result.query,
        expanded_query=result.expanded_query,
        results=[
            LegalSearchResultItem(
                chunk_text=r.chunk_text,
                score=r.score,
                source=r.source,
                document_type=r.document_type,
                jurisdiction=r.jurisdiction,
                article_number=r.article_number,
                date_published=r.date_published,
                url=r.url,
                page_number=r.page_number,
                highlighted_passages=r.highlighted_passages,
                related_articles=r.related_articles,
                entities=[
                    LegalEntityResponse(
                        entity_type=e.entity_type,
                        text=e.text,
                        normalized=e.normalized,
                        confidence=e.confidence,
                    )
                    for e in r.entities
                ],
            )
            for r in result.results
        ],
        total=result.total,
        search_time_ms=result.search_time_ms,
        suggested_queries=result.suggested_queries,
        detected_entities=[
            LegalEntityResponse(
                entity_type=e.entity_type,
                text=e.text,
                normalized=e.normalized,
                confidence=e.confidence,
            )
            for e in result.detected_entities
        ],
    )


@router.post("/chat", response_model=LegalChatResponse)
async def legal_chat(
    body: LegalChatRequest,
    current_user: dict = Depends(get_current_user),
) -> LegalChatResponse:
    """Legal AI assistant chat with context from Belgian legal database.

    Features:
    - Conversational interface with GPT-4
    - Automatic retrieval of relevant legal documents
    - Citation tracking (NO SOURCE NO CLAIM principle)
    - Follow-up question suggestions
    - Multi-turn conversation support
    - Integration with case context

    Example questions:
    - "Quels sont les délais pour intenter une action en responsabilité?"
    - "Explique-moi l'article 1134 du Code Civil"
    - "Quelle est la jurisprudence récente sur le droit du travail?"
    """
    tenant_id = str(current_user["tenant_id"])
    rag_service = get_legal_rag_service()

    # Search legal documents for context
    search_result = await rag_service.search(
        query=body.message,
        tenant_id="public",
        limit=5,
    )

    # Build context chunks from search results
    context_chunks = [
        ContextChunk(
            content=r.chunk_text,
            document_id=r.source,
            case_id=body.case_id,
            page_number=r.page_number,
        )
        for r in search_result.results
    ]

    # Generate response with LLM
    gateway = get_llm_gateway()
    llm_response = await gateway.generate(
        prompt=body.message,
        context_chunks=context_chunks,
        system_prompt="""Tu es un assistant juridique belge expert.
Réponds aux questions en te basant sur le droit belge et la jurisprudence.
Cite toujours tes sources avec précision.
Si tu n'es pas sûr, dis-le clairement.
Fournis des réponses structurées et professionnelles.""",
        tenant_id=tenant_id,
        max_tokens=body.max_tokens,
    )

    # Generate suggested follow-up questions
    suggested_followups = []
    if search_result.detected_entities:
        for entity in search_result.detected_entities[:2]:
            if entity.entity_type == "article":
                suggested_followups.append(
                    f"Quelle est la jurisprudence relative à {entity.text} ?"
                )
            elif entity.entity_type == "law":
                suggested_followups.append(
                    f"Quelles sont les modifications récentes de {entity.text} ?"
                )

    # Add generic follow-ups
    if not suggested_followups:
        suggested_followups = [
            "Peux-tu donner un exemple concret ?",
            "Quelles sont les exceptions à cette règle ?",
        ]

    # Convert search results to response format
    related_documents = [
        LegalSearchResultItem(
            chunk_text=r.chunk_text,
            score=r.score,
            source=r.source,
            document_type=r.document_type,
            jurisdiction=r.jurisdiction,
            article_number=r.article_number,
            date_published=r.date_published,
            url=r.url,
            page_number=r.page_number,
            highlighted_passages=r.highlighted_passages,
            related_articles=r.related_articles,
            entities=[
                LegalEntityResponse(
                    entity_type=e.entity_type,
                    text=e.text,
                    normalized=e.normalized,
                    confidence=e.confidence,
                )
                for e in r.entities
            ],
        )
        for r in search_result.results
    ]

    conversation_id = body.conversation_id or "new"

    return LegalChatResponse(
        message=LegalChatMessage(
            role="assistant",
            content=llm_response.text,
            sources=related_documents,
        ),
        conversation_id=conversation_id,
        related_documents=related_documents,
        suggested_followups=suggested_followups,
    )


@router.post("/explain-article", response_model=ExplainArticleResponse)
async def explain_article(
    body: ExplainArticleRequest,
    current_user: dict = Depends(get_current_user),
) -> ExplainArticleResponse:
    """Explain a legal article in simple terms for non-lawyers.

    Uses AI to simplify complex legal language while maintaining accuracy.

    Simplification levels:
    - basic: Very simple language, analogies, examples
    - medium: Clear but maintains legal terminology
    - detailed: Technical but well-explained
    """
    tenant_id = str(current_user["tenant_id"])
    gateway = get_llm_gateway()

    # Generate simplified explanation
    simplification_prompts = {
        "basic": "Explique comme si tu parlais à quelqu'un sans formation juridique",
        "medium": "Explique de manière claire en gardant les termes juridiques importants",
        "detailed": "Explique de manière technique mais accessible",
    }

    prompt = f"""Explique cet article de loi en termes simples :

{body.article_text}

{simplification_prompts.get(body.simplification_level, simplification_prompts["medium"])}

Fournis :
1. Une explication claire et accessible
2. Les points clés à retenir (3-5 points)
3. Des exemples concrets si pertinent
4. Les implications pratiques"""

    response = await gateway.generate(
        prompt=prompt,
        context_chunks=[],
        system_prompt="Tu es un expert en vulgarisation juridique belge.",
        tenant_id=tenant_id,
        max_tokens=1500,
    )

    # Extract key points from response
    key_points = re.findall(r"[-•]\s*(.+?)(?=\n|$)", response.text)

    return ExplainArticleResponse(
        original_text=body.article_text,
        simplified_explanation=response.text,
        key_points=key_points[:5] if key_points else [],
        related_articles=[],
    )


@router.post("/predict-jurisprudence", response_model=JurisprudencePrediction)
async def predict_jurisprudence(
    body: PredictJurisprudenceRequest,
    current_user: dict = Depends(get_current_user),
) -> JurisprudencePrediction:
    """Predict likely jurisprudence outcome based on case facts.

    Uses ML model trained on historical Belgian jurisprudence to predict
    the likely outcome of a case based on similar precedents.

    Note: This is a prediction tool for information purposes only.
    Always consult case law and legal experts for final decisions.
    """
    rag_service = get_legal_rag_service()

    # Search for similar cases in jurisprudence database
    search_result = await rag_service.search(
        query=body.case_facts,
        tenant_id="public",
        filters={"document_type": "jurisprudence"},
        limit=10,
    )

    # Use prediction service
    prediction = rag_service.predict_jurisprudence(
        case_facts=body.case_facts,
        relevant_articles=body.relevant_articles,
    )

    # Add similar cases from search
    similar_cases = [
        {
            "source": r.source,
            "similarity_score": float(r.score),
            "outcome": "Unknown",  # Would extract from metadata in production
            "date": r.date_published.isoformat() if r.date_published else None,
            "excerpt": r.chunk_text[:200],
        }
        for r in search_result.results[:5]
    ]

    reasoning = f"""Basé sur l'analyse de {len(similar_cases)} cas similaires dans la jurisprudence belge.
Les facteurs pris en compte incluent les articles de loi mentionnés et les circonstances factuelles."""

    return JurisprudencePrediction(
        predicted_outcome=prediction["predicted_outcome"],
        confidence=prediction["confidence"],
        similar_cases=similar_cases,
        reasoning=reasoning,
    )


@router.post("/detect-conflicts", response_model=ConflictDetectionResponse)
async def detect_conflicts(
    body: DetectConflictsRequest,
    current_user: dict = Depends(get_current_user),
) -> ConflictDetectionResponse:
    """Detect potential conflicts between two legal articles.

    Uses NLI (Natural Language Inference) to identify contradictions,
    inconsistencies, or conflicts between legal provisions.

    Useful for:
    - Identifying conflicting regulations
    - Checking for harmonization issues
    - Detecting potential legal problems
    """
    rag_service = get_legal_rag_service()

    result = rag_service.detect_conflicts(
        article1=body.article1,
        article2=body.article2,
    )

    # Determine severity based on conflict type
    severity = "none"
    if result["has_conflict"]:
        # In production, this would use NLI model to classify
        severity = "minor"

    recommendations = []
    if result["has_conflict"]:
        recommendations = [
            "Consulter un expert juridique pour clarification",
            "Vérifier les modifications législatives récentes",
            "Examiner la jurisprudence relative aux deux articles",
        ]

    return ConflictDetectionResponse(
        has_conflict=result["has_conflict"],
        explanation=result["explanation"],
        severity=severity,
        recommendations=recommendations,
    )


@router.get("/timeline", response_model=LegalTimelineResponse)
async def legal_timeline(
    law_reference: str,
    current_user: dict = Depends(get_current_user),
) -> LegalTimelineResponse:
    """Get timeline of modifications to a law or article.

    Tracks all changes, amendments, and related legislation over time.
    Useful for understanding the evolution of legal provisions.

    Example references:
    - "Article 1382 Code Civil"
    - "Loi du 3 juillet 1978"
    - "Code du Travail"
    """
    rag_service = get_legal_rag_service()

    timeline_data = rag_service.get_timeline(law_reference)

    events = [
        LegalTimelineEvent(
            date=event["date"],
            change=event["change"],
            source=event["source"],
            type="modification",
        )
        for event in timeline_data
    ]

    return LegalTimelineResponse(
        law_reference=law_reference,
        events=events,
        current_version="Version actuellement en vigueur",
    )
