# Qdrant Vector Database Setup

Qdrant powers the semantic search and RAG (Retrieval Augmented Generation) capabilities in LexiBel.

## Overview

- **Version**: Qdrant latest (1.7+)
- **Purpose**: Vector embeddings storage for semantic search
- **Use Cases**:
  - Document chunk similarity search
  - Case precedent retrieval
  - Semantic email search
  - RAG context retrieval for AI agents

## Docker Compose Configuration

```yaml
qdrant:
  image: qdrant/qdrant:latest
  ports:
    - "6333:6333"  # REST API
    - "6334:6334"  # gRPC API
  volumes:
    - qdrant_data:/qdrant/storage
  restart: unless-stopped
```

## Quick Start

### 1. Start Qdrant

```bash
cd /f/LexiBel
docker compose up -d qdrant
```

### 2. Access Dashboard

Open `http://localhost:6333/dashboard` in your browser.

### 3. Verify Installation

```bash
curl http://localhost:6333/healthz
```

Response: `{"title":"healthz","version":"1.7.4"}`

## Collection Structure

LexiBel uses multiple collections for different data types:

### 1. Document Chunks Collection

**Name**: `lexibel_chunks`

**Vector Configuration**:
- Size: 1536 (OpenAI `text-embedding-3-small`)
- Distance: Cosine

**Payload Schema**:
```json
{
  "chunk_id": "uuid",
  "tenant_id": "uuid",
  "case_id": "uuid",
  "document_id": "uuid",
  "content": "text",
  "chunk_index": 0,
  "metadata": {}
}
```

### 2. Email Collection

**Name**: `lexibel_emails`

**Vector Configuration**:
- Size: 1536
- Distance: Cosine

**Payload Schema**:
```json
{
  "email_id": "uuid",
  "tenant_id": "uuid",
  "subject": "text",
  "body": "text",
  "sender": "email",
  "sent_at": "timestamp"
}
```

### 3. Case Precedents Collection

**Name**: `lexibel_precedents`

**Vector Configuration**:
- Size: 1536
- Distance: Cosine

**Payload Schema**:
```json
{
  "case_id": "uuid",
  "tenant_id": "uuid",
  "case_type": "string",
  "outcome": "string",
  "summary": "text"
}
```

## Collection Creation

### Via REST API

```bash
# Create document chunks collection
curl -X PUT 'http://localhost:6333/collections/lexibel_chunks' \
  -H 'Content-Type: application/json' \
  -d '{
    "vectors": {
      "size": 1536,
      "distance": "Cosine"
    },
    "optimizers_config": {
      "indexing_threshold": 20000
    }
  }'
```

### Via Python Client

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

client = QdrantClient(url="http://localhost:6333")

# Create collection
client.create_collection(
    collection_name="lexibel_chunks",
    vectors_config=VectorParams(
        size=1536,
        distance=Distance.COSINE
    )
)
```

## Python Client Usage

### Installation

```bash
pip install qdrant-client
```

### Basic Operations

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import uuid

# Initialize client
client = QdrantClient(url="http://localhost:6333")

# Create collection
client.create_collection(
    collection_name="lexibel_chunks",
    vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
)

# Insert vectors
points = [
    PointStruct(
        id=str(uuid.uuid4()),
        vector=[0.1] * 1536,  # Replace with actual embedding
        payload={
            "chunk_id": str(uuid.uuid4()),
            "tenant_id": str(uuid.uuid4()),
            "content": "This is a legal document chunk...",
            "chunk_index": 0
        }
    )
]

client.upsert(
    collection_name="lexibel_chunks",
    points=points
)

# Search
results = client.search(
    collection_name="lexibel_chunks",
    query_vector=[0.1] * 1536,  # Replace with query embedding
    limit=10,
    query_filter={
        "must": [
            {"key": "tenant_id", "match": {"value": "tenant-uuid"}}
        ]
    }
)

for result in results:
    print(f"Score: {result.score}, Content: {result.payload['content']}")
```

### Advanced Filtering

```python
from qdrant_client.models import Filter, FieldCondition, MatchValue

# Search with multiple filters
results = client.search(
    collection_name="lexibel_chunks",
    query_vector=query_embedding,
    query_filter=Filter(
        must=[
            FieldCondition(
                key="tenant_id",
                match=MatchValue(value="tenant-uuid")
            ),
            FieldCondition(
                key="case_id",
                match=MatchValue(value="case-uuid")
            )
        ]
    ),
    limit=5
)
```

### Batch Operations

```python
# Batch upsert for performance
points = []
for i, (embedding, chunk) in enumerate(chunks):
    points.append(
        PointStruct(
            id=str(uuid.uuid4()),
            vector=embedding,
            payload={
                "chunk_id": chunk.id,
                "tenant_id": chunk.tenant_id,
                "content": chunk.content,
                "chunk_index": i
            }
        )
    )

# Upload in batches of 100
batch_size = 100
for i in range(0, len(points), batch_size):
    client.upsert(
        collection_name="lexibel_chunks",
        points=points[i:i + batch_size]
    )
```

## RAG Integration

### Semantic Search for RAG Context

```python
def get_rag_context(
    client: QdrantClient,
    query: str,
    tenant_id: str,
    case_id: str | None = None,
    limit: int = 5
) -> list[dict]:
    """
    Retrieve relevant document chunks for RAG context.

    Args:
        client: Qdrant client
        query: User query
        tenant_id: Tenant UUID
        case_id: Optional case UUID for filtering
        limit: Number of results

    Returns:
        List of relevant chunks with scores
    """
    # Get query embedding (pseudo-code, use actual embedding model)
    from openai import OpenAI
    openai_client = OpenAI()

    response = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=query
    )
    query_vector = response.data[0].embedding

    # Build filter
    must_conditions = [
        FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))
    ]
    if case_id:
        must_conditions.append(
            FieldCondition(key="case_id", match=MatchValue(value=case_id))
        )

    # Search
    results = client.search(
        collection_name="lexibel_chunks",
        query_vector=query_vector,
        query_filter=Filter(must=must_conditions),
        limit=limit
    )

    # Format results
    return [
        {
            "content": result.payload["content"],
            "score": result.score,
            "chunk_id": result.payload["chunk_id"],
            "document_id": result.payload.get("document_id")
        }
        for result in results
    ]
```

### Usage in RAG Pipeline

```python
# 1. Retrieve context
context_chunks = get_rag_context(
    client=qdrant_client,
    query="What are the payment terms?",
    tenant_id="tenant-uuid",
    case_id="case-uuid",
    limit=3
)

# 2. Build prompt with context
context_text = "\n\n".join([chunk["content"] for chunk in context_chunks])
prompt = f"""
Context:
{context_text}

Question: What are the payment terms?

Answer based on the context provided:
"""

# 3. Generate response with LLM
from openai import OpenAI
openai_client = OpenAI()

response = openai_client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": "You are a legal AI assistant."},
        {"role": "user", "content": prompt}
    ]
)

print(response.choices[0].message.content)
```

## Performance Optimization

### 1. Indexing Configuration

```python
from qdrant_client.models import OptimizersConfigDiff

client.update_collection(
    collection_name="lexibel_chunks",
    optimizer_config=OptimizersConfigDiff(
        indexing_threshold=20000,  # Start indexing after 20k vectors
        max_optimization_threads=4
    )
)
```

### 2. Quantization for Reduced Memory

```python
from qdrant_client.models import ScalarQuantization, ScalarQuantizationConfig, ScalarType

client.update_collection(
    collection_name="lexibel_chunks",
    quantization_config=ScalarQuantization(
        scalar=ScalarQuantizationConfig(
            type=ScalarType.INT8,
            quantile=0.99,
            always_ram=True
        )
    )
)
```

### 3. HNSW Parameters

```python
from qdrant_client.models import HnswConfigDiff

client.update_collection(
    collection_name="lexibel_chunks",
    hnsw_config=HnswConfigDiff(
        m=16,  # Number of edges per node
        ef_construct=100  # Size of dynamic list for construction
    )
)
```

## Health Checks

### Via REST API

```bash
curl http://localhost:6333/healthz
```

### Via Python

```python
from qdrant_client import QdrantClient

client = QdrantClient(url="http://localhost:6333")

# Check connection
collections = client.get_collections()
print(f"Connected! Collections: {collections}")
```

## Monitoring

### Collection Info

```bash
curl http://localhost:6333/collections/lexibel_chunks
```

```python
client = QdrantClient(url="http://localhost:6333")

info = client.get_collection("lexibel_chunks")
print(f"Vectors count: {info.points_count}")
print(f"Segments count: {info.segments_count}")
print(f"Status: {info.status}")
```

### Metrics Endpoint

Qdrant exposes Prometheus metrics:

```bash
curl http://localhost:6333/metrics
```

## Backup & Restore

### Create Snapshot

```bash
curl -X POST 'http://localhost:6333/collections/lexibel_chunks/snapshots'
```

Response:
```json
{
  "result": {
    "name": "lexibel_chunks-2026-02-17-12-00-00.snapshot"
  }
}
```

### Download Snapshot

```bash
curl -O 'http://localhost:6333/collections/lexibel_chunks/snapshots/lexibel_chunks-2026-02-17-12-00-00.snapshot'
```

### Restore Snapshot

```bash
curl -X PUT 'http://localhost:6333/collections/lexibel_chunks/snapshots/upload' \
  -H 'Content-Type: multipart/form-data' \
  -F 'snapshot=@lexibel_chunks-2026-02-17-12-00-00.snapshot'
```

## Troubleshooting

### Connection Refused

Verify Qdrant is running:

```bash
docker compose ps qdrant
docker compose logs qdrant
```

### Slow Search Queries

1. Enable indexing: Ensure collection has enough vectors
2. Use quantization to reduce memory usage
3. Adjust HNSW parameters (`m`, `ef_construct`)
4. Add payload indexes for filtered queries

### Out of Memory

Reduce vector dimensions or enable quantization:

```python
from qdrant_client.models import ScalarQuantization, ScalarQuantizationConfig

client.update_collection(
    collection_name="lexibel_chunks",
    quantization_config=ScalarQuantization(
        scalar=ScalarQuantizationConfig(type=ScalarType.INT8)
    )
)
```

## Resources

- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Python Client](https://github.com/qdrant/qdrant-client)
- [Best Practices](https://qdrant.tech/documentation/guides/common-errors/)
- [Filtering Guide](https://qdrant.tech/documentation/concepts/filtering/)
