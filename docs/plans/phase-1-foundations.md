# Phase 1: Foundations — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to execute this plan with parallel agents.

**Goal:** Set up all infrastructure (Neo4j, Qdrant, monitoring) and create 20 database models with migrations for the 4 innovations.

**Architecture:** Infrastructure-first approach. Databases → Models → Migrations → Monitoring → CI/CD.

**Tech Stack:** Neo4j 5.15, Qdrant 1.7, PostgreSQL 16, Redis 7, Prometheus, Grafana, Alembic, SQLAlchemy 2.0

**Duration:** 2 weeks (10 working days)

**Parallel Agents:** 10 agents working concurrently

---

## Task 1: Setup Neo4j for SENTINEL

**Agent:** Neo4j Setup Agent

**Files:**
- Create: `infra/neo4j/docker-compose.yml`
- Create: `infra/neo4j/.env.example`
- Create: `infra/neo4j/init.cypher`
- Create: `apps/api/services/neo4j_client.py`
- Create: `apps/api/tests/test_neo4j_client.py`

**Step 1: Create Neo4j docker-compose**

File: `infra/neo4j/docker-compose.yml`

```yaml
version: '3.8'

services:
  neo4j:
    image: neo4j:5.15-community
    container_name: lexibel-neo4j
    ports:
      - "7474:7474"  # HTTP
      - "7687:7687"  # Bolt
    environment:
      - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD}
      - NEO4J_PLUGINS=["apoc"]
      - NEO4J_dbms_memory_heap_max__size=2G
      - NEO4J_dbms_memory_pagecache_size=1G
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
      - ./init.cypher:/var/lib/neo4j/import/init.cypher
    networks:
      - lexibel

volumes:
  neo4j_data:
  neo4j_logs:

networks:
  lexibel:
    external: true
```

**Step 2: Create init schema**

File: `infra/neo4j/init.cypher`

```cypher
// Create constraints
CREATE CONSTRAINT person_id IF NOT EXISTS FOR (p:Person) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT company_id IF NOT EXISTS FOR (c:Company) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT lawyer_id IF NOT EXISTS FOR (l:Lawyer) REQUIRE l.id IS UNIQUE;
CREATE CONSTRAINT case_id IF NOT EXISTS FOR (c:Case) REQUIRE c.id IS UNIQUE;

// Create indexes
CREATE INDEX person_name IF NOT EXISTS FOR (p:Person) ON (p.name);
CREATE INDEX company_name IF NOT EXISTS FOR (c:Company) ON (c.name);
CREATE INDEX company_vat IF NOT EXISTS FOR (c:Company) ON (c.vat);
```

**Step 3: Write Neo4j client**

File: `apps/api/services/neo4j_client.py`

```python
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
```

**Step 4: Write test**

File: `apps/api/tests/test_neo4j_client.py`

```python
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
```

**Step 5: Run tests**

```bash
cd /f/LexiBel
docker compose -f infra/neo4j/docker-compose.yml up -d
sleep 10  # Wait for Neo4j to start
pytest apps/api/tests/test_neo4j_client.py -v
```

Expected: PASS (2 tests)

**Step 6: Commit**

```bash
git add infra/neo4j/ apps/api/services/neo4j_client.py apps/api/tests/test_neo4j_client.py
git commit -m "feat(infra): setup Neo4j 5.15 for SENTINEL graph database

- Docker Compose with APOC plugin
- Init schema with constraints and indexes
- Async Neo4j client with health check
- Connection tests

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Setup Qdrant for BRAIN

**Agent:** Qdrant Setup Agent

**Files:**
- Create: `infra/qdrant/docker-compose.yml`
- Create: `apps/api/services/qdrant_client.py`
- Create: `apps/api/tests/test_qdrant_client.py`

**Step 1: Create Qdrant docker-compose**

File: `infra/qdrant/docker-compose.yml`

```yaml
version: '3.8'

services:
  qdrant:
    image: qdrant/qdrant:v1.7.4
    container_name: lexibel-qdrant
    ports:
      - "6333:6333"  # HTTP
      - "6334:6334"  # gRPC
    volumes:
      - qdrant_storage:/qdrant/storage
    networks:
      - lexibel

volumes:
  qdrant_storage:

networks:
  lexibel:
    external: true
```

**Step 2: Write Qdrant client**

File: `apps/api/services/qdrant_client.py`

```python
"""Qdrant client for BRAIN vector search."""
import os
from qdrant_client import QdrantClient, AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from typing import Optional
import uuid

class QdrantVectorStore:
    """Async Qdrant client for embeddings."""

    def __init__(self):
        self.url = os.getenv("QDRANT_URL", "http://localhost:6333")
        self._client: Optional[AsyncQdrantClient] = None

    async def connect(self):
        """Connect to Qdrant."""
        self._client = AsyncQdrantClient(url=self.url)

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

    async def upsert(self, collection: str, id: str, vector: list[float], payload: dict):
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
        results = await self._client.search(
            collection_name=collection,
            query_vector=vector,
            limit=limit
        )
        return results

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
```

**Step 3: Write test**

File: `apps/api/tests/test_qdrant_client.py`

```python
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
    await client.upsert(
        "test_search",
        "test_id",
        [0.1, 0.2, 0.3],
        {"text": "test"}
    )

    # Search
    results = await client.search("test_search", [0.1, 0.2, 0.3], limit=1)
    assert len(results) == 1
    assert results[0].id == "test_id"

    await client.close()
```

**Step 4: Run tests**

```bash
docker compose -f infra/qdrant/docker-compose.yml up -d
sleep 5
pytest apps/api/tests/test_qdrant_client.py -v
```

Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add infra/qdrant/ apps/api/services/qdrant_client.py apps/api/tests/test_qdrant_client.py
git commit -m "feat(infra): setup Qdrant 1.7 for BRAIN vector search

- Docker Compose for Qdrant
- Async client with COSINE distance
- Collection management (create, upsert, search)
- Health check and tests

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 3: Setup Monitoring (Prometheus + Grafana)

**Agent:** Monitoring Setup Agent

**Files:**
- Create: `infra/monitoring/docker-compose.yml`
- Create: `infra/monitoring/prometheus.yml`
- Create: `infra/monitoring/grafana/dashboards/lexibel.json`
- Create: `apps/api/services/metrics.py`

**Step 1: Create monitoring docker-compose**

File: `infra/monitoring/docker-compose.yml`

```yaml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:v2.48.0
    container_name: lexibel-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    networks:
      - lexibel

  grafana:
    image: grafana/grafana:10.2.2
    container_name: lexibel-grafana
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_INSTALL_PLUGINS=
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
    networks:
      - lexibel

volumes:
  prometheus_data:
  grafana_data:

networks:
  lexibel:
    external: true
```

**Step 2: Create Prometheus config**

File: `infra/monitoring/prometheus.yml`

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'lexibel-api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/metrics'

  - job_name: 'neo4j'
    static_configs:
      - targets: ['neo4j:7474']
    metrics_path: '/metrics'

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
```

**Step 3: Create metrics service**

File: `apps/api/services/metrics.py`

```python
"""Prometheus metrics for LexiBel."""
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response

# API metrics
api_requests_total = Counter(
    'lexibel_api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status']
)

api_request_duration_seconds = Histogram(
    'lexibel_api_request_duration_seconds',
    'API request duration',
    ['method', 'endpoint']
)

# BRAIN metrics
brain_actions_total = Counter(
    'lexibel_brain_actions_total',
    'Total BRAIN actions',
    ['action_type', 'status']
)

brain_insights_total = Counter(
    'lexibel_brain_insights_total',
    'Total BRAIN insights',
    ['insight_type', 'severity']
)

# PROPHET metrics
prophet_predictions_total = Counter(
    'lexibel_prophet_predictions_total',
    'Total PROPHET predictions',
    ['prediction_type']
)

prophet_prediction_duration_seconds = Histogram(
    'lexibel_prophet_prediction_duration_seconds',
    'PROPHET prediction duration'
)

# SENTINEL metrics
sentinel_conflicts_detected = Counter(
    'lexibel_sentinel_conflicts_detected',
    'Total conflicts detected',
    ['conflict_type', 'severity']
)

sentinel_check_duration_seconds = Histogram(
    'lexibel_sentinel_check_duration_seconds',
    'SENTINEL conflict check duration'
)

# TIMELINE metrics
timeline_events_extracted = Counter(
    'lexibel_timeline_events_extracted',
    'Total timeline events extracted',
    ['source_type']
)

timeline_extraction_duration_seconds = Histogram(
    'lexibel_timeline_extraction_duration_seconds',
    'Timeline extraction duration'
)

# Database metrics
db_connections_active = Gauge(
    'lexibel_db_connections_active',
    'Active database connections',
    ['database']
)


async def metrics_endpoint():
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
```

**Step 4: Add metrics to main.py**

Modify: `apps/api/main.py`

```python
# Add at top
from apps.api.services.metrics import metrics_endpoint

# Add route
@app.get("/metrics")
async def metrics():
    """Prometheus metrics."""
    return await metrics_endpoint()
```

**Step 5: Start monitoring**

```bash
docker network create lexibel || true
docker compose -f infra/monitoring/docker-compose.yml up -d
```

**Step 6: Verify**

```bash
curl http://localhost:9090/-/healthy  # Prometheus
curl http://localhost:3001/api/health  # Grafana
```

Expected: Both return 200 OK

**Step 7: Commit**

```bash
git add infra/monitoring/ apps/api/services/metrics.py apps/api/main.py
git commit -m "feat(infra): setup Prometheus + Grafana monitoring

- Prometheus 2.48 for metrics collection
- Grafana 10.2 for dashboards
- Custom metrics for all 4 innovations
- /metrics endpoint on API

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 4-7: Create Database Models (BRAIN, PROPHET, SENTINEL, TIMELINE)

*Note: Ces 4 tâches peuvent être exécutées en parallèle par 4 agents différents.*

### Task 4: BRAIN Models

**Agent:** BRAIN Models Agent

**Files:**
- Create: `packages/db/models/brain_action.py`
- Create: `packages/db/models/brain_insight.py`
- Create: `packages/db/models/brain_memory.py`

File: `packages/db/models/brain_action.py`

```python
"""BRAIN action model."""
from sqlalchemy import Column, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from packages.db.base import Base
from packages.db.mixins import TenantMixin, TimestampMixin
import uuid

class BrainAction(Base, TenantMixin, TimestampMixin):
    """BRAIN action pending or executed."""

    __tablename__ = "brain_actions"

    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    action_type = Column(String(50), nullable=False, index=True)  # 'alert', 'draft', 'suggestion', 'auto_send'
    priority = Column(String(20), nullable=False, default='normal', index=True)  # 'critical', 'urgent', 'normal'
    status = Column(String(20), nullable=False, default='pending', index=True)  # 'pending', 'approved', 'rejected', 'executed'
    confidence_score = Column(Float, nullable=False)  # 0.0-1.0
    trigger_source = Column(String(50), nullable=False)  # 'call', 'email', 'document', 'deadline'
    trigger_id = Column(UUID(as_uuid=True), nullable=True)
    action_data = Column(JSONB, nullable=False, default=dict, server_default='{}')
    generated_content = Column(Text, nullable=True)
    executed_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    feedback = Column(Text, nullable=True)

    # Relationships
    case = relationship("Case", back_populates="brain_actions")
    reviewer = relationship("User", foreign_keys=[reviewed_by])
```

File: `packages/db/models/brain_insight.py`

```python
"""BRAIN insight model."""
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from packages.db.base import Base
from packages.db.mixins import TenantMixin, TimestampMixin

class BrainInsight(Base, TenantMixin, TimestampMixin):
    """BRAIN insight about a case."""

    __tablename__ = "brain_insights"

    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    insight_type = Column(String(50), nullable=False, index=True)  # 'risk', 'opportunity', 'contradiction', 'deadline'
    severity = Column(String(20), nullable=False, index=True)  # 'low', 'medium', 'high', 'critical'
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    evidence_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=False, default=list, server_default='{}')
    suggested_actions = Column(ARRAY(String), nullable=False, default=list, server_default='{}')
    dismissed = Column(Boolean, default=False, nullable=False)
    dismissed_at = Column(DateTime(timezone=True), nullable=True)
    dismissed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Relationships
    case = relationship("Case", back_populates="brain_insights")
```

File: `packages/db/models/brain_memory.py`

```python
"""BRAIN memory model for vector storage metadata."""
from sqlalchemy import Column, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from packages.db.base import Base
from packages.db.mixins import TenantMixin, TimestampMixin

class BrainMemory(Base, TenantMixin, TimestampMixin):
    """BRAIN memory for RAG (metadata, actual vectors in Qdrant)."""

    __tablename__ = "brain_memories"

    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    memory_type = Column(String(50), nullable=False, index=True)  # 'fact', 'preference', 'pattern', 'learning'
    content = Column(Text, nullable=False)
    qdrant_id = Column(String(100), nullable=False, unique=True)  # ID in Qdrant
    source_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=False, default=list, server_default='{}')
    confidence = Column(Float, nullable=False)  # 0.0-1.0

    # Relationships
    case = relationship("Case", back_populates="brain_memories")
```

**Test:** Create test file `apps/api/tests/test_brain_models.py`

```python
"""Tests for BRAIN models."""
import pytest
from packages.db.models.brain_action import BrainAction
from packages.db.models.brain_insight import BrainInsight
from packages.db.models.brain_memory import BrainMemory

def test_brain_action_model():
    """Test BrainAction model structure."""
    action = BrainAction(
        case_id="00000000-0000-0000-0000-000000000001",
        action_type="alert",
        priority="critical",
        confidence_score=0.95,
        trigger_source="call",
        action_data={"message": "test"}
    )
    assert action.action_type == "alert"
    assert action.confidence_score == 0.95

def test_brain_insight_model():
    """Test BrainInsight model structure."""
    insight = BrainInsight(
        case_id="00000000-0000-0000-0000-000000000001",
        insight_type="risk",
        severity="high",
        title="Test Risk",
        description="Test description"
    )
    assert insight.severity == "high"

def test_brain_memory_model():
    """Test BrainMemory model structure."""
    memory = BrainMemory(
        case_id="00000000-0000-0000-0000-000000000001",
        memory_type="fact",
        content="Test fact",
        qdrant_id="test_123",
        confidence=0.9
    )
    assert memory.confidence == 0.9
```

**Commit:**

```bash
git add packages/db/models/brain_*.py apps/api/tests/test_brain_models.py
git commit -m "feat(models): add BRAIN models (action, insight, memory)

- BrainAction: Actions pending/approved/executed
- BrainInsight: Insights (risk, opportunity, contradiction)
- BrainMemory: Vector memory metadata (actual vectors in Qdrant)
- Tests for model structure

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

### Task 5: PROPHET Models

**Agent:** PROPHET Models Agent

**Files:**
- Create: `packages/db/models/prophet_prediction.py`
- Create: `packages/db/models/prophet_simulation.py`

*(Similar detailed structure as Task 4 - omitted for brevity)*

---

### Task 6: SENTINEL Models

**Agent:** SENTINEL Models Agent

**Files:**
- Create: `packages/db/models/sentinel_conflict.py`
- Create: `packages/db/models/sentinel_entity.py`

*(Similar detailed structure as Task 4 - omitted for brevity)*

---

### Task 7: TIMELINE Models

**Agent:** TIMELINE Models Agent

**Files:**
- Create: `packages/db/models/timeline_event.py`
- Create: `packages/db/models/timeline_document.py`

*(Similar detailed structure as Task 4 - omitted for brevity)*

---

## Task 8: Create Alembic Migrations

**Agent:** Migrations Agent

**Files:**
- Create: `packages/db/migrations/versions/011_create_brain_tables.py`
- Create: `packages/db/migrations/versions/012_create_prophet_tables.py`
- Create: `packages/db/migrations/versions/013_create_sentinel_tables.py`
- Create: `packages/db/migrations/versions/014_create_timeline_tables.py`

**Step 1: Generate migration for BRAIN**

```bash
cd /f/LexiBel
alembic revision -m "create_brain_tables"
```

File: `packages/db/migrations/versions/011_create_brain_tables.py`

```python
"""create brain tables

Revision ID: 011
Revises: 010
Create Date: 2026-02-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None

def upgrade():
    # BrainAction
    op.create_table(
        'brain_actions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('action_type', sa.String(50), nullable=False, index=True),
        sa.Column('priority', sa.String(20), nullable=False, index=True),
        sa.Column('status', sa.String(20), nullable=False, index=True),
        sa.Column('confidence_score', sa.Float, nullable=False),
        sa.Column('trigger_source', sa.String(50), nullable=False),
        sa.Column('trigger_id', postgresql.UUID(as_uuid=True)),
        sa.Column('action_data', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('generated_content', sa.Text),
        sa.Column('executed_at', sa.DateTime(timezone=True)),
        sa.Column('reviewed_by', postgresql.UUID(as_uuid=True)),
        sa.Column('feedback', sa.Text),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id']),
    )
    op.create_index('idx_brain_actions_tenant_case', 'brain_actions', ['tenant_id', 'case_id'])

    # BrainInsight
    op.create_table(
        'brain_insights',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('insight_type', sa.String(50), nullable=False, index=True),
        sa.Column('severity', sa.String(20), nullable=False, index=True),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('evidence_ids', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), server_default='{}'),
        sa.Column('suggested_actions', postgresql.ARRAY(sa.String), server_default='{}'),
        sa.Column('dismissed', sa.Boolean, default=False),
        sa.Column('dismissed_at', sa.DateTime(timezone=True)),
        sa.Column('dismissed_by', postgresql.UUID(as_uuid=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['dismissed_by'], ['users.id']),
    )

    # BrainMemory
    op.create_table(
        'brain_memories',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('memory_type', sa.String(50), nullable=False, index=True),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('qdrant_id', sa.String(100), nullable=False, unique=True),
        sa.Column('source_ids', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), server_default='{}'),
        sa.Column('confidence', sa.Float, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
    )

def downgrade():
    op.drop_table('brain_memories')
    op.drop_table('brain_insights')
    op.drop_table('brain_actions')
```

**Step 2: Test migration**

```bash
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

Expected: All migrations successful

**Step 3: Commit**

```bash
git add packages/db/migrations/versions/011_*.py
git commit -m "feat(migrations): add BRAIN tables migration

- brain_actions: Actions pending/executed
- brain_insights: Insights for cases
- brain_memories: Vector memory metadata
- Indexes for performance

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

*(Similar migrations for PROPHET, SENTINEL, TIMELINE - omitted for brevity)*

---

## Task 9: Setup CI/CD Pipeline

**Agent:** CI/CD Agent

**Files:**
- Create: `.github/workflows/test.yml`
- Create: `.github/workflows/deploy-staging.yml`
- Modify: `.github/workflows/deploy.yml`

**Step 1: Create test workflow**

File: `.github/workflows/test.yml`

```yaml
name: Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: lexibel_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

      neo4j:
        image: neo4j:5.15-community
        env:
          NEO4J_AUTH: neo4j/testpassword
        ports:
          - 7687:7687

      qdrant:
        image: qdrant/qdrant:v1.7.4
        ports:
          - 6333:6333

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov

      - name: Run migrations
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/lexibel_test
        run: |
          alembic upgrade head

      - name: Run tests
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/lexibel_test
          REDIS_URL: redis://localhost:6379
          NEO4J_URI: bolt://localhost:7687
          NEO4J_PASSWORD: testpassword
          QDRANT_URL: http://localhost:6333
        run: |
          pytest apps/api/tests/ -v --cov=apps.api --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

**Step 2: Commit**

```bash
git add .github/workflows/
git commit -m "feat(ci): add GitHub Actions workflow for tests

- Runs on push to main/develop
- Services: PostgreSQL, Redis, Neo4j, Qdrant
- Runs migrations + pytest with coverage
- Uploads to Codecov

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 10: Documentation

**Agent:** Documentation Agent

**Files:**
- Create: `docs/infrastructure/README.md`
- Create: `docs/infrastructure/neo4j-setup.md`
- Create: `docs/infrastructure/qdrant-setup.md`
- Create: `docs/infrastructure/monitoring.md`
- Create: `docs/database/models-overview.md`

**Step 1: Create infrastructure README**

File: `docs/infrastructure/README.md`

```markdown
# Infrastructure Setup

This directory contains documentation for LexiBel infrastructure.

## Components

- **Neo4j 5.15** - Graph database for SENTINEL conflict detection
- **Qdrant 1.7** - Vector database for BRAIN memory/RAG
- **Prometheus 2.48** - Metrics collection
- **Grafana 10.2** - Dashboards

## Quick Start

```bash
# Create network
docker network create lexibel

# Start all infrastructure
docker compose -f infra/neo4j/docker-compose.yml up -d
docker compose -f infra/qdrant/docker-compose.yml up -d
docker compose -f infra/monitoring/docker-compose.yml up -d

# Verify
curl http://localhost:7474  # Neo4j browser
curl http://localhost:6333  # Qdrant
curl http://localhost:9090  # Prometheus
curl http://localhost:3001  # Grafana
```

## Environment Variables

```bash
# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# Qdrant
QDRANT_URL=http://localhost:6333

# Prometheus
PROMETHEUS_URL=http://localhost:9090
```

## See Also

- [Neo4j Setup](./neo4j-setup.md)
- [Qdrant Setup](./qdrant-setup.md)
- [Monitoring](./monitoring.md)
```

*(Additional detailed docs - omitted for brevity)*

**Step 2: Commit**

```bash
git add docs/infrastructure/ docs/database/
git commit -m "docs: add infrastructure and database documentation

- Infrastructure README with quick start
- Neo4j setup guide
- Qdrant setup guide
- Monitoring guide (Prometheus + Grafana)
- Database models overview

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Phase 1 Completion Checklist

- [ ] Neo4j running and accessible
- [ ] Qdrant running and accessible
- [ ] Prometheus + Grafana running
- [ ] 20 database models created
- [ ] 4 migrations created and tested
- [ ] CI/CD pipeline green
- [ ] All tests passing
- [ ] Documentation complete

## Success Criteria

- ✅ All infrastructure services healthy
- ✅ `alembic upgrade head` succeeds
- ✅ All model tests pass
- ✅ GitHub Actions workflow passes
- ✅ Metrics endpoint returns data
- ✅ Documentation complete and accurate

---

**Phase 1 Duration:** 2 weeks (80 hours)

**Next Phase:** Phase 2 - SENTINEL (Conflict Detection)
