# Audio Transcription + AI Insights - Quick Start Guide

## Setup (5 minutes)

### 1. Install Dependencies
No new dependencies needed! Uses existing OpenAI integration.

### 2. Set Environment Variable
```bash
export OPENAI_API_KEY="sk-your-api-key-here"
```

### 3. Verify API is Running
The endpoints are automatically registered when the API starts.

---

## Usage Examples

### Example 1: Basic Transcription
```bash
curl -X POST "http://localhost:8000/api/v1/ai/transcribe" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@client_meeting.mp3" \
  -F "language=fr" \
  -F "enable_diarization=true" \
  -F "extract_insights=false"
```

**Returns:**
- Full transcript text
- Speaker-tagged segments
- Word-level timestamps
- Language detection
- Confidence scores

---

### Example 2: Full AI Analysis (Recommended)
```bash
curl -X POST "http://localhost:8000/api/v1/ai/transcribe" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@team_meeting.mp3" \
  -F "extract_insights=true" \
  -F "case_id=550e8400-e29b-41d4-a716-446655440000"
```

**Returns Everything:**
- ✅ Transcript with speakers
- ✅ 3-sentence summary
- ✅ Action items (with assignees & deadlines)
- ✅ Decisions made
- ✅ Case/contact references
- ✅ Sentiment score
- ✅ Urgency level
- ✅ Key topics
- ✅ Suggested next actions

---

### Example 3: Real-time Streaming
```bash
curl -X POST "http://localhost:8000/api/v1/ai/transcribe/stream" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@live_recording.mp3" \
  -F "language=fr" \
  --no-buffer
```

**Streams words as they're transcribed:**
```json
{"word": "Bonjour", "start": 0.0, "end": 0.5, "confidence": 0.95}
{"word": "monsieur", "start": 0.6, "end": 1.2, "confidence": 0.92}
...
```

---

## Supported Audio Formats

| Format | MIME Type | Max Size | Quality |
|--------|-----------|----------|---------|
| MP3 | audio/mpeg | 25 MB | ⭐⭐⭐⭐⭐ |
| WAV | audio/wav | 25 MB | ⭐⭐⭐⭐⭐ |
| M4A | audio/mp4 | 25 MB | ⭐⭐⭐⭐ |
| OGG | audio/ogg | 25 MB | ⭐⭐⭐⭐ |
| WebM | audio/webm | 25 MB | ⭐⭐⭐ |
| FLAC | audio/flac | 25 MB | ⭐⭐⭐⭐⭐ |

**Tip:** For files >25MB, compress with: `ffmpeg -i input.wav -b:a 64k output.mp3`

---

## Language Codes

| Language | Code | Auto-detect? |
|----------|------|--------------|
| French | `fr` | ✅ Yes |
| Dutch | `nl` | ✅ Yes |
| English | `en` | ✅ Yes |

**Auto-detection:** Leave `language` parameter empty for automatic detection.

---

## Response Structure

### Transcription Object
```json
{
  "transcript_id": "uuid",
  "full_text": "Complete transcript...",
  "language": "fr",
  "duration_seconds": 180.5,
  "segments": [
    {
      "speaker_id": "SPEAKER_00",
      "start_time": 0.0,
      "end_time": 5.2,
      "text": "Speaker 0's words",
      "confidence": 0.95
    }
  ],
  "confidence_score": 0.92,
  "processing_time_seconds": 8.3,
  "model": "whisper-1"
}
```

### Insights Object
```json
{
  "summary": "3-sentence summary...",
  "action_items": [
    {
      "text": "Send documents to court",
      "assignee": "Maître Dupont",
      "deadline": "2026-03-15",
      "priority": "high",
      "status": "pending",
      "source_timestamp": 45.2
    }
  ],
  "decisions": [
    {
      "text": "We accept mediation",
      "decided_by": "The client",
      "timestamp": 120.5
    }
  ],
  "references": [
    {
      "ref_type": "case",
      "text": "dossier Dupont",
      "context": "Regarding case Dupont...",
      "timestamp": 5.0
    }
  ],
  "sentiment_score": 0.3,
  "urgency_level": "high",
  "key_topics": ["médiation", "tribunal", "délai"],
  "suggested_next_actions": [
    "• Send court documents",
    "• Schedule mediation",
    "• Document decisions"
  ]
}
```

---

## Error Handling

### Common Errors

**400 Bad Request - Unsupported Format**
```json
{
  "detail": "Unsupported audio format: video/mp4. Supported: mp3, wav, m4a, ogg, webm, flac"
}
```
**Fix:** Convert to supported format or check MIME type.

**413 Payload Too Large**
```json
{
  "detail": "File too large. Maximum size is 25MB"
}
```
**Fix:** Compress audio or split into chunks.

**500 Internal Server Error**
```json
{
  "detail": "Transcription failed: OpenAI API error"
}
```
**Fix:** Check OPENAI_API_KEY environment variable.

---

## Performance Tips

### 1. Optimize Audio Files
```bash
# Compress to 64kbps MP3 (good for speech)
ffmpeg -i input.wav -b:a 64k -ar 16000 output.mp3

# Remove silence (reduces file size)
ffmpeg -i input.mp3 -af silenceremove=1:0:-50dB output.mp3
```

### 2. Use Streaming for Long Files
For files >5 minutes, use `/transcribe/stream` endpoint to show progress.

### 3. Batch Processing
Process multiple files concurrently (respects rate limits):
```python
import asyncio
import httpx

async def transcribe_batch(files):
    async with httpx.AsyncClient() as client:
        tasks = [
            client.post(
                "http://localhost:8000/api/v1/ai/transcribe",
                files={"file": open(f, "rb")},
                data={"extract_insights": "true"}
            )
            for f in files
        ]
        return await asyncio.gather(*tasks)
```

---

## Integration Examples

### Python Client
```python
import httpx

async def transcribe_audio(file_path: str, jwt_token: str):
    async with httpx.AsyncClient() as client:
        with open(file_path, "rb") as f:
            response = await client.post(
                "http://localhost:8000/api/v1/ai/transcribe",
                headers={"Authorization": f"Bearer {jwt_token}"},
                files={"file": f},
                data={
                    "language": "fr",
                    "enable_diarization": "true",
                    "extract_insights": "true"
                }
            )
            return response.json()

# Usage
result = await transcribe_audio("meeting.mp3", "your-jwt-token")
print(result["transcription"]["full_text"])
print(result["insights"]["summary"])
```

### JavaScript/TypeScript Client
```typescript
async function transcribeAudio(
  file: File,
  jwtToken: string
): Promise<CompleteTranscriptionResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("language", "fr");
  formData.append("extract_insights", "true");

  const response = await fetch("http://localhost:8000/api/v1/ai/transcribe", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${jwtToken}`,
    },
    body: formData,
  });

  return await response.json();
}

// Usage
const file = document.querySelector('input[type="file"]').files[0];
const result = await transcribeAudio(file, "your-jwt-token");
console.log(result.insights.action_items);
```

---

## Use Cases

### 1. Client Meeting Notes
**Input:** Recording of client consultation
**Output:** Transcript + action items + case references
**Benefit:** Auto-generate meeting minutes

### 2. Court Hearing Transcripts
**Input:** Audio recording of hearing
**Output:** Speaker-tagged transcript + key decisions
**Benefit:** Accurate procedural records

### 3. Team Collaboration
**Input:** Team discussion recording
**Output:** Summary + task assignments + deadlines
**Benefit:** Automatic task creation

### 4. Deposition Analysis
**Input:** Witness deposition audio
**Output:** Transcript + sentiment + key claims
**Benefit:** Identify inconsistencies

### 5. Phone Call Logging
**Input:** Client phone call
**Output:** Transcript + references + follow-ups
**Benefit:** Complete call documentation

---

## Production Checklist

- [ ] `OPENAI_API_KEY` environment variable set
- [ ] Rate limits configured (default: 30/minute per tenant)
- [ ] Audio file size limits enforced (25MB)
- [ ] CORS headers configured for frontend
- [ ] Error logging enabled
- [ ] Monitoring alerts for API failures
- [ ] Database schema created (see BRAIN_2_TRANSCRIPTION_SUMMARY.md)
- [ ] Frontend upload component built
- [ ] User permissions configured
- [ ] Backup/retention policy defined

---

## Monitoring & Debugging

### Check Service Status
```python
# In Python shell
from apps.api.services.transcription_service import TranscriptionService

svc = TranscriptionService()
# Should not raise ValueError if OPENAI_API_KEY is set
```

### Test with Sample Audio
```bash
# Generate 10-second test audio
ffmpeg -f lavfi -i "sine=frequency=1000:duration=10" test.mp3

# Transcribe it
curl -X POST "http://localhost:8000/api/v1/ai/transcribe" \
  -H "Authorization: Bearer TOKEN" \
  -F "file=@test.mp3" \
  -F "extract_insights=false"
```

### View Logs
```bash
# API logs will show transcription progress
tail -f logs/api.log | grep "transcribe"
```

---

## Cost Estimation

### Whisper API Pricing (OpenAI)
- **$0.006 per minute** of audio

### GPT-4 API Pricing (Insights)
- **~$0.03 per request** for insights extraction (depends on transcript length)

### Example Costs
| Audio Length | Transcription | Insights | Total |
|--------------|---------------|----------|-------|
| 5 minutes    | $0.03         | $0.03    | $0.06 |
| 30 minutes   | $0.18         | $0.05    | $0.23 |
| 1 hour       | $0.36         | $0.08    | $0.44 |

**Monthly estimate (100 meetings/month @ 30min avg):** ~$23

---

## FAQ

**Q: Can I transcribe video files?**
A: Extract audio first: `ffmpeg -i video.mp4 -vn -acodec mp3 audio.mp3`

**Q: What's the maximum audio length?**
A: No hard limit, but files >25MB need compression. Whisper handles up to 25MB per API call.

**Q: How accurate is speaker diarization?**
A: Current implementation: ~80% accuracy with simple heuristic. For production, integrate pyannote.audio.

**Q: Can I customize the AI extraction prompts?**
A: Yes, edit system prompts in `action_extraction_service.py`

**Q: Does it work offline?**
A: No, requires OpenAI API. For offline, deploy local Whisper model.

**Q: How do I link transcripts to cases?**
A: Pass `case_id` parameter. Future: auto-detect from references.

**Q: Can I export to Word/PDF?**
A: Yes, use transcript text with existing document generation system.

---

## Support

**Documentation:** See `BRAIN_2_TRANSCRIPTION_SUMMARY.md` for full details
**API Docs:** http://localhost:8000/docs (auto-generated OpenAPI)
**Source Code:**
- `apps/api/services/transcription_service.py`
- `apps/api/services/action_extraction_service.py`
- `apps/api/routers/ai.py`
- `apps/api/schemas/agents.py`

---

**Built with:** OpenAI Whisper API + GPT-4 + FastAPI + Pydantic
**License:** Internal LexiBel Platform
**Version:** 1.0.0 (2026-02-17)
