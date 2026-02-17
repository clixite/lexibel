"""Neo4j client for SENTINEL graph operations."""
import os
from neo4j import AsyncGraphDatabase, AsyncDriver
from typing import Optional

class Neo4jClient:
    """Async Neo4j client."""

    def __init__(self):
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD")
        self._driver: Optional[AsyncDriver] = None

    async def connect(self):
        """Connect to Neo4j."""
        self._driver = AsyncGraphDatabase.driver(
            self.uri,
            auth=(self.user, self.password)
        )
        await self._driver.verify_connectivity()

    async def close(self):
        """Close connection."""
        if self._driver:
            await self._driver.close()

    async def execute_query(self, query: str, parameters: dict = None):
        """Execute Cypher query."""
        async with self._driver.session() as session:
            result = await session.run(query, parameters or {})
            return await result.data()

    async def health_check(self) -> bool:
        """Check if Neo4j is reachable."""
        try:
            result = await self.execute_query("RETURN 1 as health")
            return len(result) > 0
        except Exception:
            return False


# Singleton
_neo4j_client: Optional[Neo4jClient] = None

async def get_neo4j_client() -> Neo4jClient:
    """Get Neo4j client singleton."""
    global _neo4j_client
    if _neo4j_client is None:
        _neo4j_client = Neo4jClient()
        await _neo4j_client.connect()
    return _neo4j_client
