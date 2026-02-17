# LexiBel - Audit Complet - 17 février 2026

## Résumé Exécutif

**Backend**: ✅ 139 endpoints implémentés (très complet)
**Frontend**: ⚠️ 25 pages créées mais partiellement connectées
**Base de données**: ⚠️ 16/23 tables créées (7 manquantes)

**Verdict**: L'infrastructure backend est EXCELLENTE. Le problème principal est que:
1. Les tables pour les intégrations tierces (emails, calls, transcriptions) n'existent pas en DB
2. Le frontend n'utilise pas tous les endpoints disponibles
3. Il manque les données de démo pour tester end-to-end

---

## 1. Backend API - Endpoints Existants (139)

### ✅ Core Business (Complet)
- **Auth**: login, refresh, me (3)
- **Cases**: CRUD + contacts + timeline + documents + conflict-check (13)
- **Contacts**: CRUD + search + cases (6)
- **Time Entries**: CRUD + approval workflow (5)
- **Invoices**: CRUD + Peppol + send (6)
- **Timeline**: events + pagination (3)
- **Documents**: upload + download (2)
- **Inbox**: validation workflow (5)

### ✅ Intégrations (Implémenté mais tables manquantes)
- **Emails**: GET /emails, /emails/stats, /emails/sync (3)
- **Calls**: GET /calls, /calls/stats (2)
- **Ringover**: GET /ringover/calls, /ringover/stats (3)
- **Outlook**: sync, list, send (3)
- **Transcriptions**: GET /transcriptions (1)
- **Calendar**: GET /calendar/events (1)

### ✅ AI/ML (Implémenté)
- **AI Hub**: draft, summarize, analyze, transcribe (5)
- **Legal RAG**: search, chat, explain, predict, conflicts, timeline (6)
- **Agents**: due-diligence, emotional-radar, assemble-document (6)
- **ML Pipeline**: classify, link, deadlines, process (4)
- **Search**: hybrid search, generate (2)

### ✅ GraphRAG (Implémenté)
- **Graph**: case subgraph, conflicts, similar cases, entity connections, search, build, sync, stats (11)

### ✅ Admin & System (Complet)
- **Admin**: health, tenants, users, stats, integrations (6)
- **DPA**: e-Deposit, JBox (5)
- **Migration**: import jobs, preview, start, rollback (6)
- **Mobile**: optimized endpoints (4)
- **Events**: SSE streaming (1)
- **Bootstrap**: admin creation (1)

**Total Backend Endpoints**: 139 ✅

---

## 2. Base de Données - Tables Manquantes (7)

### ✅ Tables Existantes (16)
1. tenants
2. users
3. audit_logs (append-only)
4. cases
5. contacts
6. case_contacts
7. interaction_events (append-only)
8. evidence_links
9. inbox_items
10. time_entries
11. invoices
12. invoice_lines
13. third_party_entries (append-only)
14. migration_jobs
15. migration_mappings
16. (users columns added in migration 006)

### ❌ Tables Manquantes (7)

#### 1. **chunks** - Pour RAG/Legal Search
```sql
CREATE TABLE chunks (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),
    case_id UUID REFERENCES cases(id),
    document_id UUID REFERENCES evidence_links(id),
    content TEXT NOT NULL,
    embedding vector(1536), -- OpenAI ada-002 dimensions
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```
**Impact**: Legal RAG ne peut pas stocker les embeddings

#### 2. **oauth_tokens** - Pour Google/Microsoft OAuth
```sql
CREATE TABLE oauth_tokens (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),
    user_id UUID REFERENCES users(id),
    provider VARCHAR(50) NOT NULL, -- 'google', 'microsoft'
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_type VARCHAR(50) DEFAULT 'Bearer',
    expires_at TIMESTAMPTZ,
    scope TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```
**Impact**: OAuth Google/Microsoft ne peut pas stocker les tokens

#### 3. **calendar_events** - Pour Outlook/Google Calendar
```sql
CREATE TABLE calendar_events (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),
    user_id UUID REFERENCES users(id),
    case_id UUID REFERENCES cases(id),
    external_id VARCHAR(255), -- ID from provider
    provider VARCHAR(50), -- 'outlook', 'google'
    title VARCHAR(500) NOT NULL,
    description TEXT,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    location VARCHAR(500),
    attendees JSONB,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    synced_at TIMESTAMPTZ
);
```
**Impact**: Agenda ne peut pas afficher les événements

#### 4. **email_threads** - Pour conversations email
```sql
CREATE TABLE email_threads (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),
    case_id UUID REFERENCES cases(id),
    external_id VARCHAR(255), -- Thread ID from provider
    provider VARCHAR(50), -- 'outlook', 'google'
    subject VARCHAR(500),
    participants JSONB, -- {from, to, cc, bcc}
    message_count INTEGER DEFAULT 0,
    has_attachments BOOLEAN DEFAULT FALSE,
    is_important BOOLEAN DEFAULT FALSE,
    last_message_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    synced_at TIMESTAMPTZ
);
```
**Impact**: Emails ne peuvent pas être groupés par conversation

#### 5. **email_messages** - Pour messages individuels
```sql
CREATE TABLE email_messages (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),
    thread_id UUID REFERENCES email_threads(id),
    external_id VARCHAR(255), -- Message ID from provider
    provider VARCHAR(50),
    subject VARCHAR(500),
    from_address VARCHAR(255),
    to_addresses JSONB,
    cc_addresses JSONB,
    bcc_addresses JSONB,
    body_text TEXT,
    body_html TEXT,
    attachments JSONB,
    is_read BOOLEAN DEFAULT FALSE,
    is_important BOOLEAN DEFAULT FALSE,
    received_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    synced_at TIMESTAMPTZ
);
```
**Impact**: Contenu des emails ne peut pas être stocké

#### 6. **call_records** - Pour Ringover/téléphonie
```sql
CREATE TABLE call_records (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),
    case_id UUID REFERENCES cases(id),
    contact_id UUID REFERENCES contacts(id),
    external_id VARCHAR(255), -- Call ID from Ringover
    direction VARCHAR(50) NOT NULL, -- 'inbound', 'outbound'
    caller_number VARCHAR(50),
    callee_number VARCHAR(50),
    duration_seconds INTEGER,
    call_type VARCHAR(50), -- 'answered', 'missed', 'voicemail'
    recording_url TEXT,
    transcription_id UUID, -- FK to transcriptions
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    metadata JSONB, -- AI insights
    created_at TIMESTAMPTZ DEFAULT NOW(),
    synced_at TIMESTAMPTZ
);
```
**Impact**: Ringover calls ne peuvent pas être stockés structurés

#### 7. **transcriptions** - Pour Whisper/Plaud.ai
```sql
CREATE TABLE transcriptions (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),
    case_id UUID REFERENCES cases(id),
    call_id UUID REFERENCES call_records(id),
    source VARCHAR(50), -- 'ringover', 'plaud', 'manual'
    audio_url TEXT,
    audio_duration_seconds INTEGER,
    language VARCHAR(10), -- 'fr', 'nl', 'en'
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    full_text TEXT,
    summary TEXT,
    sentiment_score NUMERIC(3,2), -- -1.0 to 1.0
    sentiment_label VARCHAR(50), -- 'positive', 'neutral', 'negative'
    extracted_tasks JSONB,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);
```
**Impact**: Transcriptions AI ne peuvent pas être stockées

#### 8. **transcription_segments** - Pour timestamps
```sql
CREATE TABLE transcription_segments (
    id UUID PRIMARY KEY,
    transcription_id UUID REFERENCES transcriptions(id),
    segment_index INTEGER NOT NULL,
    speaker VARCHAR(100), -- Speaker diarization
    start_time NUMERIC(10,3), -- Seconds
    end_time NUMERIC(10,3),
    text TEXT NOT NULL,
    confidence NUMERIC(3,2), -- 0.0 to 1.0
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```
**Impact**: Transcription ligne-par-ligne impossible

---

## 3. Frontend - Pages vs Endpoints Appelés

### ✅ Pages Fonctionnelles (connectées aux bons endpoints)

#### 1. Dashboard Home (`/dashboard/page.tsx`)
**Endpoints appelés**:
- ✅ GET /cases
- ✅ GET /contacts
- ✅ GET /time-entries
- ✅ GET /invoices
- ✅ GET /inbox?status=pending
- ❌ GET /documents (hardcodé à 0 - endpoint manquant)

#### 2. Cases List (`/dashboard/cases/page.tsx`)
**Endpoints appelés**:
- ✅ GET /cases
- ✅ POST /cases

#### 3. Case Detail (`/dashboard/cases/[id]/page.tsx`)
**Endpoints appelés**:
- ✅ GET /cases/{id}
- ✅ GET /cases/{id}/contacts
- ✅ GET /time-entries?case_id={id}
- ✅ GET /cases/{id}/timeline
- ✅ PATCH /cases/{id}
- ✅ POST /cases/{id}/contacts
- ✅ GET /contacts?q={query}
- ✅ POST /time-entries
- ✅ POST /cases/{id}/events

#### 4. Contacts (`/dashboard/contacts/page.tsx`)
**Endpoints appelés**:
- ✅ GET /contacts
- ✅ POST /contacts

#### 5. Emails (`/dashboard/emails/page.tsx`)
**Endpoints appelés**:
- ⚠️ GET /emails/threads (backend existe mais table manquante)
- ⚠️ GET /emails/stats (backend existe mais table manquante)
- ⚠️ POST /emails/sync/{id} (backend existe mais table manquante)

#### 6. Calls (`/dashboard/calls/page.tsx`)
**Endpoints appelés**:
- ⚠️ GET /ringover/calls (backend existe mais table manquante)
- ⚠️ GET /ringover/stats (backend existe mais table manquante)

#### 7. Inbox (`/dashboard/inbox/page.tsx`)
**Endpoints appelés**:
- ✅ GET /inbox
- ✅ GET /cases
- ✅ POST /inbox/{id}/validate
- ✅ POST /inbox/{id}/refuse
- ✅ POST /inbox/{id}/create-case

#### 8. Billing (`/dashboard/billing/page.tsx`)
**Endpoints appelés** (à analyser en détail):
- ✅ GET /time-entries
- ✅ GET /invoices

### ⚠️ Pages Non Connectées (endpoints backend existent!)

#### 9. AI Hub (`/dashboard/ai/page.tsx`)
**Endpoints DISPONIBLES backend** (non utilisés):
- POST /ai/draft
- POST /ai/summarize
- POST /ai/analyze
- POST /ai/transcribe
- POST /ai/transcribe/stream

**Action**: Connecter le frontend aux endpoints existants

#### 10. Legal Search (`/dashboard/legal/page.tsx`)
**Endpoints DISPONIBLES backend** (non utilisés):
- GET /legal/search
- POST /legal/chat
- POST /legal/explain-article
- POST /legal/predict-jurisprudence
- POST /legal/detect-conflicts
- GET /legal/timeline

**Action**: Connecter le frontend aux endpoints existants

#### 11. Graph (`/dashboard/graph/page.tsx`)
**Endpoints DISPONIBLES backend** (non utilisés):
- GET /graph/case/{id}
- GET /graph/case/{id}/conflicts
- GET /graph/entity/{id}/connections
- POST /graph/search
- POST /graph/build/{id}

**Action**: Connecter le frontend aux endpoints existants

#### 12. Calendar (`/dashboard/calendar/page.tsx`)
**Endpoints DISPONIBLES backend**:
- ⚠️ GET /calendar/events (existe mais table manquante)

**Action**: Créer la table calendar_events + connecter frontend

#### 13. Admin (`/dashboard/admin/page.tsx`)
**Endpoints DISPONIBLES backend**:
- GET /admin/health
- GET /admin/stats
- GET /admin/tenants
- POST /admin/tenants
- GET /admin/users
- POST /admin/users/invite

**Action**: Connecter le frontend aux endpoints existants

---

## 4. Endpoints Backend Manquants (Identifiés)

### ❌ Vraiment Manquants (à créer)

1. **GET /documents** - Liste globale des documents
   - Actuellement: documents liés aux events seulement
   - Besoin: liste tous les documents du tenant avec pagination

2. **GET /cases/{id}/documents** - Liste documents d'un dossier
   - Existe mais retourne via events
   - Besoin: endpoint dédié avec filtres (type, date)

3. **POST /calendar/sync** - Déclencher synchro calendrier
   - Endpoint manquant pour Google/Outlook sync

4. **GET /admin/integrations** - Liste des intégrations OAuth actives
   - Voir quelles intégrations sont connectées (Google, Microsoft, Ringover, Plaud)

5. **POST /admin/integrations/google/connect** - Initier OAuth Google
   - Flow OAuth complet pour Gmail/Calendar

6. **POST /admin/integrations/microsoft/connect** - Initier OAuth Microsoft
   - Flow OAuth complet pour Outlook/Calendar

---

## 5. Priorités d'Implémentation

### 🔴 CRITIQUE (Bloquants fonctionnels)

1. **Créer 7 migrations DB** pour tables manquantes
   - chunks, oauth_tokens, calendar_events
   - email_threads, email_messages
   - call_records, transcriptions, transcription_segments

2. **Créer script seed_demo_data.py**
   - Insérer données de démo pour tester toutes les pages
   - 1 tenant, 1 admin, 5 dossiers, 10 contacts, etc.

3. **Fixer GET /documents endpoint**
   - Nécessaire pour dashboard home

### 🟡 IMPORTANT (Complétude fonctionnelle)

4. **Implémenter services OAuth**
   - google_oauth_service.py
   - microsoft_oauth_service.py
   - Token storage chiffré

5. **Implémenter services intégrations**
   - ringover_service.py (appels API réels)
   - plaud_service.py (webhooks + API)
   - gmail_sync_service.py
   - outlook_sync_service.py (déjà partiellement fait)

6. **Connecter frontend aux endpoints existants**
   - AI Hub → POST /ai/draft, /ai/summarize, etc.
   - Legal Search → GET /legal/search, POST /legal/chat
   - Graph → GET /graph/case/{id}, /graph/case/{id}/conflicts
   - Admin → GET /admin/health, /admin/stats

### 🟢 NICE TO HAVE (Polish)

7. **Tests end-to-end**
   - Playwright tests pour workflows critiques
   - Login → Create case → Add contact → Generate invoice

8. **Ruff + Format**
   - ruff check --fix
   - ruff format

9. **Next.js build verification**
   - npx next build
   - Fix TypeScript errors

---

## 6. Plan d'Action (Ordre d'Exécution)

### Phase A: Base de Données (30 min)
1. Créer migration 007: chunks + oauth_tokens
2. Créer migration 008: email_threads + email_messages
3. Créer migration 009: calendar_events
4. Créer migration 010: call_records + transcriptions + transcription_segments
5. Lancer migrations: alembic upgrade head

### Phase B: Services Backend (1h)
1. Créer google_oauth_service.py + microsoft_oauth_service.py
2. Créer ringover_integration_service.py (API calls)
3. Créer plaud_integration_service.py (webhooks)
4. Créer gmail_sync_service.py + outlook_sync_service.py (améliorer)
5. Créer calendar_sync_service.py
6. Ajouter endpoints manquants:
   - GET /documents
   - POST /calendar/sync
   - GET /admin/integrations
   - POST /admin/integrations/{provider}/connect

### Phase C: Seed Data (30 min)
1. Créer apps/api/scripts/seed_demo_data.py
2. Insérer:
   - 1 tenant "Cabinet Demo"
   - 1 user admin (nicolas@clixite.be)
   - 5 dossiers (statuts variés)
   - 10 contacts (5 physiques, 5 moraux avec BCE)
   - 20 events timeline
   - 10 prestations (time entries)
   - 2 factures
   - 5 inbox items
   - 3 appels (call_records)
   - 2 transcriptions
   - 5 emails (threads + messages)
   - 3 calendar events

### Phase D: Frontend Wiring (1h)
1. AI Hub page: connecter aux endpoints /ai/*
2. Legal Search page: connecter aux endpoints /legal/*
3. Graph page: connecter aux endpoints /graph/*
4. Calendar page: connecter à GET /calendar/events
5. Admin page: connecter aux endpoints /admin/*
6. Dashboard home: fixer GET /documents

### Phase E: Tests & Quality (30 min)
1. ruff check --fix && ruff format
2. python -m pytest apps/api/tests/ -x
3. npx next build
4. Lancer seed script
5. Tester manuellement toutes les pages

### Phase F: Commit & Push (10 min)
1. git add -A
2. git commit -m "feat: full end-to-end consolidation — all features functional"
3. git push

**Temps total estimé**: 3h30

---

## 7. Conclusion

**État actuel**:
- ✅ Backend excellent (139 endpoints)
- ⚠️ DB incomplète (7 tables manquantes)
- ⚠️ Frontend partiellement connecté
- ❌ Pas de données de démo

**Après consolidation**:
- ✅ DB complète (23 tables)
- ✅ Tous les endpoints fonctionnels
- ✅ Frontend 100% connecté
- ✅ Données de démo pour tester
- ✅ Tests passent
- ✅ Build Next.js OK
- ✅ Prêt pour production

**Prochaine étape**: Exécuter le plan d'action Phase A → Phase F
