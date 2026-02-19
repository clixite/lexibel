"""Tests for Qdrant client."""

import pytest
from apps.api.services.qdrant_client import QdrantVectorStore


@pytest.mark.asyncio
async def test_qdrant_connection():
    """Test Qdrant connection."""
    client = QdrantVectorStore()
    await client.connect()

    health = await client.health_check()
    assert health is True

    await client.close()


@pytest.mark.asyncio
async def test_qdrant_collection_creation():
    """Test collection creation."""
    client = QdrantVectorStore()
    await client.connect()

    await client.create_collection("test_collection", vector_size=384)

    collections = await client._client.get_collections()
    collection_names = [c.name for c in collections.collections]
    assert "test_collection" in collection_names

    await client.close()


@pytest.mark.asyncio
async def test_qdrant_upsert_and_search():
    """Test vector upsert and search."""
    client = QdrantVectorStore()
    await client.connect()

    await client.create_collection("test_search", vector_size=3)

    # Insert vector
    await client.upsert("test_search", 1, [0.1, 0.2, 0.3], {"text": "test"})

    # Search
    results = await client.search("test_search", [0.1, 0.2, 0.3], limit=1)
    assert len(results) == 1
    assert results[0].id == 1

    await client.close()
