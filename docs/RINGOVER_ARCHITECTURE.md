# Ringover Integration — Architecture Deep Dive

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          RINGOVER PLATFORM                              │
│  (VoIP Provider - Call Events, Recordings, User Management)            │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             │ HTTPS Webhook (HMAC-SHA256 Signed)
                             │ Events: call.answered, call.missed, voicemail
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       EDGE LAYER (Optional)                             │
│  • Cloudflare Workers / Vercel Edge                                     │
│  • Rate Limiting (1000 req/min)                                         │
│  • DDoS Protection                                                      │
│  • Request Logging                                                      │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      FASTAPI BACKEND (Main App)                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌────────────────────────────────────────────────────────┐             │
│  │  POST /api/v1/webhooks/ringover                        │             │
│  │  ──────────────────────────────────────────────────    │             │
│  │  Handler: ringover_webhook()                           │             │
│  │                                                         │             │
│  │  1. Verify HMAC-SHA256 Signature                       │             │
│  │     ├─ Extract X-Ringover-Signature header             │             │
│  │     ├─ Compute HMAC(secret, body)                      │             │
│  │     └─ Compare (constant-time)                         │             │
│  │                                                         │             │
│  │  2. Parse JSON Payload                                 │             │
│  │     ├─ Validate with Pydantic (RingoverCallEvent)      │             │
│  │     └─ Extract: call_id, direction, duration, etc.     │             │
│  │                                                         │             │
│  │  3. Idempotency Check                                  │             │
│  │     ├─ Key: "ringover:{call_id}"                       │             │
│  │     ├─ Redis SETNX (TTL: 24h)                          │             │
│  │     └─ Return 200 if duplicate                         │             │
│  │                                                         │             │
│  │  4. Contact Matching                                   │             │
│  │     ├─ Parse phone to E.164 format                     │             │
│  │     │   (+32470123456, 0032470..., 0470...)            │             │
│  │     ├─ Query: SELECT * FROM contacts                   │             │
│  │     │         WHERE phone_e164 = ?                     │             │
│  │     └─ Result: Contact | None                          │             │
│  │                                                         │             │
│  │  5. Case Auto-Linking                                  │             │
│  │     ├─ IF contact matched:                             │             │
│  │     │   ├─ Query: SELECT cases                         │             │
│  │     │   │         JOIN case_contacts                   │             │
│  │     │   │         WHERE contact_id = ?                 │             │
│  │     │   │         AND status IN ('open', 'in_progress')│             │
│  │     │   │         ORDER BY opened_at DESC              │             │
│  │     │   │         LIMIT 1                              │             │
│  │     │   └─ Result: Case | None                         │             │
│  │     └─ ELSE: case_id = NULL                            │             │
│  │                                                         │             │
│  │  6. Create InteractionEvent                            │             │
│  │     ├─ Source: RINGOVER                                │             │
│  │     ├─ Event Type: CALL                                │             │
│  │     ├─ Title: "📞 Appel entrant - +32..."              │             │
│  │     ├─ Metadata: {                                     │             │
│  │     │     call_id, direction, duration,                │             │
│  │     │     recording_url, contact_id, ...               │             │
│  │     │   }                                               │             │
│  │     └─ INSERT INTO interaction_events                  │             │
│  │                                                         │             │
│  │  7. Broadcast SSE Event                                │             │
│  │     ├─ Event: "call_event_created"                     │             │
│  │     ├─ Tenant: tenant_id (from RLS)                    │             │
│  │     └─ Payload: { event_id, contact_name, ... }        │             │
│  │                                                         │             │
│  │  8. Background Task: AI Processing                     │             │
│  │     ├─ IF recording_url:                               │             │
│  │     │   ├─ Download audio file                         │             │
│  │     │   ├─ Transcribe (Whisper API)                    │             │
│  │     │   ├─ Summarize (Claude API)                      │             │
│  │     │   ├─ Sentiment Analysis (HuggingFace)            │             │
│  │     │   ├─ Extract Tasks (Claude)                      │             │
│  │     │   └─ Update metadata + Broadcast SSE             │             │
│  │     └─ ELSE: skip                                      │             │
│  │                                                         │             │
│  │  Response: { status: "accepted", call_id, ... }        │             │
│  │  Time: < 10ms (edge-optimized)                         │             │
│  └────────────────────────────────────────────────────────┘             │
│                                                                         │
│  ┌────────────────────────────────────────────────────────┐             │
│  │  GET /api/v1/events/stream                             │             │
│  │  ──────────────────────────────────────────────────    │             │
│  │  Server-Sent Events (SSE)                              │             │
│  │                                                         │             │
│  │  1. Authenticate (JWT from query param)                │             │
│  │  2. Extract tenant_id from claims                      │             │
│  │  3. Subscribe to tenant channel                        │             │
│  │  4. Yield events:                                      │             │
│  │     ├─ event: connected                                │             │
│  │     ├─ event: call_event_created                       │             │
│  │     ├─ event: call_ai_completed                        │             │
│  │     └─ keepalive (every 30s)                           │             │
│  │  5. Auto-cleanup on disconnect                         │             │
│  └────────────────────────────────────────────────────────┘             │
│                                                                         │
│  ┌────────────────────────────────────────────────────────┐             │
│  │  GET /api/v1/ringover/calls                            │             │
│  │  ──────────────────────────────────────────────────    │             │
│  │  Call History API                                      │             │
│  │                                                         │             │
│  │  Query Params:                                         │             │
│  │    • page, per_page (pagination)                       │             │
│  │    • direction (inbound/outbound)                      │             │
│  │    • call_type (answered/missed/voicemail)             │             │
│  │    • contact_id, case_id (filtering)                   │             │
│  │    • date_from, date_to (date range)                   │             │
│  │                                                         │             │
│  │  Returns: { items: [...], total, page, per_page }      │             │
│  └────────────────────────────────────────────────────────┘             │
│                                                                         │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             │ SSE Stream (text/event-stream)
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        NEXT.JS FRONTEND                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌────────────────────────────────────────────────────────┐             │
│  │  useEventStream() Hook                                 │             │
│  │  ──────────────────────────────────────────────────    │             │
│  │  React Hook for SSE Connection                         │             │
│  │                                                         │             │
│  │  1. Create EventSource                                 │             │
│  │     ├─ URL: /api/v1/events/stream?token={JWT}          │             │
│  │     └─ Listeners: connected, call_event_created, ...   │             │
│  │                                                         │             │
│  │  2. Event Handlers                                     │             │
│  │     ├─ onCallEvent: (data) => {                        │             │
│  │     │     toast.success("Appel reçu");                 │             │
│  │     │     router.refresh();                            │             │
│  │     │   }                                               │             │
│  │     └─ onCallAiCompleted: (data) => {                  │             │
│  │           toast.info("Analyse terminée");              │             │
│  │         }                                               │             │
│  │                                                         │             │
│  │  3. Auto-Reconnect (Exponential Backoff)               │             │
│  │     ├─ Retry delay: 1s → 2s → 4s → 8s → ... → 30s     │             │
│  │     └─ Max 30s delay between retries                   │             │
│  │                                                         │             │
│  │  4. Cleanup on Unmount                                 │             │
│  │     └─ eventSource.close()                             │             │
│  └────────────────────────────────────────────────────────┘             │
│                                                                         │
│  ┌────────────────────────────────────────────────────────┐             │
│  │  CallPlayer Component                                  │             │
│  │  ──────────────────────────────────────────────────    │             │
│  │  Advanced Audio Player                                 │             │
│  │                                                         │             │
│  │  • <audio> element (native HTML5)                      │             │
│  │  • Waveform visualization (canvas/SVG)                 │             │
│  │  • Controls:                                           │             │
│  │    ├─ Play/Pause toggle                                │             │
│  │    ├─ Skip ±10s                                        │             │
│  │    ├─ Seek bar (range input)                           │             │
│  │    ├─ Speed: 0.5x, 1x, 1.5x, 2x                        │             │
│  │    └─ Volume control                                   │             │
│  │  • Transcript sync (highlight text at current time)    │             │
│  │  • Sentiment indicator (color-coded)                   │             │
│  │  • Download button                                     │             │
│  └────────────────────────────────────────────────────────┘             │
│                                                                         │
│  ┌────────────────────────────────────────────────────────┐             │
│  │  CallNotificationProvider                              │             │
│  │  ──────────────────────────────────────────────────    │             │
│  │  Global SSE Event Handler                              │             │
│  │                                                         │             │
│  │  Wraps entire app to provide:                          │             │
│  │  • Real-time toast notifications                       │             │
│  │  • Auto-refresh timeline                               │             │
│  │  • Connection status monitoring                        │             │
│  │  • Optimistic UI updates                               │             │
│  └────────────────────────────────────────────────────────┘             │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Sequence

### 1. Incoming Call Webhook

```
Ringover → FastAPI → Database → SSE → Frontend
   (1)       (2)        (3)     (4)     (5)

(1) Ringover sends webhook POST with HMAC signature
(2) FastAPI validates, parses, matches contact/case
(3) InteractionEvent created in PostgreSQL
(4) SSE manager broadcasts to connected clients
(5) Frontend receives event, shows toast, refreshes UI
```

### 2. AI Processing Flow

```
Background Task → AI APIs → Database → SSE → Frontend
      (1)          (2)        (3)     (4)     (5)

(1) Background task downloads recording
(2) Calls Whisper, Claude, Sentiment API
(3) Updates InteractionEvent.metadata
(4) Broadcasts "call_ai_completed" event
(5) Frontend updates UI with transcript/summary
```

---

## Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Backend Services                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌────────────────┐     ┌────────────────┐                 │
│  │ webhook_service│────>│ ringover_service│                │
│  │                │     │                │                 │
│  │ • HMAC verify  │     │ • Contact match│                 │
│  │ • E.164 parse  │     │ • Case linking │                 │
│  │ • Idempotency  │     │ • Event create │                 │
│  └────────────────┘     │ • AI process   │                 │
│         │               └────────────────┘                 │
│         │                      │                           │
│         ▼                      ▼                           │
│  ┌────────────────┐     ┌────────────────┐                 │
│  │  sse_service   │     │timeline_service│                 │
│  │                │     │                │                 │
│  │ • Subscribe    │     │ • Create event │                 │
│  │ • Publish      │     │ • List events  │                 │
│  │ • Keepalive    │     │ • Filter/sort  │                 │
│  └────────────────┘     └────────────────┘                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                     Frontend Hooks                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌────────────────┐     ┌────────────────┐                 │
│  │useEventStream  │────>│  ringoverApi   │                 │
│  │                │     │                │                 │
│  │ • SSE connect  │     │ • listCalls()  │                 │
│  │ • Event parse  │     │ • getCall()    │                 │
│  │ • Reconnect    │     │ • getStats()   │                 │
│  └────────────────┘     └────────────────┘                 │
│         │                                                   │
│         ▼                                                   │
│  ┌────────────────────────────────┐                         │
│  │    React Components            │                         │
│  │                                │                         │
│  │  • CallPlayer                  │                         │
│  │  • CallTimelineItem            │                         │
│  │  • CallNotificationProvider    │                         │
│  └────────────────────────────────┘                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Database Schema

### InteractionEvent Table (Existing)

```sql
CREATE TABLE interaction_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  case_id UUID REFERENCES cases(id),
  source VARCHAR(50) NOT NULL,  -- 'RINGOVER'
  event_type VARCHAR(100) NOT NULL,  -- 'CALL'
  title VARCHAR(500) NOT NULL,
  body TEXT,
  occurred_at TIMESTAMPTZ NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}',
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  -- Indexes
  INDEX idx_tenant_source (tenant_id, source),
  INDEX idx_case_occurred (case_id, occurred_at DESC),
  INDEX idx_metadata_gin (metadata) USING GIN
);

-- RLS Policy (tenant isolation)
ALTER TABLE interaction_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON interaction_events
  USING (tenant_id = current_setting('app.current_tenant')::uuid);
```

### Metadata JSON Structure

```json
{
  // Call Metadata
  "call_id": "ringover-abc123",
  "direction": "inbound",
  "caller_number": "+32470123456",
  "callee_number": "+32471234567",
  "duration_seconds": 154,
  "call_type": "answered",
  "recording_url": "https://recordings.ringover.com/abc123.mp3",
  "started_at": "2026-02-17T10:30:00Z",
  "ended_at": "2026-02-17T10:32:34Z",
  "contact_id": "uuid-of-matched-contact",

  // AI Processing Status
  "transcript_status": "pending | completed | failed",
  "transcript": "Full transcript text...",

  "summary_status": "pending | completed | failed",
  "ai_summary": "Brief call summary...",

  "sentiment_score": 0.7,  // -1 to +1
  "sentiment_label": "positive",

  "tasks_generated": true,
  "extracted_tasks": [
    {
      "title": "Send invoice correction",
      "description": "Client requested update to invoice #2026/042",
      "due_date": "2026-02-20",
      "priority": "high"
    }
  ]
}
```

---

## Security Architecture

### 1. Webhook Security

```
┌──────────────┐
│   Ringover   │
└──────┬───────┘
       │ POST + HMAC-SHA256 Signature
       ▼
┌──────────────────────────────────────┐
│  FastAPI Webhook Handler             │
│  ─────────────────────────────────   │
│                                      │
│  1. Extract Signature                │
│     X-Ringover-Signature: abc123...  │
│                                      │
│  2. Compute Expected Signature       │
│     HMAC-SHA256(secret, body)        │
│                                      │
│  3. Constant-Time Compare            │
│     hmac.compare_digest(expected,    │
│                         received)    │
│                                      │
│  4. Reject if Mismatch               │
│     HTTP 401 Unauthorized            │
│                                      │
└──────────────────────────────────────┘
```

### 2. SSE Authentication

```
┌──────────────┐
│   Browser    │
└──────┬───────┘
       │ EventSource + JWT Token
       ▼
┌──────────────────────────────────────┐
│  SSE Endpoint                        │
│  ─────────────────────────────────   │
│                                      │
│  1. Extract Token (Query Param)      │
│     ?token=eyJhbGciOiJIUzI1NiI...    │
│                                      │
│  2. Verify JWT Signature             │
│     jwt.decode(token, secret)        │
│                                      │
│  3. Extract tenant_id from Claims    │
│     claims['tenant_id']              │
│                                      │
│  4. Subscribe to Tenant Channel      │
│     sse_manager.subscribe(tenant_id) │
│                                      │
└──────────────────────────────────────┘
```

### 3. Tenant Isolation (RLS)

```sql
-- Set tenant context before queries
SET app.current_tenant = 'uuid-of-tenant';

-- All queries automatically filtered
SELECT * FROM interaction_events;
-- RLS adds: WHERE tenant_id = 'uuid-of-tenant'

-- Cross-tenant access is impossible
-- Even with direct SQL injection
```

---

## Performance Optimizations

### 1. Webhook Response Time (< 10ms)

```python
# Fast path: no blocking operations
async def ringover_webhook():
    # ✅ Quick (< 1ms): HMAC verification
    verify_hmac_signature(body, signature, secret)

    # ✅ Quick (< 2ms): JSON parsing + validation
    event = RingoverCallEvent(**data)

    # ✅ Quick (< 1ms): Redis idempotency check
    if await check_idempotency(key):
        return early_response

    # ✅ Quick (< 5ms): Database queries (indexed)
    contact = await match_contact_by_phone(phone)
    case = await find_active_cases_for_contact(contact.id)

    # ✅ Quick (< 1ms): Create event
    event = await create_call_event(...)

    # ✅ Quick (< 1ms): SSE broadcast (in-memory)
    await sse_manager.publish(tenant_id, event)

    # ✅ Background: AI processing (doesn't block response)
    background_tasks.add_task(process_ai, event)

    return {"status": "accepted"}  # < 10ms total
```

### 2. Database Indexes

```sql
-- Speed up contact matching
CREATE INDEX idx_contacts_phone ON contacts(phone_e164);

-- Speed up case linking
CREATE INDEX idx_case_contacts_composite
  ON case_contacts(contact_id, case_id);

-- Speed up timeline queries
CREATE INDEX idx_events_case_occurred
  ON interaction_events(case_id, occurred_at DESC);

-- Speed up JSONB queries
CREATE INDEX idx_events_metadata_gin
  ON interaction_events USING GIN(metadata);

-- Query for calls with recordings
SELECT * FROM interaction_events
WHERE metadata->>'recording_url' IS NOT NULL;
-- Uses GIN index on metadata
```

### 3. SSE Channel Management

```python
class SSEManager:
    def __init__(self):
        # In-memory channels (no Redis overhead)
        self._channels: dict[UUID, list[Queue]] = defaultdict(list)

    async def subscribe(self, tenant_id: UUID):
        # O(1) channel creation
        queue = asyncio.Queue()
        self._channels[tenant_id].append(queue)

        # Stream events forever
        while True:
            event = await queue.get()  # Blocking wait
            yield event

    async def publish(self, tenant_id: UUID, event):
        # O(n) where n = subscribers (typically < 10)
        for queue in self._channels.get(tenant_id, []):
            queue.put_nowait(event)  # Non-blocking
```

---

## Scalability Considerations

### Horizontal Scaling

```
Load Balancer
      │
      ├─ FastAPI Instance 1 (SSE channels: tenant A, B)
      ├─ FastAPI Instance 2 (SSE channels: tenant C, D)
      └─ FastAPI Instance 3 (SSE channels: tenant E, F)
```

**Challenge:** SSE events must reach all instances.

**Solution:** Redis Pub/Sub

```python
# sse_service.py
import redis.asyncio as redis

class SSEManager:
    def __init__(self):
        self.redis = redis.from_url("redis://localhost")

    async def publish(self, tenant_id: UUID, event):
        # Publish to Redis channel
        await self.redis.publish(
            f"sse:{tenant_id}",
            json.dumps(event)
        )

    async def subscribe(self, tenant_id: UUID):
        # Subscribe to Redis channel
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(f"sse:{tenant_id}")

        async for message in pubsub.listen():
            yield message
```

---

## Monitoring & Observability

### Key Metrics

1. **Webhook Metrics**
   - Request rate (calls/min)
   - Response time (p50, p95, p99)
   - Error rate (4xx, 5xx)
   - HMAC verification failures

2. **SSE Metrics**
   - Active connections per tenant
   - Event delivery latency
   - Reconnection rate
   - Dropped events (queue full)

3. **AI Processing Metrics**
   - Transcription time
   - Summarization time
   - Success rate
   - Error types

### Logging

```python
# Structured logging (JSON format)
logger.info(
    "ringover.webhook.received",
    extra={
        "call_id": event.call_id,
        "tenant_id": str(tenant_id),
        "direction": event.direction,
        "duration": event.duration_seconds,
        "matched_contact": bool(contact),
        "linked_case": bool(case_id),
        "latency_ms": latency,
    }
)
```

---

This architecture provides:
- ✅ **Security**: HMAC, JWT, RLS
- ✅ **Performance**: < 10ms webhooks, indexed queries
- ✅ **Scalability**: Horizontal scaling with Redis
- ✅ **Reliability**: Idempotency, auto-reconnect
- ✅ **Observability**: Structured logging, metrics
