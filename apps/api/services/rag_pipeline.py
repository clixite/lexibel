"""RAG Pipeline — Complete RAG orchestration for Case Brain.

Orchestrates the full RAG flow:
1. Ingest: Document → Chunks → Embeddings → Vector Store
2. Query: Question → Embedding → Hybrid Search → Rerank → Context
3. Generate: Context + Question → LLM → Answer with Citations

Implements P3 (No Source No Claim) at every step.
"""

import os
from dataclasses import dataclass, field
from typing import Optional

from apps.api.services.chunking_service import (
    Chunk,
    chunk_document,
    chunk_text,
    generate_embeddings,
)
from apps.api.services.vector_service import (
    InMemoryVectorService,
    VectorSearchResult,
    VectorService,
)
from apps.api.services.llm_gateway import (
    ContextChunk,
    LLMGateway,
    LLMResponse,
    StubLLMGateway,
    SYSTEM_PROMPT_DEFAULT,
)


@dataclass
class IngestResult:
    """Result of document ingestion."""

    document_id: str
    chunks_created: int
    embeddings_generated: int
    vectors_upserted: int
    success: bool = True
    error: Optional[str] = None


@dataclass
class QueryResult:
    """Result of RAG query with retrieved context."""

    query: str
    context_chunks: list[ContextChunk] = field(default_factory=list)
    total_results: int = 0
    search_time_ms: float = 0.0
    reranked: bool = False


@dataclass
class GenerateResult:
    """Result of RAG generation with answer and citations."""

    query: str
    answer: str
    sources: list = field(default_factory=list)
    model: str = ""
    tokens_used: int = 0
    has_uncited_claims: bool = False
    uncited_claims: list[str] = field(default_factory=list)
    context_chunks_used: int = 0


class RAGPipeline:
    """Complete RAG pipeline orchestrator.

    Implements the full RAG flow from document ingestion to answer generation.
    Enforces P3 (No Source No Claim) principle throughout.
    """

    def __init__(
        self,
        vector_service: Optional[VectorService] = None,
        llm_gateway: Optional[LLMGateway] = None,
        use_stub: bool = False,
    ):
        """Initialize RAG pipeline.

        Args:
            vector_service: Vector store service (defaults to InMemoryVectorService)
            llm_gateway: LLM gateway (defaults to StubLLMGateway if use_stub=True)
            use_stub: Use stub services for testing without dependencies
        """
        if use_stub or vector_service is None:
            self.vector_service = InMemoryVectorService()
        else:
            self.vector_service = vector_service

        if use_stub or llm_gateway is None:
            self.llm_gateway = StubLLMGateway(
                canned_response="Selon les documents fournis, voici une analyse basée sur les éléments du dossier. [Source: documents contexte]"
            )
        else:
            self.llm_gateway = llm_gateway

        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """Ensure vector collection exists."""
        try:
            self.vector_service.ensure_collection()
        except Exception:
            # InMemoryVectorService doesn't need collection creation
            pass

    async def ingest_document(
        self,
        document_id: str,
        content: bytes,
        mime_type: str,
        case_id: Optional[str] = None,
        tenant_id: str = "",
        evidence_link_id: Optional[str] = None,
    ) -> IngestResult:
        """Ingest a document into the RAG system.

        Steps:
        1. Chunk the document (512 tokens, 64 overlap)
        2. Generate embeddings for each chunk
        3. Upsert vectors into vector store with metadata

        Args:
            document_id: Unique document identifier
            content: Document content as bytes
            mime_type: MIME type (application/pdf, text/plain, etc.)
            case_id: Optional case ID for filtering
            tenant_id: Tenant ID for isolation (P5)
            evidence_link_id: Optional evidence link ID

        Returns:
            IngestResult with statistics
        """
        try:
            # 1. Chunk the document
            chunks = chunk_document(
                content=content,
                mime_type=mime_type,
                case_id=case_id,
                document_id=document_id,
                evidence_link_id=evidence_link_id,
                tenant_id=tenant_id,
            )

            if not chunks:
                return IngestResult(
                    document_id=document_id,
                    chunks_created=0,
                    embeddings_generated=0,
                    vectors_upserted=0,
                    success=False,
                    error="No chunks extracted from document",
                )

            # 2. Generate embeddings
            chunk_texts = [c.content for c in chunks]
            embeddings = generate_embeddings(chunk_texts)

            # 3. Upsert into vector store
            chunk_ids = [c.chunk_id for c in chunks]
            payloads = [
                {
                    "content": c.content,
                    "document_id": c.document_id,
                    "case_id": c.case_id,
                    "evidence_link_id": c.evidence_link_id,
                    "tenant_id": c.tenant_id,
                    "page_number": c.page_number,
                    "chunk_index": c.chunk_index,
                    "metadata": c.metadata,
                }
                for c in chunks
            ]

            self.vector_service.upsert_chunks(
                chunk_ids=chunk_ids,
                embeddings=embeddings,
                payloads=payloads,
            )

            return IngestResult(
                document_id=document_id,
                chunks_created=len(chunks),
                embeddings_generated=len(embeddings),
                vectors_upserted=len(chunk_ids),
                success=True,
            )

        except Exception as e:
            return IngestResult(
                document_id=document_id,
                chunks_created=0,
                embeddings_generated=0,
                vectors_upserted=0,
                success=False,
                error=str(e),
            )

    async def ingest_text(
        self,
        document_id: str,
        text: str,
        case_id: Optional[str] = None,
        tenant_id: str = "",
        evidence_link_id: Optional[str] = None,
        extra_metadata: Optional[dict] = None,
    ) -> IngestResult:
        """Ingest plain text into the RAG system.

        Convenience method for text ingestion without MIME type handling.

        Args:
            document_id: Unique document identifier
            text: Text content
            case_id: Optional case ID
            tenant_id: Tenant ID for isolation
            evidence_link_id: Optional evidence link ID
            extra_metadata: Additional metadata

        Returns:
            IngestResult with statistics
        """
        try:
            # Chunk the text
            chunks = chunk_text(
                text=text,
                case_id=case_id,
                document_id=document_id,
                evidence_link_id=evidence_link_id,
                tenant_id=tenant_id,
                extra_metadata=extra_metadata,
            )

            if not chunks:
                return IngestResult(
                    document_id=document_id,
                    chunks_created=0,
                    embeddings_generated=0,
                    vectors_upserted=0,
                    success=False,
                    error="No chunks created from text",
                )

            # Generate embeddings
            chunk_texts = [c.content for c in chunks]
            embeddings = generate_embeddings(chunk_texts)

            # Upsert into vector store
            chunk_ids = [c.chunk_id for c in chunks]
            payloads = [
                {
                    "content": c.content,
                    "document_id": c.document_id,
                    "case_id": c.case_id,
                    "evidence_link_id": c.evidence_link_id,
                    "tenant_id": c.tenant_id,
                    "page_number": c.page_number,
                    "chunk_index": c.chunk_index,
                    "metadata": c.metadata,
                }
                for c in chunks
            ]

            self.vector_service.upsert_chunks(
                chunk_ids=chunk_ids,
                embeddings=embeddings,
                payloads=payloads,
            )

            return IngestResult(
                document_id=document_id,
                chunks_created=len(chunks),
                embeddings_generated=len(embeddings),
                vectors_upserted=len(chunk_ids),
                success=True,
            )

        except Exception as e:
            return IngestResult(
                document_id=document_id,
                chunks_created=0,
                embeddings_generated=0,
                vectors_upserted=0,
                success=False,
                error=str(e),
            )

    async def query(
        self,
        question: str,
        tenant_id: str,
        case_id: Optional[str] = None,
        top_k: int = 10,
        filters: Optional[dict] = None,
        enable_rerank: bool = False,
    ) -> QueryResult:
        """Query the RAG system for relevant context.

        Steps:
        1. Embed the question
        2. Perform vector similarity search
        3. Optionally re-rank results
        4. Return context chunks for generation

        Args:
            question: Natural language question
            tenant_id: Tenant ID for isolation (P5)
            case_id: Optional case ID filter
            top_k: Number of results to return
            filters: Optional additional filters
            enable_rerank: Enable cross-encoder re-ranking (if available)

        Returns:
            QueryResult with retrieved context chunks
        """
        import time

        start = time.time()

        try:
            # 1. Embed the question
            query_embedding = generate_embeddings([question])[0]

            # 2. Vector search
            results = self.vector_service.search(
                query_embedding=query_embedding,
                tenant_id=tenant_id,
                top_k=top_k * 2 if enable_rerank else top_k,
                case_id=case_id,
                filters=filters,
            )

            # 3. Re-ranking (simple score-based for now, upgrade to cross-encoder)
            if enable_rerank and len(results) > top_k:
                # Simple re-ranking: sort by score, take top_k
                results = sorted(results, key=lambda r: r.score, reverse=True)[:top_k]

            # 4. Convert to ContextChunk format
            context_chunks = [
                ContextChunk(
                    content=r.content,
                    document_id=r.document_id,
                    evidence_link_id=r.evidence_link_id,
                    case_id=r.case_id,
                    page_number=r.page_number,
                    chunk_index=0,
                )
                for r in results
            ]

            search_time_ms = (time.time() - start) * 1000

            return QueryResult(
                query=question,
                context_chunks=context_chunks,
                total_results=len(results),
                search_time_ms=search_time_ms,
                reranked=enable_rerank,
            )

        except Exception as e:
            return QueryResult(
                query=question,
                context_chunks=[],
                total_results=0,
                search_time_ms=0.0,
                reranked=False,
            )

    async def generate_answer(
        self,
        question: str,
        context_chunks: list[ContextChunk],
        tenant_id: str,
        system_prompt: str = SYSTEM_PROMPT_DEFAULT,
        max_tokens: int = 2000,
    ) -> GenerateResult:
        """Generate an answer from context chunks using LLM.

        Implements P3 (No Source No Claim) by:
        1. Providing sources to LLM
        2. Validating generated answer has citations
        3. Flagging uncited claims

        Args:
            question: User question
            context_chunks: Retrieved context from query()
            tenant_id: Tenant ID for rate limiting
            system_prompt: LLM system prompt
            max_tokens: Max tokens to generate

        Returns:
            GenerateResult with answer and citation validation
        """
        try:
            # Generate with LLM
            response: LLMResponse = await self.llm_gateway.generate(
                prompt=question,
                context_chunks=context_chunks,
                system_prompt=system_prompt,
                tenant_id=tenant_id,
                max_tokens=max_tokens,
            )

            return GenerateResult(
                query=question,
                answer=response.text,
                sources=response.sources,
                model=response.model,
                tokens_used=response.tokens_used,
                has_uncited_claims=response.has_uncited_claims,
                uncited_claims=response.uncited_claims,
                context_chunks_used=len(context_chunks),
            )

        except Exception as e:
            return GenerateResult(
                query=question,
                answer=f"Erreur lors de la génération: {str(e)}",
                sources=[],
                model="error",
                tokens_used=0,
                has_uncited_claims=False,
                uncited_claims=[],
                context_chunks_used=0,
            )

    async def answer_question(
        self,
        question: str,
        tenant_id: str,
        case_id: Optional[str] = None,
        top_k: int = 10,
        system_prompt: str = SYSTEM_PROMPT_DEFAULT,
        max_tokens: int = 2000,
    ) -> GenerateResult:
        """Complete RAG flow: query + generate.

        Convenience method that combines query() and generate_answer().

        Args:
            question: User question
            tenant_id: Tenant ID
            case_id: Optional case filter
            top_k: Number of context chunks
            system_prompt: LLM system prompt
            max_tokens: Max tokens to generate

        Returns:
            GenerateResult with answer and citations
        """
        # 1. Query for context
        query_result = await self.query(
            question=question,
            tenant_id=tenant_id,
            case_id=case_id,
            top_k=top_k,
            enable_rerank=True,
        )

        # 2. Generate answer
        generate_result = await self.generate_answer(
            question=question,
            context_chunks=query_result.context_chunks,
            tenant_id=tenant_id,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
        )

        return generate_result

    def delete_document(self, document_id: str) -> bool:
        """Delete all vectors for a document.

        Args:
            document_id: Document ID to delete

        Returns:
            True if successful
        """
        try:
            self.vector_service.delete_by_document(document_id)
            return True
        except Exception:
            return False


# ── Factory Functions ──


def create_rag_pipeline(
    use_stub: bool = False,
    qdrant_url: Optional[str] = None,
    llm_api_key: Optional[str] = None,
) -> RAGPipeline:
    """Create a RAG pipeline with optional configuration.

    Args:
        use_stub: Use stub services (no Qdrant, no LLM API)
        qdrant_url: Qdrant URL (default: from env or localhost)
        llm_api_key: LLM API key (default: from env)

    Returns:
        Configured RAGPipeline instance
    """
    vector_service = None
    llm_gateway = None

    if not use_stub:
        # Try to use real services
        try:
            from apps.api.services.vector_service import VectorService

            vector_service = VectorService(url=qdrant_url)
        except Exception:
            # Fall back to in-memory
            vector_service = InMemoryVectorService()

        # Try to use real LLM
        if llm_api_key or os.getenv("LLM_API_KEY"):
            llm_gateway = LLMGateway(api_key=llm_api_key)
        else:
            # Fall back to stub
            llm_gateway = StubLLMGateway()

    return RAGPipeline(
        vector_service=vector_service,
        llm_gateway=llm_gateway,
        use_stub=use_stub,
    )
