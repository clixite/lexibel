"""Neo4j client for SENTINEL graph operations."""

import asyncio
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from neo4j import AsyncGraphDatabase, AsyncDriver
except ImportError:
    AsyncGraphDatabase = None  # type: ignore[assignment,misc]
    AsyncDriver = None  # type: ignore[assignment,misc]
    logger.info("neo4j package not installed. Neo4j features will be unavailable.")


class Neo4jClient:
    """Async Neo4j client."""

    def __init__(self):
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD")
        self._driver: Optional[AsyncDriver] = None

    async def connect(self):
        """Connect to Neo4j."""
        if AsyncGraphDatabase is None:
            raise RuntimeError(
                "neo4j package is not installed. Install it with: pip install neo4j"
            )
        try:
            self._driver = AsyncGraphDatabase.driver(
                self.uri, auth=(self.user, self.password)
            )
            await self._driver.verify_connectivity()
        except Exception as e:
            # Cleanup driver on connection failure
            if self._driver:
                await self._driver.close()
                self._driver = None
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise

    async def close(self):
        """Close connection."""
        if self._driver:
            await self._driver.close()

    async def execute_query(self, query: str, parameters: dict = None):
        """Execute Cypher query."""
        if self._driver is None:
            raise RuntimeError("Neo4j client not connected. Call connect() first.")
        async with self._driver.session() as session:
            result = await session.run(query, parameters or {})
            return await result.data()

    async def health_check(self) -> bool:
        """Check if Neo4j is reachable."""
        try:
            result = await self.execute_query("RETURN 1 as health")
            return len(result) > 0
        except RuntimeError as e:
            logger.warning(f"Health check failed - client not connected: {e}")
            return False
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False


# Singleton
_neo4j_client: Optional[Neo4jClient] = None
_lock = asyncio.Lock()


async def get_neo4j_client() -> Neo4jClient:
    """Get Neo4j client singleton."""
    global _neo4j_client
    async with _lock:
        if _neo4j_client is None:
            _neo4j_client = Neo4jClient()
            await _neo4j_client.connect()
    return _neo4j_client
