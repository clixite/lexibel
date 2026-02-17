# Plaud.ai Integration - LexiBel

## Overview

This document describes the Plaud.ai webhook integration for LexiBel. Since Plaud.ai does not provide a public API, the integration is entirely webhook-based.

## Architecture

### Components

1. **Plaud Client** (`apps/api/services/plaud_client.py`)
   - Stub client for potential future API access
   - Provides health check functionality
   - Currently not used in production (webhooks only)

2. **Webhook Handler** (`apps/api/webhooks/plaud.py`)
   - POST endpoint: `/api/v1/webhooks/plaud`
   - HMAC-SHA256 signature verification
   - Creates Transcription and TranscriptionSegment records
   - Optionally creates InteractionEvent for timeline integration

3. **Transcriptions Router** (`apps/api/routers/transcriptions.py`)
   - GET `/api/v1/transcriptions` - List all transcriptions
   - GET `/api/v1/transcriptions/{id}` - Get transcription details with segments
   - Supports filtering by case, source, and status

## Database Models

### Transcription
Located in `packages/db/models/transcription.py`

Fields:
- `id` (UUID, PK)
- `tenant_id` (UUID, FK)
- `case_id` (UUID, FK, nullable)
- `source` (string) - 'plaud', 'ringover', 'manual'
- `audio_url` (string, nullable)
- `audio_duration_seconds` (integer)
- `language` (string) - 'fr', 'nl', 'en'
- `status` (string) - 'pending', 'processing', 'completed', 'failed'
- `full_text` (text)
- `summary` (text, nullable)
- `sentiment_score` (numeric, nullable)
- `sentiment_label` (string, nullable)
- `extracted_tasks` (JSONB array)
- `metadata` (JSONB)
- `completed_at` (timestamp)

### TranscriptionSegment
Located in `packages/db/models/transcription_segment.py`

Fields:
- `id` (UUID, PK)
- `transcription_id` (UUID, FK)
- `segment_index` (integer)
- `speaker` (string, nullable)
- `start_time` (numeric) - seconds with 3 decimal precision
- `end_time` (numeric)
- `text` (text)
- `confidence` (numeric, nullable) - 0.0 to 1.0

## Webhook Payload Format

Plaud.ai sends the following JSON payload:

```json
{
  "transcription_id": "plaud_rec_123456789",
  "tenant_id": "uuid-here",
  "case_id": "uuid-here",
  "audio_url": "https://...",
  "text": "Full transcription text...",
  "segments": [
    {
      "segment_index": 0,
      "speaker": "Client",
      "start_time": 0.0,
      "end_time": 8.5,
      "text": "Segment text...",
      "confidence": 0.95
    }
  ],
  "speakers": [
    {
      "id": "speaker_1",
      "name": "Client"
    }
  ],
  "duration": 120,
  "language": "fr",
  "metadata": {}
}
```

## Security

### HMAC Signature Verification

Every webhook request must include the `X-Plaud-Signature` header containing an HMAC-SHA256 signature.

**Signature Generation:**
```python
import hashlib
import hmac

signature = hmac.new(
    WEBHOOK_SECRET.encode('utf-8'),
    payload_bytes,
    hashlib.sha256
).hexdigest()
```

**Environment Variable:**
```bash
PLAUD_WEBHOOK_SECRET=your-secret-here
```

Default for development: `plaud-dev-secret`

### Idempotency

The webhook handler implements idempotency using the `transcription_id`:
- Key format: `plaud:{transcription_id}`
- In-memory store for development (replace with Redis in production)
- Prevents duplicate processing of the same recording

## Processing Flow

1. **Request Validation**
   - Verify `X-Plaud-Signature` header is present
   - Compute HMAC-SHA256 of raw body
   - Compare with provided signature (constant-time comparison)

2. **Idempotency Check**
   - Check if `plaud:{transcription_id}` exists in store
   - Return 200 with `duplicate: true` if already processed

3. **Database Transaction**
   - Set RLS context: `SET LOCAL app.current_tenant_id = '{tenant_id}'`
   - Create `Transcription` record
   - Create `TranscriptionSegment` records for each segment
   - Create `InteractionEvent` if `case_id` is provided

4. **Response**
   ```json
   {
     "status": "accepted",
     "transcription_id": "plaud_rec_123456789",
     "db_transcription_id": "uuid-of-db-record",
     "interaction_event_created": true,
     "segments_created": 3
   }
   ```

## Error Handling

### 401 Unauthorized
- Missing `X-Plaud-Signature` header
- Invalid HMAC signature

### 400 Bad Request
- Invalid JSON payload
- Invalid payload structure (missing required fields)
- Invalid UUID format for `case_id` or `tenant_id`

### 500 Internal Server Error
- Database connection failure
- Transaction error during record creation

## Testing

### Example Payload
See `docs/plaud_webhook_example.json`

### Test Script
Run `tests/test_plaud_webhook.py`:

```bash
# Test signature generation
python tests/test_plaud_webhook.py

# Test live webhook (requires API running)
# Set WEBHOOK_SECRET in script to match your .env
python -m pytest tests/test_plaud_webhook.py -v
```

### Manual Testing with curl

```bash
# Generate signature (use your secret)
SECRET="plaud-dev-secret"
PAYLOAD='{"transcription_id":"test123","tenant_id":"...",...}'
SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" -hex | cut -d' ' -f2)

# Send request
curl -X POST http://localhost:8000/api/v1/webhooks/plaud \
  -H "Content-Type: application/json" \
  -H "X-Plaud-Signature: $SIGNATURE" \
  -d "$PAYLOAD"
```

## API Endpoints

### List Transcriptions
```
GET /api/v1/transcriptions
```

Query Parameters:
- `case_id` (UUID, optional) - Filter by case
- `source` (string, optional) - Filter by source (plaud, ringover, manual)
- `status` (string, optional) - Filter by status
- `limit` (integer, default 50, max 200)
- `offset` (integer, default 0)

Response:
```json
{
  "transcriptions": [...],
  "total": 10,
  "limit": 50,
  "offset": 0
}
```

### Get Transcription Details
```
GET /api/v1/transcriptions/{id}
```

Query Parameters:
- `include_segments` (boolean, default true)

Response:
```json
{
  "id": "uuid",
  "case_id": "uuid",
  "source": "plaud",
  "status": "completed",
  "language": "fr",
  "full_text": "...",
  "segments": [
    {
      "segment_index": 0,
      "speaker": "Client",
      "start_time": 0.0,
      "end_time": 8.5,
      "text": "...",
      "confidence": 0.95
    }
  ],
  "segments_count": 3
}
```

## Integration with Timeline

When a `case_id` is provided in the webhook payload, an `InteractionEvent` is automatically created:

```python
InteractionEvent(
    tenant_id=tenant_id,
    case_id=case_id,
    source="PLAUD",
    event_type="TRANSCRIPTION",
    title=f"Plaud Transcription - {language.upper()}",
    body=full_text[:1000],  # Truncated summary
    occurred_at=datetime.utcnow(),
    metadata_={
        "transcription_id": str(transcription.id),
        "duration_seconds": duration,
        "language": language,
        "audio_url": audio_url,
        "segments_count": len(segments)
    }
)
```

This makes the transcription appear in the case timeline for easy access.

## Production Considerations

1. **Replace In-Memory Idempotency Store**
   - Use Redis SETNX with 24h TTL
   - Key format: `idempotency:plaud:{transcription_id}`

2. **Webhook Secret Rotation**
   - Store in secure vault (AWS Secrets Manager, Vault)
   - Support multiple secrets during rotation period

3. **Monitoring**
   - Log all webhook requests (with signature validation result)
   - Alert on repeated signature failures (potential attack)
   - Track processing latency and error rates

4. **Rate Limiting**
   - Apply rate limits to webhook endpoint
   - Current middleware: 1000 requests/hour per IP

5. **Audio Storage**
   - Plaud provides `audio_url` with signed URLs
   - Consider downloading and archiving to own S3 bucket
   - Set retention policy based on legal requirements

## Future Enhancements

1. **AI Analysis Pipeline**
   - Sentiment analysis on segments
   - Action item extraction
   - Summary generation
   - Legal terminology detection

2. **Speaker Identification**
   - Link speakers to Contact records
   - Voice fingerprinting for automatic identification

3. **Multi-language Support**
   - Automatic translation
   - Language detection confidence scoring

4. **Real-time Transcription**
   - WebSocket endpoint for live transcription
   - Incremental segment updates

## Files Modified/Created

### Created
- `F:/LexiBel/apps/api/services/plaud_client.py` - Plaud API client stub
- `F:/LexiBel/docs/plaud_webhook_example.json` - Example webhook payload
- `F:/LexiBel/tests/test_plaud_webhook.py` - Test script
- `F:/LexiBel/docs/PLAUD_INTEGRATION.md` - This documentation

### Modified
- `F:/LexiBel/apps/api/webhooks/plaud.py` - Complete rewrite for DB integration
- `F:/LexiBel/apps/api/routers/transcriptions.py` - Complete rewrite for proper API

### Existing (Referenced)
- `F:/LexiBel/packages/db/models/transcription.py` - Transcription model
- `F:/LexiBel/packages/db/models/transcription_segment.py` - Segment model
- `F:/LexiBel/packages/db/models/interaction_event.py` - Timeline integration
- `F:/LexiBel/apps/api/main.py` - Router already registered
- `F:/LexiBel/apps/api/services/webhook_service.py` - HMAC verification utilities

## Environment Variables

```bash
# Required
PLAUD_WEBHOOK_SECRET=your-webhook-secret-here

# Optional (for future API access)
PLAUD_API_KEY=your-api-key-here
```

## Support

For issues or questions:
1. Check logs in `/var/log/lexibel/api.log`
2. Verify webhook signature calculation
3. Ensure tenant_id exists in database
4. Check RLS policies are correctly configured
