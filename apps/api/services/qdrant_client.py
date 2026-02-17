"""Qdrant client for BRAIN vector search."""
import os
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from typing import Optional, Union

class QdrantVectorStore:
    """Async Qdrant client for embeddings."""

    def __init__(self):
        self.url = os.getenv("QDRANT_URL", "http://localhost:6333")
        self._client: Optional[AsyncQdrantClient] = None

    async def connect(self):
        """Connect to Qdrant."""
        self._client = AsyncQdrantClient(url=self.url, check_compatibility=False)

    async def close(self):
        """Close connection."""
        if self._client:
            await self._client.close()

    async def create_collection(self, name: str, vector_size: int = 1536):
        """Create collection if not exists."""
        collections = await self._client.get_collections()
        if name not in [c.name for c in collections.collections]:
            await self._client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE
                )
            )

    async def upsert(self, collection: str, id: Union[str, int], vector: list[float], payload: dict):
        """Insert or update vector."""
        await self._client.upsert(
            collection_name=collection,
            points=[
                PointStruct(
                    id=id,
                    vector=vector,
                    payload=payload
                )
            ]
        )

    async def search(self, collection: str, vector: list[float], limit: int = 10):
        """Search similar vectors."""
        results = await self._client.query_points(
            collection_name=collection,
            query=vector,
            limit=limit
        )
        return results.points

    async def health_check(self) -> bool:
        """Check if Qdrant is reachable."""
        try:
            await self._client.get_collections()
            return True
        except Exception:
            return False


# Singleton
_qdrant_client: Optional[QdrantVectorStore] = None

async def get_qdrant_client() -> QdrantVectorStore:
    """Get Qdrant client singleton."""
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantVectorStore()
        await _qdrant_client.connect()
    return _qdrant_client
