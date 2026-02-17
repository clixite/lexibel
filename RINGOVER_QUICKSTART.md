# Ringover Integration — Quick Start Guide

**Get up and running with Ringover in 5 minutes.**

---

## Prerequisites

- Python 3.11+ with FastAPI
- Node.js 18+ with Next.js
- PostgreSQL database
- Ringover account

---

## Backend Setup (3 steps)

### Step 1: Set Environment Variable

```bash
# .env
RINGOVER_WEBHOOK_SECRET=your-secret-from-ringover
```

### Step 2: Run Migrations (if needed)

The integration uses existing `interaction_events` table. No new migrations required!

```bash
alembic upgrade head
```

### Step 3: Start Backend

```bash
cd apps/api
uvicorn main:app --reload
```

**Webhook URL:** `http://localhost:8000/api/v1/webhooks/ringover`

---

## Frontend Setup (2 steps)

### Step 1: Set Environment Variable

```bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Step 2: Wrap App with Provider

```tsx
// app/layout.tsx
import { CallNotificationProvider } from '@/components/calls/CallNotificationProvider';
import { Toaster } from 'sonner';

export default function RootLayout({ children }) {
  return (
    <html>
      <body>
        <CallNotificationProvider>
          {children}
        </CallNotificationProvider>
        <Toaster position="top-right" />
      </body>
    </html>
  );
}
```

---

## Ringover Configuration

### Step 1: Create Webhook

1. Log in to [Ringover Dashboard](https://dashboard.ringover.com)
2. Navigate to **Settings** → **Webhooks**
3. Click **Create New Webhook**
4. Fill in:
   - **Name:** LexiBel Integration
   - **URL:** `https://your-domain.com/api/v1/webhooks/ringover`
   - **Secret:** (generate and copy to `.env`)
   - **Events:**
     - ✅ Call answered
     - ✅ Call missed
     - ✅ Voicemail

### Step 2: Test Webhook

Click **Test Webhook** in Ringover dashboard. You should see:

```json
{
  "status": "accepted",
  "call_id": "test-123",
  "event_created": true,
  "contact_matched": false,
  "case_linked": false
}
```

---

## Testing Locally

### Option 1: ngrok (Recommended)

```bash
# Terminal 1: Start backend
uvicorn main:app --reload

# Terminal 2: Expose with ngrok
ngrok http 8000

# Use ngrok URL in Ringover webhook config
# https://abc123.ngrok.io/api/v1/webhooks/ringover
```

### Option 2: Manual cURL

```bash
# Generate test webhook
SECRET="ringover-dev-secret"
PAYLOAD='{
  "call_id": "test-456",
  "tenant_id": "tenant-1",
  "call_type": "answered",
  "caller_number": "+32470123456",
  "callee_number": "+32471234567",
  "direction": "inbound",
  "duration_seconds": 120,
  "started_at": "2026-02-17T10:30:00Z",
  "recording_url": "https://example.com/recording.mp3"
}'

SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" | cut -d' ' -f2)

curl -X POST http://localhost:8000/api/v1/webhooks/ringover \
  -H "X-Ringover-Signature: $SIGNATURE" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD"
```

---

## Usage Examples

### 1. Display Call in Timeline

```tsx
// app/dashboard/cases/[id]/timeline.tsx
import { CallTimelineItem } from '@/components/timeline/CallTimelineItem';

export function CaseTimeline({ events }: { events: InteractionEvent[] }) {
  return (
    <div className="space-y-4">
      {events.map((event) => {
        if (event.source === 'RINGOVER') {
          return <CallTimelineItem key={event.id} event={event} />;
        }
        return <DefaultTimelineItem key={event.id} event={event} />;
      })}
    </div>
  );
}
```

### 2. List Recent Calls

```tsx
// app/dashboard/calls/page.tsx
'use client';

import { useEffect, useState } from 'react';
import { ringoverApi, CallEvent } from '@/lib/api/ringover';

export default function CallsPage() {
  const [calls, setCalls] = useState<CallEvent[]>([]);

  useEffect(() => {
    ringoverApi.listCalls({ per_page: 50 }).then((data) => {
      setCalls(data.items);
    });
  }, []);

  return (
    <div>
      <h1>Recent Calls</h1>
      {calls.map((call) => (
        <div key={call.id}>
          <p>{call.contact_name || call.phone_number}</p>
          <p>{call.duration_formatted} • {call.occurred_at}</p>
        </div>
      ))}
    </div>
  );
}
```

### 3. Call Statistics Widget

```tsx
// app/dashboard/widgets/CallStats.tsx
'use client';

import { useEffect, useState } from 'react';
import { ringoverApi, CallStats } from '@/lib/api/ringover';

export function CallStatsWidget() {
  const [stats, setStats] = useState<CallStats | null>(null);

  useEffect(() => {
    ringoverApi.getStats(30).then(setStats);
  }, []);

  if (!stats) return <div>Loading...</div>;

  return (
    <div className="grid grid-cols-3 gap-4">
      <div>
        <p className="text-2xl font-bold">{stats.total_calls}</p>
        <p className="text-sm text-gray-600">Total Calls</p>
      </div>
      <div>
        <p className="text-2xl font-bold">{stats.answered_calls}</p>
        <p className="text-sm text-gray-600">Answered</p>
      </div>
      <div>
        <p className="text-2xl font-bold">{stats.avg_duration_minutes.toFixed(1)}m</p>
        <p className="text-sm text-gray-600">Avg Duration</p>
      </div>
    </div>
  );
}
```

---

## Real-time Events

### Subscribe to Events

The `CallNotificationProvider` automatically subscribes to SSE events. To add custom handlers:

```tsx
// Custom component
import { useEventStream } from '@/lib/hooks/useEventStream';

function MyComponent() {
  const { isConnected } = useEventStream({
    onCallEvent: (data) => {
      console.log('New call:', data);
      // Custom logic here
    },
    onCallAiCompleted: (data) => {
      console.log('AI processing done:', data);
      // Update UI with transcript/summary
    },
  });

  return <div>SSE Connected: {isConnected ? '✅' : '❌'}</div>;
}
```

---

## Troubleshooting

### Webhook not receiving events

1. Check HMAC signature verification:
   ```python
   # Temporarily disable in ringover.py for testing
   # if not verify_hmac_signature(...):
   #     raise HTTPException(...)
   ```

2. Check Ringover logs in dashboard
3. Verify URL is publicly accessible (use ngrok)

### SSE connection failing

1. Check CORS configuration:
   ```python
   # main.py
   allow_origins=["http://localhost:3000"]
   ```

2. Verify JWT token is valid:
   ```bash
   # Check token in browser console
   console.log(session?.accessToken);
   ```

3. Check EventSource errors:
   ```javascript
   eventSource.onerror = (e) => console.error('SSE Error:', e);
   ```

### Contact not matched

1. Verify phone format is E.164:
   ```python
   # Test E.164 parsing
   from apps.api.services.webhook_service import parse_e164
   print(parse_e164("+32470123456"))  # Should return "+32470123456"
   print(parse_e164("0470123456"))    # Should return "+32470123456"
   ```

2. Check contact exists with correct phone:
   ```sql
   SELECT * FROM contacts WHERE phone_e164 = '+32470123456';
   ```

---

## Production Checklist

- [ ] Set production `RINGOVER_WEBHOOK_SECRET`
- [ ] Configure HTTPS for webhook URL
- [ ] Set up Redis for idempotency (replace in-memory store)
- [ ] Enable rate limiting on webhook endpoint
- [ ] Set up monitoring (Sentry, DataDog)
- [ ] Configure CDN for call recordings
- [ ] Implement AI processing (BRAIN 2)
- [ ] Add database indexes on `metadata` JSONB fields
- [ ] Set up backup for call recordings
- [ ] Configure log retention policy

---

## Next Steps

1. **Test the integration** with a real Ringover call
2. **Customize UI** (colors, icons, layout)
3. **Add AI features** (see BRAIN 2 requirements)
4. **Set up monitoring** (webhook success rate, SSE connections)
5. **Deploy to production** (use checklist above)

---

## Support

- **Documentation:** `docs/RINGOVER_INTEGRATION.md`
- **Summary:** `RINGOVER_SUMMARY.md`
- **API Reference:** `http://localhost:8000/api/v1/docs`

---

**You're all set!** 🚀

Incoming calls will now appear in real-time with rich metadata, audio playback, and AI insights.
