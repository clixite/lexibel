# Graph AI System Architecture Diagram

## High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          CLIENT LAYER                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌────────────────┐  ┌────────────────┐  ┌─────────────────────┐       │
│  │  Graph View    │  │   Conflict     │  │  Risk Prediction    │       │
│  │  (Cytoscape)   │  │   Explorer     │  │     Panel           │       │
│  │                │  │   Dashboard    │  │                     │       │
│  │  - Force       │  │  - Severity    │  │  - ML Risk Score    │       │
│  │    Layout      │  │    Filters     │  │  - Recommendations  │       │
│  │  - Interactive │  │  - Path View   │  │  - What-If Analysis │       │
│  │  - Zoom/Pan    │  │  - AI Insights │  │                     │       │
│  └────────────────┘  └────────────────┘  └─────────────────────┘       │
│                                                                           │
│  React 18 + Next.js 14 + TanStack Query + Tailwind CSS                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTPS/REST
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          API LAYER (FastAPI)                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │              Graph Router (/api/v1/graph)                        │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │                                                                   │   │
│  │  GET  /case/{id}                        → Case Subgraph         │   │
│  │  GET  /case/{id}/conflicts/advanced     → Multi-Hop Detection   │   │
│  │  GET  /case/{id}/conflicts/predict/{e}  → ML Prediction         │   │
│  │  POST /sync/case/{id}                   → PostgreSQL Sync       │   │
│  │  GET  /network/stats                    → Network Analytics     │   │
│  │                                                                   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                     │
│                    ┌───────────────┼───────────────┐                    │
│                    ▼               ▼               ▼                    │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐      │
│  │ Conflict         │  │ Graph Sync       │  │ Graph RAG       │      │
│  │ Detection        │  │ Service          │  │ Service         │      │
│  │ Service          │  │                  │  │                 │      │
│  │                  │  │ - Event Queue    │  │ - NER Search    │      │
│  │ - 1-Hop Direct   │  │ - Async Worker   │  │ - Graph Context │      │
│  │ - 2-Hop Assoc.   │  │ - Auto Sync      │  │ - Similarity    │      │
│  │ - 3-Hop Network  │  │ - Retry Logic    │  │                 │      │
│  │ - Risk Scoring   │  │                  │  │                 │      │
│  │ - ML Prediction  │  │                  │  │                 │      │
│  └──────────────────┘  └──────────────────┘  └─────────────────┘      │
│           │                     │                      │                │
└───────────┼─────────────────────┼──────────────────────┼───────────────┘
            │                     │                      │
            ▼                     │                      ▼
┌──────────────────────┐          │           ┌──────────────────────┐
│   Graph Builder      │          │           │   NER Service        │
│                      │          │           │   (spaCy/Transformers)│
│ - Entity Extraction  │          │           │                      │
│ - Node Creation      │          │           │ - PERSON             │
│ - Relationship Map   │          │           │ - ORGANIZATION       │
│ - Conflict Check     │          │           │ - LEGAL_CONCEPT      │
└──────────────────────┘          │           └──────────────────────┘
                                  │
            ┌─────────────────────┼─────────────────────┐
            ▼                     ▼                     ▼
┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│                     │  │                     │  │                     │
│   Neo4j Graph DB    │  │   PostgreSQL DB     │  │   Vector Store      │
│   (Knowledge Graph) │  │   (Primary Data)    │  │   (Embeddings)      │
│                     │  │                     │  │                     │
├─────────────────────┤  ├─────────────────────┤  ├─────────────────────┤
│                     │  │                     │  │                     │
│  Nodes:             │  │  Tables:            │  │  Collections:       │
│  • Person           │  │  • cases            │  │  • case_embeddings  │
│  • Organization     │  │  • contacts         │  │  • document_chunks  │
│  • Case             │  │  • lawyers          │  │  • legal_concepts   │
│  • Court            │  │  • documents        │  │                     │
│  • Document         │  │  • deadlines        │  │                     │
│  • LegalConcept     │  │  • parties          │  │                     │
│  • Event            │  │  • relationships    │  │                     │
│                     │  │                     │  │                     │
│  Relationships:     │  │                     │  │                     │
│  • PARTY_TO         │  │  Sync Triggers:     │  │                     │
│  • REPRESENTS       │  │  • ON INSERT        │  │                     │
│  • OPPOSED_TO ⚠️    │  │  • ON UPDATE        │  │                     │
│  • RELATED_TO       │  │  • ON DELETE        │  │                     │
│  • FILED_AT         │  │                     │  │                     │
│  • MENTIONS         │  │  ↓ (triggers sync)  │  │                     │
│  • CITES            │  │                     │  │                     │
│                     │  │                     │  │                     │
│  Indexes:           │  │                     │  │                     │
│  • id               │  │                     │  │                     │
│  • tenant_id        │  │                     │  │                     │
│  • name             │  │                     │  │                     │
│                     │  │                     │  │                     │
└─────────────────────┘  └─────────────────────┘  └─────────────────────┘
```

---

## Conflict Detection Flow

```
┌──────────────┐
│  User Action │  (View case / Add party / Pre-engagement check)
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│  API Request: GET /case/{id}/conflicts/advanced              │
│  Params: max_depth=3, min_confidence=0.3                     │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
       ┌───────────────────────────────┐
       │  ConflictDetectionService     │
       └───────────────┬───────────────┘
                       │
       ┌───────────────┼───────────────┐
       │               │               │
       ▼               ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│  1-Hop      │ │  2-Hop      │ │  3-Hop      │
│  Detection  │ │  Detection  │ │  Detection  │
├─────────────┤ ├─────────────┤ ├─────────────┤
│             │ │             │ │             │
│ Direct      │ │ Associate   │ │ Network     │
│ Conflicts   │ │ Conflicts   │ │ Conflicts   │
│             │ │             │ │             │
│ Find:       │ │ Find:       │ │ Find:       │
│ • Same      │ │ • A→B→C     │ │ • Complex   │
│   entity    │ │   where     │ │   paths     │
│   with      │ │   A,C are   │ │ • Multiple  │
│   opposing  │ │   opposing  │ │   hops      │
│   roles     │ │             │ │             │
│             │ │             │ │             │
│ Severity:   │ │ Severity:   │ │ Severity:   │
│ CRITICAL    │ │ HIGH        │ │ MEDIUM      │
│             │ │             │ │             │
└─────┬───────┘ └─────┬───────┘ └─────┬───────┘
      │               │               │
      └───────────────┼───────────────┘
                      ▼
          ┌───────────────────────┐
          │  Risk Score Engine    │
          ├───────────────────────┤
          │                       │
          │  Score = (            │
          │    type_weight * 40 + │
          │    severity * 30 +    │
          │    centrality * 20 +  │
          │    confidence * 10    │
          │  ) * multiplier       │
          │                       │
          └───────────┬───────────┘
                      │
                      ▼
          ┌───────────────────────┐
          │  Generate Report      │
          ├───────────────────────┤
          │                       │
          │  • Total conflicts    │
          │  • By severity        │
          │  • By type            │
          │  • Conflict paths     │
          │  • Network analysis   │
          │  • AI recommendations │
          │                       │
          └───────────┬───────────┘
                      │
                      ▼
              ┌───────────────┐
              │  JSON Response│
              └───────────────┘
```

---

## PostgreSQL → Neo4j Sync Flow

```
┌─────────────────┐
│  PostgreSQL     │
│  Event          │
│                 │
│  INSERT/UPDATE/ │
│  DELETE on:     │
│  • cases        │
│  • contacts     │
│  • lawyers      │
│  • documents    │
└────────┬────────┘
         │
         │ (Trigger/Hook)
         │
         ▼
┌──────────────────────────┐
│  Sync Event Created      │
├──────────────────────────┤
│  SyncEvent {             │
│    entity_type: CASE     │
│    entity_id: "123"      │
│    operation: CREATE     │
│    data: {...}           │
│    tenant_id: "xyz"      │
│  }                       │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  Async Queue             │
│  (In-Memory FIFO)        │
│                          │
│  [Event1, Event2, ...]   │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  Sync Worker             │
│  (Background Process)    │
│                          │
│  while running:          │
│    event = queue.get()   │
│    process(event)        │
└──────────┬───────────────┘
           │
           ├─────────────────┐
           │                 │
           ▼                 ▼
  ┌────────────────┐  ┌────────────────┐
  │  sync_case()   │  │ sync_contact() │
  ├────────────────┤  ├────────────────┤
  │                │  │                │
  │ 1. Create      │  │ 1. Create      │
  │    Case node   │  │    Person/Org  │
  │                │  │    node        │
  │ 2. Create      │  │                │
  │    Court node  │  │ 2. Link to     │
  │                │  │    Organization│
  │ 3. Link parties│  │                │
  │    (PARTY_TO)  │  │ 3. Return      │
  │                │  │    result      │
  │ 4. Detect      │  │                │
  │    opposing    │  │                │
  │    sides       │  │                │
  │    (OPPOSED_TO)│  │                │
  │                │  │                │
  │ 5. Return      │  │                │
  │    result      │  │                │
  └────────┬───────┘  └────────┬───────┘
           │                   │
           └─────────┬─────────┘
                     │
                     ▼
            ┌────────────────┐
            │  Neo4j Graph   │
            │  Updated       │
            ├────────────────┤
            │                │
            │  New nodes:    │
            │  • Case        │
            │  • Persons     │
            │  • Court       │
            │                │
            │  New rels:     │
            │  • PARTY_TO    │
            │  • OPPOSED_TO  │
            │  • FILED_AT    │
            │                │
            └────────────────┘
```

---

## Multi-Hop Conflict Detection Algorithm

```
Input: case_id, tenant_id, max_depth=3

┌────────────────────────────────┐
│  Step 1: Get Case Subgraph     │
├────────────────────────────────┤
│                                │
│  MATCH (c:Case {id: $case_id}) │
│  MATCH path = (c)-[*1..3]-(n)  │
│  WHERE n.tenant_id = $tid      │
│  RETURN nodes, relationships   │
│                                │
└────────────┬───────────────────┘
             │
             ▼
┌────────────────────────────────┐
│  Step 2: 1-Hop Analysis        │
├────────────────────────────────┤
│                                │
│  For each entity:              │
│    Get all relationships       │
│    Check for opposing pairs:   │
│      REPRESENTS + OPPOSED_TO   │
│      PARTY_TO + OPPOSED_TO     │
│                                │
│  ↓                             │
│  John → REPRESENTS → Alice     │
│  John → REPRESENTS → Bob       │
│  Alice → OPPOSED_TO → Bob      │
│                                │
│  ⚠️ CONFLICT: John on both     │
│               sides!           │
│                                │
│  Severity: CRITICAL            │
│  Confidence: 0.9               │
│                                │
└────────────┬───────────────────┘
             │
             ▼
┌────────────────────────────────┐
│  Step 3: 2-Hop Analysis        │
├────────────────────────────────┤
│                                │
│  Build adjacency map           │
│  For each entity:              │
│    For each neighbor (1-hop):  │
│      For each neighbor of      │
│        neighbor (2-hop):       │
│        Check conflict pattern  │
│                                │
│  ↓                             │
│  Lawyer A → REPRESENTS → Org B │
│  Org B → BELONGS_TO → Person C │
│  Person C → OPPOSED_TO → ...   │
│                                │
│  ⚠️ CONFLICT: Through associate│
│                                │
│  Severity: HIGH                │
│  Confidence: 0.7               │
│                                │
└────────────┬───────────────────┘
             │
             ▼
┌────────────────────────────────┐
│  Step 4: 3-Hop Analysis        │
├────────────────────────────────┤
│                                │
│  Use graph.get_neighbors(      │
│    node_id, depth=3            │
│  )                             │
│                                │
│  Count opposing connections    │
│  If >= 2 opposing in network:  │
│    Flag as complex conflict    │
│                                │
│  Severity: MEDIUM              │
│  Confidence: 0.5               │
│                                │
└────────────┬───────────────────┘
             │
             ▼
┌────────────────────────────────┐
│  Step 5: Risk Scoring          │
├────────────────────────────────┤
│                                │
│  For each conflict:            │
│                                │
│    risk = (                    │
│      conflict_type_wt * 40 +   │
│      severity_score * 30 +     │
│      centrality * 20 +         │
│      confidence * 10           │
│    ) * case_multiplier         │
│                                │
│    Example:                    │
│    type_wt = 1.0 (direct opp)  │
│    severity = 1.0 (critical)   │
│    centrality = 0.8 (high)     │
│    confidence = 0.9            │
│    multiplier = 1.0            │
│                                │
│    risk = (1.0*40 + 1.0*30 +   │
│            0.8*20 + 0.9*10)    │
│         = 95.0                 │
│                                │
└────────────┬───────────────────┘
             │
             ▼
┌────────────────────────────────┐
│  Step 6: Generate Report       │
├────────────────────────────────┤
│                                │
│  ConflictReport {              │
│    total: 5                    │
│    by_severity: {              │
│      critical: 1,              │
│      high: 2,                  │
│      medium: 2                 │
│    }                           │
│    conflicts: [...]            │
│    recommendations: [          │
│      "URGENT: Critical..."     │
│    ]                           │
│  }                             │
│                                │
└────────────────────────────────┘

Output: Comprehensive conflict report
```

---

## Data Flow: From Document to Conflict Detection

```
┌──────────────┐
│  Upload      │
│  Document    │
│  (PDF/DOCX)  │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Extract     │
│  Text        │
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│  NER Service     │
│  (spaCy/LLM)     │
│                  │
│  Detect:         │
│  • PERSON        │
│  • ORGANIZATION  │
│  • COURT         │
│  • LEGAL_CONCEPT │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│  Graph Builder   │
│                  │
│  process_doc()   │
└──────┬───────────┘
       │
       ├──────────────────────┐
       │                      │
       ▼                      ▼
┌──────────────┐    ┌──────────────┐
│  Create      │    │  Create      │
│  Nodes       │    │  Relationships│
│              │    │              │
│  • Case      │    │  • MENTIONS  │
│  • Document  │    │  • PARTY_TO  │
│  • Person    │    │  • ATTACHED  │
│  • Org       │    │              │
└──────┬───────┘    └──────┬───────┘
       │                   │
       └────────┬──────────┘
                │
                ▼
       ┌─────────────────┐
       │  Neo4j Graph    │
       │  Updated        │
       └────────┬────────┘
                │
                │ (Auto-trigger)
                │
                ▼
       ┌─────────────────┐
       │  Conflict       │
       │  Detection      │
       │  Service        │
       └────────┬────────┘
                │
                ▼
       ┌─────────────────┐
       │  Alert if       │
       │  Critical       │
       │  Conflicts      │
       └─────────────────┘
```

---

## Network Topology Example

```
                    ┌──────────────┐
                    │  Case A      │
                    │  (Diamond)   │
                    └──────┬───────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           │ PARTY_TO      │ PARTY_TO      │ FILED_AT
           │               │               │
           ▼               ▼               ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │ Alice    │    │   Bob    │    │Superior  │
    │ Smith    │◄───┤  Jones   │    │Court     │
    │ (Circle) │    │ (Circle) │    │(Octagon) │
    └────┬─────┘    └────┬─────┘    └──────────┘
         │               │
         │ OPPOSED_TO ⚠️│
         └───────────────┘
         │
         │ REPRESENTED_BY
         │
         ▼
    ┌──────────┐
    │ Lawyer   │
    │ Sarah    │
    │ Attorney │
    │ (Circle) │
    └────┬─────┘
         │
         │ REPRESENTS (Case B)
         │
         ▼
    ┌──────────┐
    │   Eve    │◄──────OPPOSED_TO─────┐
    │  Miller  │                      │
    │ (Circle) │                      │
    └──────────┘                      │
                                 ┌────┴─────┐
                                 │  Frank   │
                                 │  Wilson  │
                                 │ (Circle) │
                                 └──────────┘

Legend:
━━━  Normal relationship
⚠️   Conflict indicator (OPPOSED_TO)
□    Case node (Diamond)
○    Person node (Circle)
⬡    Court node (Octagon)

Conflicts Detected:
1. Sarah represents Alice AND Bob (who are OPPOSED_TO each other)
   → CRITICAL: Direct opposition
   → Risk Score: 98.5

2. Sarah represents Alice (Case A) and Eve (Case B)
   Eve is OPPOSED_TO Frank
   → HIGH: Potential future conflict if Frank joins Case A
   → Risk Score: 72.0
```

---

This architecture supports:
- ✅ Real-time conflict detection
- ✅ Multi-hop relationship analysis
- ✅ Predictive risk assessment
- ✅ Scalable graph sync
- ✅ Visual analytics
- ✅ ML-powered insights
- ✅ Comprehensive audit trail
