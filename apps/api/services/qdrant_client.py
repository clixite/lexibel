"""Qdrant client for BRAIN vector search."""

import asyncio
import logging
import os
from typing import Optional, Union

logger = logging.getLogger(__name__)

try:
    from qdrant_client import AsyncQdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
except ImportError:
    AsyncQdrantClient = None  # type: ignore[assignment,misc]
    Distance = None  # type: ignore[assignment,misc]
    VectorParams = None  # type: ignore[assignment,misc]
    PointStruct = None  # type: ignore[assignment,misc]
    logger.info(
        "qdrant-client package not installed. Vector search will be unavailable."
    )


class QdrantVectorStore:
    """Async Qdrant client for embeddings."""

    def __init__(self):
        self.url = os.getenv("QDRANT_URL", "http://localhost:6333")
        self._client: Optional[AsyncQdrantClient] = None

    async def connect(self):
        """Connect to Qdrant."""
        if AsyncQdrantClient is None:
            raise RuntimeError(
                "qdrant-client package is not installed. "
                "Install it with: pip install qdrant-client"
            )
        try:
            self._client = AsyncQdrantClient(url=self.url, check_compatibility=False)
            # Test connection
            await self._client.get_collections()
        except Exception as e:
            # Cleanup client on connection failure
            if self._client:
                await self._client.close()
                self._client = None
            logger.error(f"Failed to connect to Qdrant at {self.url}: {e}")
            raise

    async def close(self):
        """Close connection."""
        if self._client:
            await self._client.close()

    async def create_collection(self, name: str, vector_size: int = 1536):
        """Create collection if not exists."""
        if self._client is None:
            raise RuntimeError("Qdrant client not connected. Call connect() first.")
        collections = await self._client.get_collections()
        if name not in [c.name for c in collections.collections]:
            await self._client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )

    async def upsert(
        self, collection: str, id: Union[str, int], vector: list[float], payload: dict
    ):
        """Insert or update vector."""
        if self._client is None:
            raise RuntimeError("Qdrant client not connected. Call connect() first.")
        await self._client.upsert(
            collection_name=collection,
            points=[PointStruct(id=id, vector=vector, payload=payload)],
        )

    async def search(self, collection: str, vector: list[float], limit: int = 10):
        """Search similar vectors."""
        try:
            from qdrant_client.http.models import SearchRequest
        except ImportError:
            raise RuntimeError(
                "qdrant-client package is not installed. "
                "Install it with: pip install qdrant-client"
            )

        if self._client is None:
            raise RuntimeError("Qdrant client not connected. Call connect() first.")
        results = await self._client.http.search_api.search_points(
            collection_name=collection,
            search_request=SearchRequest(vector=vector, limit=limit, with_payload=True),
        )
        return results.result

    async def health_check(self) -> bool:
        """Check if Qdrant is reachable."""
        try:
            if self._client is None:
                raise RuntimeError("Qdrant client not connected. Call connect() first.")
            await self._client.get_collections()
            return True
        except RuntimeError as e:
            logger.warning(f"Qdrant health check failed - client not connected: {e}")
            return False
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return False


# Singleton
_qdrant_client: Optional[QdrantVectorStore] = None
_lock = asyncio.Lock()


async def get_qdrant_client() -> QdrantVectorStore:
    """Get Qdrant client singleton."""
    global _qdrant_client
    async with _lock:
        if _qdrant_client is None:
            _qdrant_client = QdrantVectorStore()
            await _qdrant_client.connect()
        return _qdrant_client
