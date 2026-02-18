# AUDIT REPORT — LexiBel
Date: 2026-02-18
Auditeur: Claude (PM Senior — Mode READ-ONLY)

---

## Résumé Exécutif

**Score global: 76/100**

### Points forts
- Architecture backend **complète et cohérente** : 36/36 routers présents, 34/34 modèles DB, 17 migrations Alembic
- Design system **premium implémenté à 100%** : Crimson Pro ✅, Manrope ✅, Deep Slate ✅, Warm Gold ✅, animations ✅
- **40 fichiers de tests** backend couvrant tous les domaines critiques
- Infrastructure Docker **well-defined** : 9 services (PostgreSQL, Redis, Qdrant, Neo4j, MinIO, vLLM, API, Worker, Web)
- Documentation riche : 18 fichiers .md dans docs/ + CLAUDE.md + SKILL.md
- Fonctionnalités avancées en place : SENTINEL, LLM Gateway GDPR, OAuth SSO, AI Brain

### Points faibles
- **Build frontend BROKEN** : Conflit de version Next.js (package.json déclare v14.2.20, npx résout v16.1.6 globale)
- **6 pages de détail manquantes** : cases/[id], contacts/[id], emails/[id], calls/[id], sentinel/entity/[id], cases/[id]/conflicts
- **Aucun test frontend** (zéro fichier .test.tsx / .spec.tsx)
- `middleware.ts` déprécié dans Next.js v16 (doit être renommé en `proxy`)
- 2 modèles DB (`timeline_document.py`, `timeline_event.py`) non exportés dans `__init__.py`

---

## 1. Backend (score: 88/100)

### 1.1 Routers (36/36 ✅ — COMPLET)

| Router | Fichier | Lignes |
|--------|---------|--------|
| auth | apps/api/auth/router.py | ✅ |
| mfa | apps/api/auth/mfa_router.py | ✅ |
| cases | apps/api/routers/cases.py | 263 |
| contacts | apps/api/routers/contacts.py | 143 |
| timeline | apps/api/routers/timeline.py | 93 |
| documents | apps/api/routers/documents.py | 121 |
| inbox | apps/api/routers/inbox.py | 142 |
| time_entries | apps/api/routers/time_entries.py | 131 |
| invoices | apps/api/routers/invoices.py | 128 |
| third_party | apps/api/routers/third_party.py | 75 |
| webhook/ringover | apps/api/webhooks/ringover.py | ✅ |
| webhook/plaud | apps/api/webhooks/plaud.py | ✅ |
| integrations | apps/api/routers/integrations.py | 651 |
| events | apps/api/routers/events.py | 34 |
| bootstrap | apps/api/routers/bootstrap.py | 85 |
| search | apps/api/routers/search.py | 140 |
| ai | apps/api/routers/ai.py | 465 |
| migration | apps/api/routers/migration.py | 125 |
| dpa | apps/api/routers/dpa.py | 152 |
| outlook | apps/api/routers/outlook.py | 104 |
| ml | apps/api/routers/ml.py | 154 |
| graph | apps/api/routers/graph.py | 564 |
| agents | apps/api/routers/agents.py | 113 |
| admin | apps/api/routers/admin.py | 329 |
| mobile | apps/api/routers/mobile.py | 121 |
| ringover | apps/api/routers/ringover.py | 447 |
| legal_rag | apps/api/routers/legal_rag.py | 443 |
| calendar | apps/api/routers/calendar.py | 164 |
| emails | apps/api/routers/emails.py | 59 |
| calls | apps/api/routers/calls.py | 176 |
| transcriptions | apps/api/routers/transcriptions.py | 208 |
| dashboard | apps/api/routers/dashboard.py | 91 |
| oauth | apps/api/routers/oauth.py | 383 |
| cloud_documents | apps/api/routers/cloud_documents.py | 503 |
| llm | apps/api/routers/llm.py | 329 |
| sentinel *(optional)* | apps/api/routes/sentinel.py | ✅ |

> Nota bene : le router `sentinel` est importé avec `try/except` (defensive import). Il est présent mais ne sera inclus que si l'import réussit en runtime.

### 1.2 Modèles DB (34/34 ✅ — COMPLET)

Tous les modèles importés dans `packages/db/models/__init__.py` ont leur fichier correspondant :

| Modèle | Fichier | Lignes |
|--------|---------|--------|
| Tenant | tenant.py | 61 |
| User | user.py | 90 |
| AuditLog | audit_log.py | 70 |
| Case | case.py | 86 |
| Contact | contact.py | 71 |
| CaseContact | case_contact.py | 49 |
| InteractionEvent | interaction_event.py | 85 |
| EvidenceLink | evidence_link.py | 61 |
| InboxItem | inbox_item.py | 76 |
| TimeEntry | time_entry.py | 97 |
| Invoice | invoice.py | 113 |
| InvoiceLine | invoice_line.py | 69 |
| ThirdPartyEntry | third_party_entry.py | 71 |
| MigrationJob | migration_job.py | 83 |
| MigrationMapping | migration_mapping.py | 55 |
| Chunk | chunk.py | 47 |
| OAuthToken | oauth_token.py | 75 |
| CalendarEvent | calendar_event.py | 99 |
| EmailThread | email_thread.py | 86 |
| EmailMessage | email_message.py | 105 |
| CallRecord | call_record.py | 104 |
| Transcription | transcription.py | 99 |
| TranscriptionSegment | transcription_segment.py | 74 |
| BrainAction | brain_action.py | 96 |
| BrainInsight | brain_insight.py | 83 |
| BrainMemory | brain_memory.py | 64 |
| ProphetPrediction | prophet_prediction.py | 97 |
| ProphetSimulation | prophet_simulation.py | 76 |
| SentinelConflict | sentinel_conflict.py | 103 |
| SentinelEntity | sentinel_entity.py | 62 |
| AIAuditLog | ai_audit_log.py | 136 |
| CloudDocument | cloud_document.py | 150 |
| CloudSyncJob | cloud_sync_job.py | 86 |
| DocumentCaseLink | document_case_link.py | 62 |

⚠️ **ANOMALIE** : 2 fichiers modèle existent dans le répertoire mais **ne sont PAS importés dans `__init__.py`** :
- `packages/db/models/timeline_document.py` (77 lignes) — orphelin
- `packages/db/models/timeline_event.py` (120 lignes) — orphelin

Ces modèles ne seront pas découverts par Alembic. À investiguer.

### 1.3 Services (65+ fichiers — COMPLET)

**Services top-level :** webhook_service, dpa_service, outlook_service, search_service, third_party_service, invoice_service, lora_registry, time_service, timeline_service, backup_service, migration_service, audit_export_service, vector_service, chunking_service, sse_service, vllm_service, document_service, inbox_service, case_service, contact_service, action_extraction_service, transcription_service, rag_service, ringover_service, plaud_client, ringover_client, llm_gateway, rag_pipeline, calendar_sync_service, gmail_sync_service, microsoft_calendar_service, oauth_encryption_service, google_oauth_service, ringover_integration_service, microsoft_outlook_sync_service, microsoft_oauth_service, neo4j_client, qdrant_client, metrics, oauth_engine, email_sync, google_drive_sync, microsoft_onedrive_sync

**Sous-modules :**
- `services/agents/` : document_assembler, due_diligence_agent, emotional_radar (3 fichiers)
- `services/graph/` : graph_builder, neo4j_service, graph_rag_service, ner_service, conflict_detection_service, graph_sync_service (6 fichiers)
- `services/ml/` : linkage_ranker, deadline_extractor, email_triage (3 fichiers)
- `services/importers/` : forlex_importer, csv_importer, dpa_importer (3 fichiers)
- `services/sentinel/` : graph_sync, conflict_detector, enrichment, alerter (4 fichiers)
- `services/llm/` : data_classifier, anonymizer, gateway, audit_logger (4 fichiers)

### 1.4 Middleware (5/5 ✅)
- `middleware/tenant.py` ✅ — Multi-tenant JWT extraction
- `middleware/audit.py` ✅ — Audit trail
- `middleware/rate_limit.py` ✅ — Per-user/role rate limiting
- `middleware/security_headers.py` ✅ — CSP, HSTS, X-Request-ID
- `middleware/compression.py` ✅ — ETag/Compression
- `middleware/rbac.py` ✅ (présent mais **non utilisé dans main.py** — à vérifier)

### 1.5 Migrations Alembic (17/17)
| # | Fichier |
|---|---------|
| 001 | create_core_tables_and_rls |
| 002 | create_cases_contacts |
| 003 | create_timeline_ged |
| 004 | create_billing |
| 005 | create_migration |
| 006 | add_user_auth_columns |
| 007 | create_chunks_oauth_tokens |
| 008 | create_email_tables |
| 009 | create_calendar_events |
| 010 | create_call_transcription_tables |
| 011 | create_brain_tables |
| 012 | create_prophet_tables |
| 013 | create_sentinel_tables |
| 014 | create_timeline_tables |
| 015 | add_oauth_token_status_email |
| 016 | create_ai_audit_logs |
| 017 | cloud_documents_and_sync |

### 1.6 Dépendances (requirements.txt — COMPLET)
Catégories couvertes : FastAPI/Uvicorn, SQLAlchemy/asyncpg/Alembic, Redis/Celery, JWT/Auth/TOTP, OAuth (Google + Microsoft/MSAL), S3/boto3, Qdrant, Neo4j, ML/NLP (sentence-transformers, tiktoken, openai), Document parsing (pdfplumber, python-docx), Prometheus, pytest-timeout

---

## 2. Frontend (score: 62/100)

### 2.1 Pages Dashboard (24/30 — 6 MANQUANTES ❌)

| Page | Statut | Lignes |
|------|--------|--------|
| /dashboard | ✅ | 418 |
| /dashboard/cases | ✅ | 524 |
| /dashboard/cases/[id] | ❌ MANQUANT | — |
| /dashboard/cases/[id]/conflicts | ❌ MANQUANT | — |
| /dashboard/contacts | ✅ | 440 |
| /dashboard/contacts/[id] | ❌ MANQUANT | — |
| /dashboard/inbox | ✅ | 829 |
| /dashboard/billing | ✅ | 161 |
| /dashboard/calendar | ✅ | 215 |
| /dashboard/emails | ✅ | 189 |
| /dashboard/emails/[id] | ❌ MANQUANT | — |
| /dashboard/calls | ✅ | 207 |
| /dashboard/calls/[id] | ❌ MANQUANT | — |
| /dashboard/documents | ✅ | 654 |
| /dashboard/timeline | ✅ | 549 |
| /dashboard/search | ✅ | 230 |
| /dashboard/graph | ✅ | 331 |
| /dashboard/legal | ✅ | 399 |
| /dashboard/migration | ✅ | 518 |
| /dashboard/admin | ✅ | 110 |
| /dashboard/admin/integrations | ✅ | 410 |
| /dashboard/admin/llm | ✅ | 1601 |
| /dashboard/ai | ✅ | 415 |
| /dashboard/ai/documents | ✅ | 287 |
| /dashboard/ai/due-diligence | ✅ | 222 |
| /dashboard/ai/emotional-radar | ✅ | 263 |
| /dashboard/ai/transcription | ✅ | 440 |
| /dashboard/sentinel | ✅ | 200 |
| /dashboard/sentinel/conflicts | ✅ | 367 |
| /dashboard/sentinel/entity/[id] | ❌ MANQUANT | — |

> Impact UX majeur : cliquer sur un dossier, un contact, un email ou un appel mène à une page 404.

### 2.2 Design System (COMPLET ✅)

| Élément | Statut |
|---------|--------|
| Font Crimson Pro | ✅ (globals.css + tailwind.config.ts) |
| Font Manrope | ✅ (globals.css + tailwind.config.ts) |
| Couleur Deep Slate (#1E293B) | ✅ |
| Couleur Warm Gold (#D4AF37) | ✅ |
| Animations (fade, slide-up, scale-in, shimmer, pulse-subtle) | ✅ |
| Dark mode variables | ✅ (fondation posée) |
| Shadows ultra-subtiles | ✅ |
| Border radius minimal (corporate) | ✅ |

### 2.3 Composants UI (20 existants)

| Composant | Lignes |
|-----------|--------|
| AutoSaveIndicator.tsx | 70 |
| Avatar.tsx | 65 |
| Badge.tsx | 55 |
| Breadcrumb.tsx | 45 |
| Button.tsx | 55 |
| Card.tsx | 48 |
| ComponentShowcase.tsx | 281 |
| ContextMenu.tsx | 80 |
| DataTable.tsx | 242 |
| EmptyState.tsx | 68 |
| ErrorState.tsx | 28 |
| Input.tsx | 67 |
| LoadingSkeleton.tsx | 81 |
| Modal.tsx | 92 |
| QuickTest.tsx | 147 |
| Skeleton.tsx | 31 |
| StatCard.tsx | 57 |
| Tabs.tsx | 92 |
| Toast.tsx | 98 |
| Tooltip.tsx | 52 |

### 2.4 Dépendances Frontend (package.json)

| Lib | Version | Note |
|-----|---------|------|
| next | 14.2.20 | ⚠️ CONFLIT — système a v16.1.6 |
| react | ^18.2.0 | ✅ |
| next-auth | 5.0.0-beta.25 | ⚠️ Beta |
| @tanstack/react-query | ^5.20.0 | ✅ |
| zustand | ^4.5.0 | ✅ |
| zod | ^4.3.6 | ✅ v4 (breaking change vs v3) |
| cytoscape | ^3.33.1 | ✅ (graphe SENTINEL) |
| tailwindcss | ^3.4.0 | ✅ |
| vitest | ^1.2.0 | ✅ (mais 0 tests écrits) |

### 2.5 Build: **FAIL** ❌

```
▲ Next.js 16.1.6 (Turbopack)
⚠ The "middleware" file convention is deprecated → use "proxy"
Error: Turbopack build failed with 1 errors
Error: Next.js could not find next/package.json from F:\LexiBel\apps\web\app
```

**Cause racine** : `npx next build` résout la version globale (16.1.6) installée dans le workspace pnpm racine, au lieu de la v14 définie dans `apps/web/package.json`. Next.js 16 + Turbopack cherche le projet depuis `apps/web/app/` au lieu de `apps/web/`.

**Correction nécessaire** : Exécuter `pnpm install` depuis `apps/web/` et utiliser `pnpm next build` (local), ou aligner la version Next.js dans le workspace.

---

## 3. Infrastructure (score: 78/100)

### 3.1 Services Docker (9 définis dans docker-compose.yml)

| Service | Image | Port | Statut Config |
|---------|-------|------|---------------|
| postgres | postgres:16-alpine | 5434:5432 | ✅ healthcheck |
| redis | redis:7-alpine | 6381:6379 | ✅ healthcheck |
| qdrant | qdrant/qdrant:latest | 6333-6334 | ✅ |
| neo4j | neo4j:5-community | 7474, 7687 | ✅ healthcheck |
| vllm | custom Dockerfile | 8001:8000 | ⚠️ GPU only (profile: gpu) |
| minio | minio/minio:latest | 9000-9001 | ✅ |
| api | custom Dockerfile.api | 8000:8000 | ✅ depends_on healthy |
| worker | Dockerfile.api (Celery) | — | ✅ Celery 4 queues |
| web | custom Dockerfile.web | 3000 | ✅ |

⚠️ **Notes** :
- vLLM n'est disponible qu'en mode GPU (profile: `gpu`) — désactivé par défaut en dev
- Port PostgreSQL exposé sur 5434 (non-standard) → potentiel problème pour les outils externes
- Port Redis exposé sur 6381 (non-standard)

### 3.2 Production
- URL : `https://lexibel.clixite.cloud` (définie dans CORS origins de main.py)
- Statut prod : **non vérifié** (audit local uniquement)

---

## 4. Base de Données

### 4.1 Tables (34 modèles + potentiellement 2 orphelins)

Familles de tables :
- **Core** : tenants, users, audit_logs (3)
- **Legal** : cases, contacts, case_contacts, interaction_events, evidence_links, third_party_entries (6)
- **Communication** : inbox_items, email_threads, email_messages, call_records, transcriptions, transcription_segments (6)
- **Billing** : invoices, invoice_lines, time_entries (3)
- **Calendrier** : calendar_events (1)
- **Documents** : chunks, cloud_documents, cloud_sync_jobs, document_case_links (4)
- **Migration** : migration_jobs, migration_mappings (2)
- **AI/Brain** : brain_actions, brain_insights, brain_memories, prophet_predictions, prophet_simulations, ai_audit_logs (6)
- **SENTINEL** : sentinel_conflicts, sentinel_entities (2)
- **OAuth** : oauth_tokens (1)

### 4.2 Migrations
17 migrations appliquées séquentiellement — historique complet et cohérent.

---

## 5. Tests (score: 72/100)

### 5.1 Tests Backend (40 fichiers dans apps/api/tests/)

| Fichier | Domaine |
|---------|---------|
| test_auth.py | Authentification |
| test_mfa.py | MFA/TOTP |
| test_cases.py | Dossiers |
| test_contacts.py | Contacts |
| test_inbox.py | Inbox |
| test_billing.py | Facturation |
| test_timeline.py | Timeline |
| test_search.py | Recherche |
| test_migration.py | Migration |
| test_admin.py | Administration |
| test_dpa.py | DPA |
| test_mobile.py | Mobile API |
| test_agents.py | AI Agents |
| test_graph.py | Graph |
| test_graph_rag.py | Graph RAG |
| test_graph_sync.py | SENTINEL Graph Sync |
| test_conflict_detector.py | SENTINEL Détection |
| test_bce_enrichment.py | BCE Enrichissement |
| test_alerter.py | SENTINEL Alertes |
| test_sentinel_api.py | SENTINEL API |
| test_sentinel_models.py | SENTINEL Modèles |
| test_brain_models.py | Brain Modèles |
| test_prophet_models.py | Prophet Modèles |
| test_timeline_models.py | Timeline Modèles |
| test_ai.py | AI Général |
| test_llm_gateway.py | LLM Gateway (764 lignes!) |
| test_llm_security.py | LLM Sécurité (289 lignes) |
| test_integrations.py | Intégrations |
| test_brain.py | Brain |
| test_webhooks.py | Webhooks |
| test_health.py | Health Check |
| test_middleware.py | Middleware |
| test_security.py | Sécurité Générale |
| test_ml.py | ML Models |
| test_vllm.py | vLLM |
| test_sse.py | SSE |
| test_neo4j_client.py | Neo4j |
| test_qdrant_client.py | Qdrant |
| test_mvp_integration.py | Tests E2E Intégration |
| write_test.py | *(helper — pas un vrai test)* |

### 5.2 Tests Frontend
**ZÉRO test frontend** — aucun fichier .test.tsx, .spec.tsx, .test.ts, .spec.ts dans apps/web/ (hors node_modules). Vitest est installé mais non utilisé.

---

## 6. Documentation (score: 85/100)

### Fichiers à la racine
- `CLAUDE.md` — Instructions Claude Code
- `SKILL.md` — Skills définis
- `guide_setup.md` — Guide de démarrage

### docs/ (18 fichiers)
- `NEXT-STEPS.md` — Roadmap
- `INNOVATIONS-2026.md` — Innovations planifiées
- `RINGOVER_INTEGRATION.md` — Guide intégration Ringover
- `RINGOVER_ARCHITECTURE.md` — Architecture Ringover
- `INTEGRATIONS_SETUP.md` — Guide setup intégrations
- `microsoft_oauth_setup.md` — OAuth Microsoft
- `PLAUD_INTEGRATION.md` — Intégration PLAUD
- `E2E_TEST_REPORT.md` — Rapport de tests E2E (235 lignes)
- `compliance/GDPR_AI_COMPLIANCE.md` — Conformité GDPR/AI Act (210 lignes)
- `infrastructure/README.md` — Infrastructure générale
- `infrastructure/neo4j-setup.md` — Setup Neo4j
- `infrastructure/qdrant-setup.md` — Setup Qdrant
- `infrastructure/monitoring.md` — Monitoring Prometheus
- `database/models-overview.md` — Vue d'ensemble modèles
- `plans/phase-1-foundations.md` — Plan Phase 1
- `plans/2026-02-17-innovations-legal-tech-design.md` — Design innovations
- `plans/2026-02-17-4-innovations-implementation-plan.md` — Plan implémentation
- `plans/2026-02-18-phase2-brain-ai-implementation.md` — Phase 2 Brain AI (récent)

---

## 7. Git

### Branches
- `main` (unique branche locale + remote)

### 30 derniers commits (chronologique → récent)
```
d4f4666 feat: enterprise SaaS premium UX transformation
bd4ffeb feat(sentinel): add graph sync service for Neo4j
a748bfd feat(sentinel): add BCE API enrichment service
6707fff feat(sentinel): add real-time conflict alert system
322f4d5 feat(sentinel): add Pydantic schemas for API
c564ec3 feat(sentinel): add REST API endpoints
54d9d20 refactor(sentinel): improve schema type safety
840d072 fix(sentinel): resolve 5 critical spec compliance issues
2bf557c fix(sentinel): resolve critical code quality issues
b286803 feat(sentinel): register SENTINEL routes in main FastAPI app
0dfefc5 fix: backend API hardening
2b2febe fix: frontend polish — all pages verified, API calls fixed
3573314 Fix: use text() for raw SQL in seed script
40ee60d Update seed script: use admin123 password
fb6b32b Fix: add text to local imports in seed_data function
294d2a6 Fix: remove id from CaseContact (composite PK)
5f3974c Fix: correct Invoice field names
817ef76 Fix: add tenant_id to InvoiceLine creation
bfe634d Fix: correct ThirdPartyEntry field names
75a56b7 Fix: update InboxItem to match new model schema
52ecb62 feat: OAuth SSO Wizard — Google + Microsoft 365
97d864f Add E2E test report — all core endpoints functional
0181ead feat: SENTINEL UI — conflict detection dashboard + graph
93bafeb feat: LLM Gateway GDPR — 7 providers, data classification, AI Act
3825620 fix: LLM Gateway — Gemini routing, ruff cleanups, security tests
3c56... fix: add PyJWT dependency for JWT auth
bfe6... fix: ConflictCard accept ConflictDetail without status field
2a85... fix: add msal dependency for Microsoft OAuth
a309... fix: Zod v4 compatibility — z.record() key+value schemas
```

### Fichiers les plus actifs (HEAD~10..HEAD — 49 fichiers, +11076 lignes)
- `apps/api/services/llm/gateway.py` (+1006 lignes)
- `apps/web/app/dashboard/admin/llm/page.tsx` (+1601 lignes)
- `apps/api/tests/test_llm_gateway.py` (+764 lignes)
- `apps/api/services/email_sync.py` (+517 lignes)
- `apps/api/routers/oauth.py` (+383 lignes)

---

## 8. Taille du Projet

| Métrique | Valeur |
|----------|--------|
| Fichiers Python | ~259 (tous, hors __pycache__) |
| Fichiers TypeScript/TSX | 114 (hors node_modules) |
| Routers FastAPI | 36 |
| Modèles SQLAlchemy | 34 |
| Migrations Alembic | 17 |
| Services backend | 65+ fichiers |
| Tests backend | 40 fichiers |
| Pages frontend | 24/30 |
| Composants UI | 20 |
| Fichiers docs .md | 18 (hors node_modules) |

---

## 9. Recommandations Prioritaires

### P0 — CRITIQUE (bloquant prod/dev)

1. **Corriger le build Next.js**
   - Cause : `npx next build` utilise Next.js 16 global au lieu de v14 local
   - Fix : Lancer depuis `apps/web/` avec `pnpm next build` après `pnpm install`
   - Ou : Mettre à jour `package.json` vers Next.js 16 et corriger la config Turbopack (`turbopack.root`)
   - Impact : Build actuellement impossible → déploiement bloqué

2. **Renommer `middleware.ts` → `proxy.ts`** (ou mettre à jour pour Next.js 16)
   - La convention `middleware` est dépréciée dans Next.js 16

### P1 — HAUTE PRIORITÉ (impact UX majeur)

3. **Créer les 6 pages de détail manquantes**
   - `/dashboard/cases/[id]/page.tsx` — page dossier (navigation primaire!)
   - `/dashboard/contacts/[id]/page.tsx` — fiche contact
   - `/dashboard/emails/[id]/page.tsx` — fil email
   - `/dashboard/calls/[id]/page.tsx` — détail appel
   - `/dashboard/sentinel/entity/[id]/page.tsx` — entité SENTINEL
   - `/dashboard/cases/[id]/conflicts/page.tsx` — conflits par dossier

4. **Ajouter `timeline_document.py` et `timeline_event.py` à `__init__.py`**
   - Ces 2 modèles existent mais ne sont pas découverts par Alembic → risque de tables non créées

### P2 — IMPORTANTE (qualité)

5. **Vérifier le middleware RBAC** (`middleware/rbac.py`) non utilisé dans `main.py`
   - S'il doit être utilisé, l'activer ; sinon le documenter ou supprimer

6. **Écrire des tests frontend**
   - Vitest est installé mais 0 test écrit → couverture frontend = 0%
   - Commencer par les composants critiques : Button, Modal, DataTable

7. **Standardiser les ports Docker**
   - PostgreSQL sur 5434 (standard = 5432) → confusion outillage
   - Redis sur 6381 (standard = 6379) → confusion outillage
   - Documenter explicitement ces choix

### P3 — AMÉLIORATION (dette technique)

8. **Aligner version Next.js dans le workspace pnpm**
   - Risque de divergences entre `node_modules` racine et `apps/web/node_modules`

9. **next-auth 5.0.0-beta.25** — Version beta en production
   - Surveiller la stabilité, envisager de verrouiller sur une version stable

10. **Zod v4** (4.3.6) — Breaking change important vs v3
    - Le commit `fix: Zod v4 compatibility` suggère la migration est faite, mais vérifier exhaustivement

---

*Rapport généré en mode READ-ONLY — aucune modification effectuée sur le code source.*
