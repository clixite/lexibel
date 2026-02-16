"""Search service — hybrid search combining vector similarity + keyword.

Implements P3 (No Source No Claim): every result must have a traceable source.
"""
import re
from dataclasses import dataclass, field
from typing import Optional

from apps.api.services.chunking_service import generate_embeddings
from apps.api.services.vector_service import VectorSearchResult, VectorService


@dataclass
class SearchResult:
    """A search result with source traceability (P3)."""

    chunk_text: str
    document_id: Optional[str] = None
    case_id: Optional[str] = None
    evidence_link_id: Optional[str] = None
    score: float = 0.0
    page_number: Optional[int] = None
    source_type: str = "vector"  # vector, keyword, hybrid
    metadata: dict = field(default_factory=dict)

    @property
    def has_source(self) -> bool:
        """P3: verify this result has a traceable source."""
        return bool(self.document_id or self.evidence_link_id)


@dataclass
class SearchResponse:
    """Full search response with results and metadata."""

    query: str
    results: list[SearchResult]
    total: int
    vector_count: int = 0
    keyword_count: int = 0


def _keyword_score(text: str, query: str) -> float:
    """Simple BM25-style keyword scoring.

    Counts query term occurrences in text, normalized by text length.
    """
    text_lower = text.lower()
    terms = re.findall(r"\w+", query.lower())
    if not terms:
        return 0.0

    total_score = 0.0
    words = re.findall(r"\w+", text_lower)
    doc_len = len(words) if words else 1

    for term in terms:
        tf = text_lower.count(term)
        # BM25-like: tf / (tf + k1) where k1 adjusts for doc length
        k1 = 1.2
        normalized_tf = tf / (tf + k1 * (doc_len / 200))
        total_score += normalized_tf

    return total_score / len(terms)


class SearchService:
    """Hybrid search service combining vector + keyword scoring."""

    def __init__(self, vector_service: VectorService) -> None:
        self._vector = vector_service

    def search(
        self,
        query: str,
        tenant_id: str,
        case_id: Optional[str] = None,
        top_k: int = 10,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3,
    ) -> SearchResponse:
        """Hybrid search: vector similarity + keyword scoring, then rerank."""
        # 1. Vector search
        query_embedding = generate_embeddings([query])[0]
        vector_results = self._vector.search(
            query_embedding=query_embedding,
            tenant_id=tenant_id,
            case_id=case_id,
            top_k=top_k * 2,  # Fetch more for reranking
        )

        # 2. Score and rerank with keyword component
        scored: list[tuple[SearchResult, float]] = []
        for vr in vector_results:
            kw_score = _keyword_score(vr.content, query)
            hybrid_score = (vector_weight * vr.score) + (keyword_weight * kw_score)

            result = SearchResult(
                chunk_text=vr.content,
                document_id=vr.document_id,
                case_id=vr.case_id,
                evidence_link_id=vr.evidence_link_id,
                score=hybrid_score,
                page_number=vr.page_number,
                source_type="hybrid",
                metadata=vr.metadata or {},
            )
            scored.append((result, hybrid_score))

        # 3. Sort by hybrid score descending
        scored.sort(key=lambda x: x[1], reverse=True)

        # 4. Take top_k, ensure P3 (No Source No Claim)
        results = [r for r, _ in scored[:top_k] if r.has_source]

        return SearchResponse(
            query=query,
            results=results,
            total=len(results),
            vector_count=len(vector_results),
            keyword_count=0,  # Pure keyword search not yet implemented
        )

    def vector_search(
        self,
        query: str,
        tenant_id: str,
        case_id: Optional[str] = None,
        top_k: int = 10,
    ) -> list[SearchResult]:
        """Pure vector search without keyword component."""
        query_embedding = generate_embeddings([query])[0]
        vector_results = self._vector.search(
            query_embedding=query_embedding,
            tenant_id=tenant_id,
            case_id=case_id,
            top_k=top_k,
        )

        return [
            SearchResult(
                chunk_text=vr.content,
                document_id=vr.document_id,
                case_id=vr.case_id,
                evidence_link_id=vr.evidence_link_id,
                score=vr.score,
                page_number=vr.page_number,
                source_type="vector",
                metadata=vr.metadata or {},
            )
            for vr in vector_results
            if vr.content  # Filter empty chunks
        ]
