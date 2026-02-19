"""Tests for Neo4j client."""

import pytest
from apps.api.services.neo4j_client import Neo4jClient


@pytest.mark.asyncio
async def test_neo4j_connection():
    """Test Neo4j connection."""
    client = Neo4jClient()
    await client.connect()

    health = await client.health_check()
    assert health is True

    await client.close()


@pytest.mark.asyncio
async def test_neo4j_query_execution():
    """Test query execution."""
    client = Neo4jClient()
    await client.connect()

    result = await client.execute_query("RETURN 42 as answer")
    assert result[0]["answer"] == 42

    await client.close()
