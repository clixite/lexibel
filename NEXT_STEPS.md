# LexiBel - Next Steps (Updated 2026-02-17)

**Previous Status** (from docs/NEXT-STEPS.md): Phase 1-3 complete, Phase 2 "The Brain" not started

**Current Status**: Infrastructure consolidated, awaiting Docker startup + implementation

---

## 🚨 IMMEDIATE ACTIONS (Before Anything Else)

### 1. Start Docker Desktop ⏱️ 2 min

Docker must be running to proceed with database operations.

```bash
# Windows: Open Docker Desktop from Start menu
# Mac: Open Docker.app
# Linux: sudo systemctl start docker
```

### 2. Run Migrations ⏱️ 5 min

```bash
cd /f/LexiBel
bash run_migrations.sh
```

Expected output:
```
✅ Docker is running
✅ PostgreSQL is running
🚀 Running Alembic migrations...
INFO  [alembic.runtime.migration] Running upgrade 006 -> 007
INFO  [alembic.runtime.migration] Running upgrade 007 -> 008
INFO  [alembic.runtime.migration] Running upgrade 008 -> 009
INFO  [alembic.runtime.migration] Running upgrade 009 -> 010
✅ Migrations completed!
```

### 3. Seed Demo Data ⏱️ 5 min

```bash
cd /f/LexiBel
docker compose up -d api  # Ensure API container is running
docker exec -it lexibel-api-1 python -m apps.api.scripts.seed_demo_data
```

Expected output:
```
🌱 Starting seed data...
✅ Tenant created: Cabinet Demo
✅ User created: nicolas@clixite.be
✅ 10 contacts created
✅ 5 cases created
...
🎉 Demo data seed completed successfully!
```

### 4. Verify Setup ⏱️ 2 min

```bash
# Check tables exist
docker exec lexibel-postgres-1 psql -U lexibel -d lexibel -c "\dt" | grep -E "cases|contacts|email_threads|call_records"

# Check data exists
docker exec lexibel-postgres-1 psql -U lexibel -d lexibel -c "SELECT COUNT(*) FROM cases"
# Expected: 5

# Start services
cd /f/LexiBel
docker compose up -d

# Check API health
curl http://localhost:8000/api/v1/admin/health
# Expected: {"status": "ok", "db": "connected", ...}
```

---

## 🔴 HIGH PRIORITY (Start Here After Setup)

### 5. Implement OAuth Services ⏱️ 2 hours

**Files to Create**:

1. `apps/api/services/google_oauth_service.py`
   - OAuth2 authorization URL generation
   - Token exchange (code → access_token + refresh_token)
   - Token refresh logic
   - Fernet encryption/decryption
   - Store in `oauth_tokens` table

2. `apps/api/services/microsoft_oauth_service.py`
   - Same as Google but for Microsoft Graph API
   - Tenant ID handling

3. `apps/api/services/oauth_encryption_service.py`
   - Fernet key management
   - `encrypt_token(token: str) -> str`
   - `decrypt_token(encrypted: str) -> str`

**Endpoints to Enhance**:

- `GET /api/v1/admin/integrations` → List active OAuth connections
- `POST /api/v1/admin/integrations/google/connect` → Redirect to Google OAuth
- `GET /api/v1/oauth/google/callback` → Handle OAuth callback
- `POST /api/v1/admin/integrations/microsoft/connect` → Redirect to Microsoft OAuth
- `GET /api/v1/oauth/microsoft/callback` → Handle OAuth callback
- `DELETE /api/v1/admin/integrations/{provider}/disconnect` → Revoke tokens

**Testing**:
```bash
# Test Google OAuth flow
curl -X POST http://localhost:8000/api/v1/admin/integrations/google/connect \
  -H "Authorization: Bearer YOUR_JWT"
# Follow returned URL, authorize, check token saved in DB
```

### 6. Implement Integration Services ⏱️ 2 hours

**Files to Create**:

1. `apps/api/services/ringover_integration_service.py`
   - `fetch_calls(tenant_id, date_from, date_to) -> List[CallRecord]`
   - `get_call_recording(call_id) -> bytes`
   - API key authentication
   - Rate limiting (1000 req/min as per docs)

2. `apps/api/services/plaud_integration_service.py`
   - `upload_audio(file, case_id) -> Transcription`
   - `get_transcription_status(transcription_id) -> str`
   - Webhook handler for completed transcriptions

3. `apps/api/services/gmail_sync_service.py`
   - `sync_emails(oauth_token, user_id, since: datetime) -> List[EmailThread]`
   - Uses Google Gmail API
   - Create `email_threads` and `email_messages`
   - Background task for periodic sync

4. `apps/api/services/outlook_sync_service.py` (enhance existing)
   - Add email sync (currently only sends emails)
   - Create `email_threads` and `email_messages`
   - Use Microsoft Graph API `/me/messages`

5. `apps/api/services/calendar_sync_service.py`
   - `sync_google_calendar(oauth_token, user_id) -> List[CalendarEvent]`
   - `sync_outlook_calendar(oauth_token, user_id) -> List[CalendarEvent]`
   - Create `calendar_events`

**Testing**:
```bash
# Test Ringover sync
curl -X GET "http://localhost:8000/api/v1/ringover/calls?date_from=2026-01-01" \
  -H "Authorization: Bearer YOUR_JWT"

# Test email sync
curl -X POST http://localhost:8000/api/v1/emails/sync \
  -H "Authorization: Bearer YOUR_JWT"
```

### 7. Create Missing Backend Endpoints ⏱️ 1 hour

**Endpoints to Add**:

1. `GET /api/v1/documents`
   ```python
   # apps/api/routers/documents.py
   @router.get("")
   async def list_documents(
       page: int = 1,
       per_page: int = 50,
       case_id: UUID | None = None,
   ) -> DocumentListResponse:
       """List all documents across cases."""
       # Query evidence_links with pagination
   ```

2. `POST /api/v1/calendar/sync`
   ```python
   # apps/api/routers/calendar.py
   @router.post("/sync")
   async def trigger_calendar_sync(user_id: UUID) -> CalendarSyncResponse:
       """Trigger sync for Google + Outlook calendars."""
       await calendar_sync_service.sync_all(user_id)
   ```

**Testing**:
```bash
curl -X GET http://localhost:8000/api/v1/documents?per_page=10 \
  -H "Authorization: Bearer YOUR_JWT"
```

---

## 🟡 MEDIUM PRIORITY (After OAuth Works)

### 8. Wire Frontend to Backend ⏱️ 2 hours

**Pages to Connect**:

1. **AI Hub** (`apps/web/app/dashboard/ai/page.tsx`)
   ```typescript
   // Create hooks
   const useDraftDocument = () => useMutation({
     mutationFn: (data) => apiFetch('/ai/draft', token, { method: 'POST', body: JSON.stringify(data) })
   })

   const useSummarize = () => ...
   const useAnalyze = () => ...
   ```

2. **Legal Search** (`apps/web/app/dashboard/legal/page.tsx`)
   ```typescript
   const useLegalSearch = (query: string) => useQuery({
     queryKey: ['legal-search', query],
     queryFn: () => apiFetch(`/legal/search?q=${query}`, token)
   })

   const useLegalChat = () => useMutation(...)
   ```

3. **Graph** (`apps/web/app/dashboard/graph/page.tsx`)
   ```typescript
   const useCaseGraph = (caseId: string) => useQuery({
     queryKey: ['graph', caseId],
     queryFn: () => apiFetch(`/graph/case/${caseId}`, token)
   })
   ```

4. **Calendar** (`apps/web/app/dashboard/calendar/page.tsx`)
   ```typescript
   const useCalendarEvents = (filters) => useQuery({
     queryKey: ['calendar', filters],
     queryFn: () => apiFetch('/calendar/events', token, { params: filters })
   })
   ```

5. **Admin** (`apps/web/app/dashboard/admin/page.tsx`)
   ```typescript
   const useSystemHealth = () => useQuery({
     queryKey: ['admin-health'],
     queryFn: () => apiFetch('/admin/health', token)
   })

   const useIntegrations = () => useQuery({
     queryKey: ['admin-integrations'],
     queryFn: () => apiFetch('/admin/integrations', token)
   })
   ```

**Testing**:
- Open http://localhost:3000/dashboard/ai
- Should see AI features working
- No "Erreur de chargement" messages

### 9. Quality Assurance ⏱️ 1 hour

```bash
# Backend
cd /f/LexiBel
ruff check --fix apps/api
ruff format apps/api
python -m pytest apps/api/tests/ -x

# Frontend
cd apps/web
npx next build  # Fix all TypeScript errors
npm run lint
```

### 10. Manual Testing ⏱️ 1 hour

**Test Workflow**:

1. Login → Dashboard
   - [ ] Shows 5 cases
   - [ ] Shows 10 contacts
   - [ ] Shows stats

2. Cases → Create New
   - [ ] Create "Test Case"
   - [ ] Add contact
   - [ ] View timeline
   - [ ] Upload document

3. Contacts → Search
   - [ ] Search "Dupont"
   - [ ] View contact detail
   - [ ] See linked cases

4. Timeline
   - [ ] Filter by source
   - [ ] See 20 events

5. Billing
   - [ ] Create time entry
   - [ ] Submit for approval
   - [ ] Approve (if partner)
   - [ ] Generate invoice

6. Inbox
   - [ ] Validate pending item
   - [ ] Refuse item
   - [ ] Create case from item

7. Emails
   - [ ] See 5 threads
   - [ ] Open thread
   - [ ] Read messages
   - [ ] Link to case

8. Calls
   - [ ] See 3 calls
   - [ ] Play recording
   - [ ] View transcription

9. Calendar
   - [ ] See 3 events
   - [ ] Sync calendar

10. AI Hub
    - [ ] Summarize case
    - [ ] Draft document
    - [ ] Analyze document

11. Legal Search
    - [ ] Search "prescription"
    - [ ] Chat with AI
    - [ ] Explain article

12. Graph
    - [ ] View case graph
    - [ ] Check conflicts
    - [ ] Search entities

---

## 🟢 LOW PRIORITY (Polish & Optimization)

### 11. Performance Optimization

- [ ] Add Redis caching for frequently accessed data
- [ ] Optimize database queries (EXPLAIN ANALYZE)
- [ ] Add indexes on frequently queried columns
- [ ] Implement pagination on all list endpoints
- [ ] Add query result caching (React Query)

### 12. Security Hardening

- [ ] Add rate limiting (Redis + SlowAPI)
- [ ] Implement CSRF protection
- [ ] Add request signing for webhooks
- [ ] Enable Helmet.js for Next.js
- [ ] Configure CORS properly
- [ ] Add security headers (CSP, HSTS)

### 13. Monitoring & Observability

- [ ] Set up Sentry error tracking
- [ ] Add structured logging (JSON format)
- [ ] Implement health check endpoints
- [ ] Add metrics (Prometheus)
- [ ] Create Grafana dashboards
- [ ] Set up uptime monitoring

---

## 📦 Deployment Checklist

Before deploying to production:

- [ ] All tests pass
- [ ] Next.js build succeeds
- [ ] Environment variables documented
- [ ] Migrations run successfully
- [ ] Seed script tested
- [ ] Manual testing completed
- [ ] Security audit done
- [ ] Performance testing done
- [ ] Documentation complete
- [ ] Backup strategy in place

---

## 🎯 Definition of Done

LexiBel is **production-ready** when:

- ✅ All 23 tables exist and are populated
- ✅ All 145 endpoints return valid responses
- ✅ All 25 pages load without errors
- ✅ At least 3 integrations work (Google, Microsoft, OpenAI)
- ✅ All pytest tests pass (target: >90% coverage)
- ✅ Next.js build succeeds (0 errors)
- ✅ Manual testing shows no critical bugs
- ✅ Demo data is visible and realistic
- ✅ Documentation is complete
- ✅ Security best practices applied

---

**Estimated Total Time**: ~9 hours of focused work

**Current Progress**: ~60% complete (infrastructure ✅, integrations ⏸️, frontend wiring ⏸️)

**Next Session Focus**: 🔴 Docker + Migrations → 🟡 OAuth Services → 🟡 Frontend Wiring

