"""Vector service — Qdrant integration for document search.

Collection: lexibel_documents (384 dims for all-MiniLM-L6-v2).
Tenant isolation via payload filter on tenant_id.
"""
import os
import uuid
from dataclasses import dataclass
from typing import Any, Optional

COLLECTION_NAME = "lexibel_documents"
VECTOR_DIM = 384  # all-MiniLM-L6-v2


@dataclass
class VectorSearchResult:
    """A single vector search result."""

    chunk_id: str
    score: float
    content: str
    case_id: Optional[str] = None
    document_id: Optional[str] = None
    evidence_link_id: Optional[str] = None
    page_number: Optional[int] = None
    metadata: dict | None = None


class VectorService:
    """Qdrant vector database service with tenant-isolated search."""

    def __init__(self, url: Optional[str] = None, api_key: Optional[str] = None) -> None:
        self._url = url or os.getenv("QDRANT_URL", "http://localhost:6333")
        self._api_key = api_key or os.getenv("QDRANT_API_KEY")
        self._client: Any = None

    def _get_client(self) -> Any:
        """Lazy-init Qdrant client."""
        if self._client is None:
            try:
                from qdrant_client import QdrantClient

                self._client = QdrantClient(
                    url=self._url,
                    api_key=self._api_key,
                )
            except ImportError:
                raise ImportError("qdrant-client is required")
        return self._client

    def ensure_collection(self) -> None:
        """Create collection if it doesn't exist."""
        from qdrant_client.models import Distance, VectorParams

        client = self._get_client()
        collections = client.get_collections().collections
        names = [c.name for c in collections]
        if COLLECTION_NAME not in names:
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=VECTOR_DIM,
                    distance=Distance.COSINE,
                ),
            )

    def upsert_chunks(
        self,
        chunk_ids: list[str],
        embeddings: list[list[float]],
        payloads: list[dict],
    ) -> None:
        """Upsert chunk vectors with metadata payloads."""
        from qdrant_client.models import PointStruct

        client = self._get_client()
        points = [
            PointStruct(
                id=cid,
                vector=emb,
                payload=payload,
            )
            for cid, emb, payload in zip(chunk_ids, embeddings, payloads)
        ]
        client.upsert(collection_name=COLLECTION_NAME, points=points)

    def search(
        self,
        query_embedding: list[float],
        tenant_id: str,
        top_k: int = 10,
        case_id: Optional[str] = None,
        filters: Optional[dict] = None,
    ) -> list[VectorSearchResult]:
        """Search vectors with tenant isolation via payload filter."""
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        must_conditions = [
            FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))
        ]
        if case_id:
            must_conditions.append(
                FieldCondition(key="case_id", match=MatchValue(value=case_id))
            )
        if filters:
            for key, value in filters.items():
                must_conditions.append(
                    FieldCondition(key=key, match=MatchValue(value=value))
                )

        client = self._get_client()
        results = client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_embedding,
            query_filter=Filter(must=must_conditions),
            limit=top_k,
            with_payload=True,
        )

        return [
            VectorSearchResult(
                chunk_id=str(r.id),
                score=r.score,
                content=r.payload.get("content", ""),
                case_id=r.payload.get("case_id"),
                document_id=r.payload.get("document_id"),
                evidence_link_id=r.payload.get("evidence_link_id"),
                page_number=r.payload.get("page_number"),
                metadata=r.payload.get("metadata"),
            )
            for r in results
        ]

    def delete_by_document(self, document_id: str) -> None:
        """Delete all vectors for a given document."""
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        client = self._get_client()
        client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id),
                    )
                ]
            ),
        )


# ── In-memory stub for testing ──


class InMemoryVectorService(VectorService):
    """In-memory vector service for testing (no Qdrant needed)."""

    def __init__(self) -> None:
        self._store: dict[str, dict] = {}  # chunk_id -> {vector, payload}

    def _get_client(self) -> Any:
        return None  # Not used

    def ensure_collection(self) -> None:
        pass

    def upsert_chunks(
        self,
        chunk_ids: list[str],
        embeddings: list[list[float]],
        payloads: list[dict],
    ) -> None:
        for cid, emb, payload in zip(chunk_ids, embeddings, payloads):
            self._store[cid] = {"vector": emb, "payload": payload}

    def search(
        self,
        query_embedding: list[float],
        tenant_id: str,
        top_k: int = 10,
        case_id: Optional[str] = None,
        filters: Optional[dict] = None,
    ) -> list[VectorSearchResult]:
        """Cosine similarity search in memory with tenant filter."""
        import math

        def cosine_sim(a: list[float], b: list[float]) -> float:
            dot = sum(x * y for x, y in zip(a, b))
            mag_a = math.sqrt(sum(x * x for x in a))
            mag_b = math.sqrt(sum(x * x for x in b))
            if mag_a == 0 or mag_b == 0:
                return 0.0
            return dot / (mag_a * mag_b)

        scored: list[tuple[str, float, dict]] = []
        for cid, data in self._store.items():
            payload = data["payload"]
            if payload.get("tenant_id") != tenant_id:
                continue
            if case_id and payload.get("case_id") != case_id:
                continue
            if filters:
                skip = False
                for k, v in filters.items():
                    if payload.get(k) != v:
                        skip = True
                        break
                if skip:
                    continue
            score = cosine_sim(query_embedding, data["vector"])
            scored.append((cid, score, payload))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [
            VectorSearchResult(
                chunk_id=cid,
                score=score,
                content=payload.get("content", ""),
                case_id=payload.get("case_id"),
                document_id=payload.get("document_id"),
                evidence_link_id=payload.get("evidence_link_id"),
                page_number=payload.get("page_number"),
                metadata=payload.get("metadata"),
            )
            for cid, score, payload in scored[:top_k]
        ]

    def delete_by_document(self, document_id: str) -> None:
        to_delete = [
            cid
            for cid, data in self._store.items()
            if data["payload"].get("document_id") == document_id
        ]
        for cid in to_delete:
            del self._store[cid]
