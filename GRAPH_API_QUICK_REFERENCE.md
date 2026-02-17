# Graph API Quick Reference

## 🚀 Quick Start

### Basic Conflict Check
```bash
curl -X GET "/api/v1/graph/case/{case_id}/conflicts/advanced?max_depth=3" \
  -H "Authorization: Bearer $TOKEN"
```

### Predict Conflict Risk
```bash
curl -X GET "/api/v1/graph/case/{case_id}/conflicts/predict/{entity_id}" \
  -H "Authorization: Bearer $TOKEN"
```

### Sync Case to Graph
```bash
curl -X POST "/api/v1/graph/sync/case/{case_id}" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "...", "parties": [...]}'
```

---

## 📡 All Endpoints

### Graph Visualization
```
GET  /api/v1/graph/case/{id}                      # Case subgraph
GET  /api/v1/graph/entity/{id}/connections        # Entity neighborhood
GET  /api/v1/graph/network/stats                  # Network statistics
```

### Conflict Detection
```
GET  /api/v1/graph/case/{id}/conflicts            # Basic conflicts
GET  /api/v1/graph/case/{id}/conflicts/advanced   # Multi-hop (2026)
GET  /api/v1/graph/case/{id}/conflicts/predict/{entity_id}  # ML prediction
```

### Graph RAG
```
POST /api/v1/graph/search                         # Graph-enhanced search
GET  /api/v1/graph/case/{id}/similar              # Similar cases
```

### Graph Sync
```
POST /api/v1/graph/sync/case/{id}                 # Sync case
POST /api/v1/graph/sync/contact/{id}              # Sync contact
POST /api/v1/graph/build/{id}                     # Build from documents
```

---

## 🎯 Common Use Cases

### 1. Full Conflict Analysis
```python
# Backend
from apps.api.services.graph.conflict_detection_service import ConflictDetectionService

detector = ConflictDetectionService()
report = detector.detect_all_conflicts(
    case_id="case-123",
    tenant_id="tenant-xyz",
    max_depth=3,
    min_confidence=0.3,
)

print(f"Found {report.total_conflicts} conflicts")
for conflict in report.conflicts:
    print(f"- {conflict.entity_name}: {conflict.severity} ({conflict.risk_score}/100)")
```

```typescript
// Frontend
import { useConflictDetection } from '@/hooks/useConflictDetection';

const { data: report } = useConflictDetection(caseId, 3, 0.3);

{report?.conflicts.map(c => (
  <ConflictCard key={c.conflict_id} conflict={c} />
))}
```

### 2. Pre-Engagement Check
```python
# Check if adding new client creates conflict
detector = ConflictDetectionService()
risk = detector.predict_future_conflicts(
    case_id="new-case-123",
    new_entity_id="prospective-client-456",
    tenant_id="tenant-xyz",
)

if risk > 0.7:
    print("⚠️ HIGH CONFLICT RISK - Ethics review required")
elif risk > 0.4:
    print("⚡ Medium risk - Proceed with caution")
else:
    print("✅ Low risk - Safe to proceed")
```

### 3. Auto-Sync on Case Update
```python
# In your case service
from apps.api.services.graph.graph_sync_service import SyncEvent, SyncOperation, EntityType

async def update_case(case_id: str, data: dict):
    # 1. Update PostgreSQL
    case = await db.update(case_id, data)

    # 2. Queue graph sync
    await sync_service.queue_sync(SyncEvent(
        entity_type=EntityType.CASE,
        entity_id=str(case.id),
        operation=SyncOperation.UPDATE,
        data={
            "title": case.title,
            "parties": [{"contact_id": p.contact_id, "role": p.role} for p in case.parties],
        },
        tenant_id=str(case.tenant_id),
    ))

    # 3. Auto-detect conflicts
    detector = ConflictDetectionService()
    report = detector.detect_all_conflicts(str(case.id), str(case.tenant_id))

    if any(c.severity == "critical" for c in report.conflicts):
        await send_conflict_alert(case, report)

    return case
```

---

## 🔍 Query Examples

### Cypher (Neo4j)

#### Find All Conflicts
```cypher
MATCH (lawyer:Person {role: 'lawyer'})-[:REPRESENTS]->(client1:Person),
      (lawyer)-[:REPRESENTS]->(client2:Person),
      (client1)-[:OPPOSED_TO]->(client2)
WHERE lawyer.tenant_id = $tenant_id
RETURN lawyer.name AS conflict_lawyer,
       client1.name AS party_a,
       client2.name AS party_b
```

#### 2-Hop Associate Conflicts
```cypher
MATCH path = (a:Person)-[r1:REPRESENTS]->(b)-[r2:BELONGS_TO]->(org:Organization),
             (org)<-[:BELONGS_TO]-(c)<-[r3:OPPOSED_TO]-(d)
WHERE a.tenant_id = $tenant_id
RETURN path, length(path) AS hops
```

#### Network Centrality
```cypher
MATCH (n:Person {tenant_id: $tenant_id})-[r]-()
WITH n, count(r) AS degree
ORDER BY degree DESC
LIMIT 10
RETURN n.name AS entity, degree
```

---

## 🎨 Response Schemas

### ConflictReportResponse
```typescript
{
  case_id: string;
  total_conflicts: number;
  by_severity: {
    critical: number;
    high: number;
    medium: number;
    low: number;
    info: number;
  };
  by_type: {
    direct_opposition: number;
    associate_conflict: number;
    // ... etc
  };
  conflicts: AdvancedConflict[];
  network_analysis: {
    total_entities: number;
    total_relationships: number;
    density: number;
    avg_degree: number;
  };
  recommendations: string[];
  report_generated_at: string;
}
```

### AdvancedConflict
```typescript
{
  conflict_id: string;
  entity_id: string;
  entity_name: string;
  entity_type: 'Person' | 'Organization';
  conflict_type: 'direct_opposition' | 'dual_representation' | /* ... */;
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  confidence: number;        // 0.0-1.0
  risk_score: number;        // 0-100
  hop_distance: number;      // 1-5
  description: string;
  paths: ConflictPath[];
  network_centrality: number; // 0.0-1.0
  recommendations: string[];
  related_cases: string[];
}
```

### ConflictPath
```typescript
{
  nodes: string[];           // ['Alice', 'Bob', 'Case X']
  relationships: string[];   // ['REPRESENTS', 'OPPOSED_TO']
  description: string;       // Human-readable path
  hops: number;             // Path length
}
```

---

## ⚡ Performance Tips

### 1. Cache Conflict Results
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_conflicts_cached(case_id: str, tenant_id: str):
    return detector.detect_all_conflicts(case_id, tenant_id)
```

### 2. Batch Sync Operations
```python
# Queue multiple syncs at once
events = [
    SyncEvent(EntityType.CASE, case_id, SyncOperation.UPDATE, data, tenant_id)
    for case_id, data in updated_cases
]

for event in events:
    await sync_service.queue_sync(event)
```

### 3. Limit Graph Depth for Performance
```python
# For quick checks, use depth=2
report = detector.detect_all_conflicts(case_id, tenant_id, max_depth=2)

# For comprehensive analysis, use depth=3-4
report = detector.detect_all_conflicts(case_id, tenant_id, max_depth=3)
```

---

## 🐛 Troubleshooting

### No Conflicts Detected (Expected Some)
```python
# Check if case is in graph
graph = get_graph()
nodes, rels = graph.get_case_subgraph(case_id, tenant_id)
print(f"Nodes: {len(nodes)}, Relationships: {len(rels)}")

# Verify sync status
result = await sync_service.sync_case(case_id, case_data, tenant_id)
print(f"Synced: {result.nodes_affected} nodes, {result.relationships_affected} rels")
```

### False Positive Conflicts
```python
# Increase confidence threshold
report = detector.detect_all_conflicts(
    case_id, tenant_id,
    min_confidence=0.5,  # Default is 0.3
)
```

### Slow Performance
```python
# Reduce depth for faster queries
report = detector.detect_all_conflicts(
    case_id, tenant_id,
    max_depth=2,  # Instead of 3
)

# Check Neo4j indexes
# Run in Neo4j Browser:
# CALL db.indexes()
```

---

## 🔒 Security Checklist

- [ ] Always filter by `tenant_id` in queries
- [ ] Validate user has access to tenant before graph operations
- [ ] Sanitize input in Cypher queries (use parameterized queries)
- [ ] Rate limit conflict detection endpoints
- [ ] Log all graph modifications for audit trail
- [ ] Encrypt sensitive properties in graph
- [ ] Use read-only graph connections for reports

---

## 📊 Metrics to Monitor

```python
{
    "conflict_detection": {
        "avg_conflicts_per_case": 2.3,
        "critical_conflicts_today": 5,
        "detection_latency_ms": 150,
    },
    "graph_sync": {
        "queue_depth": 0,
        "avg_processing_time_ms": 50,
        "failed_syncs_last_hour": 0,
    },
    "graph_health": {
        "total_nodes": 1250,
        "total_relationships": 3480,
        "avg_query_time_ms": 85,
    }
}
```

---

## 🎓 Learning Resources

**Internal Docs:**
- `F:/LexiBel/apps/api/services/graph/README.md` - Complete API reference
- `F:/LexiBel/GRAPH_FRONTEND_GUIDE.md` - Frontend implementation
- `F:/LexiBel/BRAIN4_GRAPH_AI_SUMMARY.md` - Full system overview

**External:**
- [Neo4j Cypher Manual](https://neo4j.com/docs/cypher-manual/)
- [Graph Data Science Library](https://neo4j.com/docs/graph-data-science/)
- [Cytoscape.js Documentation](https://js.cytoscape.org/)

---

## 💡 Pro Tips

1. **Start with depth=2** for most conflict checks (faster, catches 90% of issues)
2. **Use depth=3+** only for high-stakes cases or comprehensive audits
3. **Cache network stats** as they change infrequently
4. **Sync incrementally** rather than full re-sync
5. **Set up monitoring** for critical conflict alerts
6. **Test with realistic data** - small graphs don't reveal performance issues
7. **Use graph visualization** for debugging complex conflicts
8. **Document conflict waivers** in graph as properties

---

**Quick Help:**
- Backend issues → Check `F:/LexiBel/apps/api/services/graph/README.md`
- Frontend setup → See `F:/LexiBel/GRAPH_FRONTEND_GUIDE.md`
- API reference → This file
- Full overview → `F:/LexiBel/BRAIN4_GRAPH_AI_SUMMARY.md`
