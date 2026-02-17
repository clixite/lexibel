# Knowledge Graph & Conflict Detection System

## Overview

LexiBel's intelligent knowledge graph system powered by Neo4j with advanced multi-hop conflict detection, real-time PostgreSQL sync, and Graph ML capabilities.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────┐
│   PostgreSQL    │────▶│  Graph Sync      │────▶│   Neo4j     │
│   (Source DB)   │     │  Service         │     │  (Graph DB) │
└─────────────────┘     └──────────────────┘     └─────────────┘
                                                         │
                                                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Graph Services Layer                         │
├─────────────────────────────────────────────────────────────────┤
│  • Conflict Detection Service (Multi-hop, ML-powered)           │
│  • Graph RAG Service (Knowledge-enhanced retrieval)             │
│  • Graph Builder (NER extraction + graph population)            │
│  • Neo4j Service (Graph database interface)                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      REST API Endpoints                          │
│  GET  /graph/case/{id}/conflicts/advanced                       │
│  GET  /graph/case/{id}/conflicts/predict/{entity_id}            │
│  POST /graph/sync/case/{id}                                     │
│  GET  /graph/network/stats                                      │
└─────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Neo4j Service (`neo4j_service.py`)

**Purpose:** Low-level Neo4j database interface with tenant isolation.

**Node Types:**
- `Person` - Individuals (clients, lawyers, witnesses)
- `Organization` - Companies, law firms, government entities
- `Case` - Legal cases
- `Court` - Court systems
- `Document` - Case documents
- `LegalConcept` - Legal principles, statutes, precedents
- `Event` - Dates, deadlines, hearings
- `Location` - Geographic locations

**Relationship Types:**
- `PARTY_TO` - Entity is a party to a case
- `REPRESENTS` - Lawyer represents entity
- `OPPOSED_TO` - Entities are on opposing sides
- `RELATED_TO` - Generic relationship
- `REFERENCES` - Document/case references legal concept
- `OCCURRED_IN` - Event occurred at location
- `FILED_AT` - Case filed at court
- `MENTIONS` - Document mentions entity
- `CITES` - Legal citation
- `ATTACHED_TO` - Document attached to case
- `BELONGS_TO` - Person belongs to organization

**Features:**
- Tenant isolation via `tenant_id` property
- In-memory implementation for testing
- Production Neo4j driver support (bolt protocol)
- Cypher query execution
- Multi-hop graph traversal

### 2. Conflict Detection Service (`conflict_detection_service.py`)

**Purpose:** Advanced multi-hop conflict detection with ML-powered risk scoring.

**Conflict Types:**
- `DIRECT_OPPOSITION` - Representing both sides (Critical)
- `DUAL_REPRESENTATION` - Conflicting interests (High)
- `FORMER_CLIENT` - Past client conflict (Medium)
- `ASSOCIATE_CONFLICT` - Through associate network (Medium)
- `ORGANIZATIONAL` - Corporate structure conflict (Medium)
- `FAMILIAL` - Family relationship conflict (Low)
- `BUSINESS_INTEREST` - Financial interest conflict (Low)

**Detection Algorithms:**

**1-Hop (Direct Conflicts):**
```python
# Entity appears with opposing roles in same case
Client A ──PARTY_TO──▶ Case X ◀──OPPOSED_TO── Client B
         ◀─REPRESENTS─ Lawyer Y ──REPRESENTS─▶
```

**2-Hop (Associate Conflicts):**
```python
# Conflict through intermediary
Lawyer A ──REPRESENTS──▶ Client X ──BELONGS_TO──▶ Org Y
                                    ◀──OPPOSED_TO── Client Z
```

**3-Hop (Complex Network Conflicts):**
```python
# Multi-degree connections revealing hidden conflicts
A ──rel1──▶ B ──rel2──▶ C ──rel3──▶ D (opposing party)
```

**Risk Scoring Formula:**
```python
risk_score = (
    conflict_type_weight * 40 +
    severity_score * 30 +
    network_centrality * 20 +
    confidence * 10
) * case_multiplier

# Where:
# - conflict_type_weight: 1.0 (direct) to 0.3 (business interest)
# - severity_score: 1.0 (critical) to 0.2 (info)
# - network_centrality: 0.0-1.0 (how connected entity is)
# - confidence: 0.0-1.0 (detection confidence)
# - case_multiplier: 1.0 + (num_related_cases - 1) * 0.1
```

**Predictive Conflict Detection:**
- Graph similarity analysis
- Network overlap calculation
- Opposing relationship pattern matching
- Returns 0.0-1.0 probability of future conflict

### 3. Graph Sync Service (`graph_sync_service.py`)

**Purpose:** Real-time synchronization from PostgreSQL to Neo4j.

**Sync Strategies:**

**Event-Driven (Recommended for Production):**
```python
# PostgreSQL trigger → Message queue → Sync worker
async def on_case_update(case_id, data):
    event = SyncEvent(
        entity_type=EntityType.CASE,
        entity_id=case_id,
        operation=SyncOperation.UPDATE,
        data=data,
        tenant_id=tenant_id,
    )
    await sync_service.queue_sync(event)
```

**Manual Sync (Development/Recovery):**
```python
# Direct API calls for immediate sync
result = await sync_service.sync_case(case_id, case_data, tenant_id)
```

**Full Sync (Initial Setup):**
```python
# Bulk sync all entities from PostgreSQL
summary = await sync_service.full_sync_from_postgres(pg_conn, tenant_id)
```

**Sync Operations:**
- `CREATE` - Add new entity to graph
- `UPDATE` - Update existing entity properties
- `DELETE` - Remove entity and relationships

**Auto-Relationship Detection:**
- Identifies opposing parties (plaintiff vs defendant)
- Links lawyers to represented clients
- Creates document-case attachments
- Maps organizational hierarchies

### 4. Graph Builder (`graph_builder.py`)

**Purpose:** Extract entities from documents and build knowledge graph.

**Pipeline:**
```
Document Text
    │
    ▼
NER Extraction (spaCy/transformers)
    │
    ▼
Entity Normalization
    │
    ▼
Graph Node Creation/Merge
    │
    ▼
Relationship Creation
    │
    ▼
Conflict Detection
```

**Entity Extraction:**
- PERSON → Person node
- ORGANIZATION → Organization node
- COURT → Court node
- LOCATION → Location node
- LEGAL_REFERENCE → LegalConcept node
- DATE → Event node
- MONETARY_AMOUNT → Event node

**Node Merging:**
- Deduplicates entities by name + label + tenant
- Preserves relationships across documents
- Updates properties on entity merge

### 5. Graph RAG Service (`graph_rag_service.py`)

**Purpose:** Graph-enhanced Retrieval-Augmented Generation.

**Features:**
- Entity-aware search (NER extraction from queries)
- Multi-hop graph traversal for context
- Similar case finding (Jaccard similarity)
- Path extraction for explainability
- Text summary generation for LLM consumption

**Use Cases:**
- "Who else is involved with this contact?" → Graph traversal
- "Find similar cases" → Entity overlap analysis
- "What legal concepts apply?" → LegalConcept node search
- "Show me the relationship network" → Subgraph extraction

## API Endpoints

### Conflict Detection

#### Advanced Multi-Hop Detection
```http
GET /api/v1/graph/case/{case_id}/conflicts/advanced?max_depth=3&min_confidence=0.3
```

**Response:**
```json
{
  "case_id": "uuid",
  "total_conflicts": 5,
  "by_severity": {
    "critical": 1,
    "high": 2,
    "medium": 2
  },
  "by_type": {
    "direct_opposition": 1,
    "associate_conflict": 2,
    "organizational": 2
  },
  "conflicts": [
    {
      "conflict_id": "uuid",
      "entity_id": "person-123",
      "entity_name": "John Doe",
      "entity_type": "Person",
      "conflict_type": "direct_opposition",
      "severity": "critical",
      "confidence": 0.95,
      "risk_score": 98.5,
      "hop_distance": 1,
      "description": "Direct conflict: John Doe has opposing roles in case",
      "paths": [
        {
          "nodes": ["John Doe", "Case X"],
          "relationships": ["REPRESENTS", "OPPOSED_TO"],
          "description": "John Doe → REPRESENTS → Case X",
          "hops": 1
        }
      ],
      "network_centrality": 0.85,
      "recommendations": [
        "Review all case relationships immediately",
        "Consider withdrawing representation",
        "Consult ethics committee"
      ],
      "related_cases": ["case-x", "case-y"]
    }
  ],
  "network_analysis": {
    "total_entities": 25,
    "total_relationships": 48,
    "density": 0.15,
    "avg_degree": 3.2
  },
  "recommendations": [
    "URGENT: 1 critical conflict(s) detected. Immediate review required.",
    "Consider withdrawing representation or obtaining conflict waivers."
  ],
  "report_generated_at": "2026-02-17T10:30:00Z"
}
```

#### Predictive Conflict Detection
```http
GET /api/v1/graph/case/{case_id}/conflicts/predict/{new_entity_id}
```

**Response:**
```json
{
  "case_id": "case-123",
  "entity_id": "person-456",
  "risk_probability": 0.72,
  "risk_level": "high",
  "recommendations": [
    "Significant conflict risk",
    "Conduct thorough conflict check",
    "Document decision process"
  ],
  "analysis_timestamp": "2026-02-17T10:35:00Z"
}
```

### Graph Sync

#### Sync Case
```http
POST /api/v1/graph/sync/case/{case_id}
Content-Type: application/json

{
  "title": "Smith v. Jones",
  "case_number": "2026-CV-12345",
  "status": "active",
  "court_id": "court-1",
  "court_name": "Superior Court",
  "filing_date": "2026-01-15",
  "parties": [
    {
      "contact_id": "contact-1",
      "name": "Alice Smith",
      "role": "plaintiff",
      "side": "plaintiff"
    },
    {
      "contact_id": "contact-2",
      "name": "Bob Jones",
      "role": "defendant",
      "side": "defendant"
    }
  ]
}
```

#### Sync Contact
```http
POST /api/v1/graph/sync/contact/{contact_id}

{
  "name": "Alice Smith",
  "type": "person",
  "email": "alice@example.com",
  "organization_id": "org-1",
  "organization_name": "Acme Corp"
}
```

### Network Statistics
```http
GET /api/v1/graph/network/stats
```

**Response:**
```json
{
  "tenant_id": "tenant-123",
  "total_nodes": 1250,
  "total_relationships": 3480,
  "nodes_by_type": {
    "Person": 450,
    "Organization": 200,
    "Case": 300,
    "Document": 250,
    "Court": 25,
    "LegalConcept": 25
  },
  "relationships_by_type": {
    "PARTY_TO": 600,
    "REPRESENTS": 450,
    "OPPOSED_TO": 300,
    "ATTACHED_TO": 250,
    "MENTIONS": 1200,
    "FILED_AT": 300
  },
  "network_density": 0.0022,
  "most_connected_entities": [
    {
      "entity_id": "lawyer-5",
      "entity_name": "Sarah Attorney",
      "entity_type": "Person",
      "connection_count": 85
    }
  ],
  "stats_generated_at": "2026-02-17T10:40:00Z"
}
```

## Best Practices (2026)

### Performance Optimization

**1. Incremental Sync:**
```python
# Only sync changed entities, not entire database
await sync_service.queue_sync(SyncEvent(
    entity_type=EntityType.CASE,
    entity_id=case_id,
    operation=SyncOperation.UPDATE,
    data=changed_fields_only,
    tenant_id=tenant_id,
))
```

**2. Batch Operations:**
```python
# Batch multiple graph operations
with driver.session() as session:
    with session.begin_transaction() as tx:
        for entity in entities:
            tx.run("CREATE (...)")
        tx.commit()
```

**3. Index Optimization:**
```cypher
-- Create indexes for fast lookups
CREATE INDEX node_id IF NOT EXISTS FOR (n:Person) ON (n.id);
CREATE INDEX tenant_isolation IF NOT EXISTS FOR (n:Case) ON (n.tenant_id);
CREATE INDEX name_search IF NOT EXISTS FOR (n:Person) ON (n.name);
```

**4. Query Caching:**
```python
# Cache frequent conflict detection results
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_cached_conflicts(case_id: str, tenant_id: str):
    return detector.detect_all_conflicts(case_id, tenant_id)
```

### Security

**1. Tenant Isolation:**
```cypher
-- ALL queries must filter by tenant_id
MATCH (n {tenant_id: $tenant_id})
WHERE n.id = $id
RETURN n
```

**2. Row-Level Security:**
```python
# Verify user has access to tenant before graph operations
if current_user["tenant_id"] != requested_tenant_id:
    raise HTTPException(403, "Access denied")
```

### Monitoring

**1. Sync Health:**
```python
# Track sync queue depth and processing time
metrics = {
    "queue_depth": sync_service._sync_queue.qsize(),
    "avg_processing_time_ms": calculate_avg(),
    "failed_syncs_last_hour": count_failures(),
}
```

**2. Conflict Detection Metrics:**
```python
# Monitor conflict detection performance
{
    "avg_conflicts_per_case": 2.3,
    "critical_conflicts_today": 5,
    "detection_latency_ms": 150,
}
```

## Future Enhancements

### Graph ML (2026+)

**1. Link Prediction:**
```python
# Predict missing relationships
model = GraphSAGE(...)
predicted_links = model.predict_links(graph, node_pairs)
```

**2. Node Classification:**
```python
# Automatically classify entity types
classifier = GCN(...)
entity_type = classifier.predict(node_features)
```

**3. Community Detection:**
```python
# Find groups of related entities
communities = louvain_algorithm(graph)
for community in communities:
    analyze_conflict_patterns(community)
```

### Temporal Graphs

**Track relationships over time:**
```cypher
CREATE (a)-[:REPRESENTED {
    from_date: "2025-01-01",
    to_date: "2025-12-31"
}]->(b)

// Query conflicts at specific point in time
MATCH path = (a)-[r:REPRESENTED]->(b)
WHERE r.from_date <= $query_date <= r.to_date
RETURN path
```

### Visual Analytics

**Interactive graph visualization:**
- Force-directed layout (D3.js)
- Conflict heatmap overlay
- Timeline slider (conflicts over time)
- Filter by relationship type
- Export to PDF reports

## Troubleshooting

### Common Issues

**1. Sync Lag:**
```bash
# Check sync queue depth
curl /api/v1/graph/sync/health

# Increase worker threads
sync_service = GraphSyncService(worker_threads=4)
```

**2. False Positive Conflicts:**
```python
# Adjust confidence threshold
report = detector.detect_all_conflicts(
    case_id, tenant_id,
    min_confidence=0.5,  # Increase from 0.3
)
```

**3. Graph Performance:**
```cypher
-- Analyze slow queries
PROFILE MATCH (n:Person)-[:REPRESENTS]->(c:Case)
WHERE n.tenant_id = $tid
RETURN n, c
```

## License

Copyright © 2026 LexiBel. All rights reserved.
