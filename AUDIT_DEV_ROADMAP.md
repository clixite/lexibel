# LEXIBEL — AUDIT COMPLET & ROADMAP DE DEVELOPPEMENT

**Date**: 01/03/2026
**Auditeur**: Ingenieur SaaS Senior + Tests terrain production
**URL**: https://lexibel.clixite.cloud
**Branche**: main (12 sprints, LXB-001 a LXB-070)

---

## SECTION 1 — ETAT ACTUEL DU PROJET

### 1.1 Metriques cle

| Metrique | Valeur |
|----------|--------|
| Routers API | 36 fichiers, 33 routes actives |
| Services backend | 54+ services dans apps/api/services/ |
| Modeles DB | 38 modeles SQLAlchemy |
| Migrations Alembic | 19 versions |
| Tests backend | 420+ (pytest) |
| Tests frontend | 0 |
| Pages frontend | 38 pages (25000 LOC total) |
| Composants UI | 25+ composants reutilisables |
| Middleware | 7 couches (CORS, GZip, Security, Tenant, RateLimit, Audit, Compression) |
| Containers Docker | 7 (postgres, redis, qdrant, neo4j, minio, api, web) |
| CI/CD | GitHub Actions (lint + tests + build + Trivy security + deploy SSH) |

### 1.2 Architecture validee

- **Multi-tenancy PostgreSQL + RLS** : `SET LOCAL app.current_tenant_id` par session, TenantMixin sur chaque modele
- **Auth JWT HS256** : access 30min + refresh 7j, MFA TOTP
- **RBAC** : 7 roles (super_admin, admin, partner, associate, junior, secretary, accountant)
- **Frontend Next.js 14** : App Router, useSession, design system complet (Crimson Pro + Manrope)
- **IA** : Brain orchestrator, SENTINEL conflits, Legal RAG, LLM gateway multi-provider, ML (deadline extractor, email triage, linkage ranker)
- **Graph** : Neo4j integration (NER, conflict detection, graph RAG)
- **Stockage** : MinIO S3-compatible, Qdrant vector search

---

## SECTION 2 — 4 BUGS CRITIQUES IDENTIFIES EN PRODUCTION

### BUG #1 — Contacts : API 500 (CRITIQUE)

**Symptome** : `/dashboard/contacts` affiche "API 500: Internal Server Error", 100% reproductible
**Localisation** : `apps/api/routers/contacts.py` → `apps/api/services/contact_service.py`

**Cause racine probable** :
Le modele `Contact` (`packages/db/models/contact.py`) herite de `TenantMixin` (qui definit `tenant_id`) ET redefinit `tenant_id` manuellement (ligne 30-34). Cette double definition peut causer un conflit SQLAlchemy au runtime.

Verification additionnelle necessaire :
- Verifier si la migration 019 (ajout colonne `metadata` JSONB) a bien ete appliquee en production
- Verifier la politique RLS sur la table `contacts` en production
- Checker les logs serveur : `docker logs lexibel-api-1 --tail 100`

**Fichiers a corriger** :
- `packages/db/models/contact.py` : Supprimer la redefinition de `tenant_id` (lignes 30-34) puisque `TenantMixin` le fournit deja
- Verifier `packages/db/migrations/versions/019_add_contact_metadata.py` est appliquee

**Commande de debug** :
```bash
ssh root@76.13.46.55 "docker exec lexibel-api-1 python -c \"
from packages.db.models.contact import Contact
print(Contact.__table__.columns.keys())
\""
```

---

### BUG #2 — Facturation : "Cannot read properties of undefined (reading 'length')" (CRITIQUE)

**Symptome** : `/dashboard/billing` affiche "Erreur de chargement - Cannot read properties of undefined (reading 'length')"
**Localisation** : `apps/web/app/dashboard/billing/TimesheetView.tsx` (ligne 77 et 385)

**Cause racine** :
`TimesheetView.tsx` ligne 73-78 fait :
```typescript
apiFetch<{ items: TimeEntry[] }>("/time-entries", token, { tenantId })
.then(([timeData, caseData]) => {
    setEntries(timeData.items);  // Si items est undefined → entries = undefined
    setCases(caseData.items);
})
```
Puis ligne 385 : `entries.length === 0` crash si `entries` est `undefined`.

Le probleme peut venir de :
1. L'API `/time-entries` retourne un format different de `{items: [...]}` en production
2. La serialisation Pydantic `TimeEntryResponse.model_validate()` echoue sur certains champs

**Fichiers a corriger** :
- `apps/web/app/dashboard/billing/TimesheetView.tsx` : Ajouter un garde defensif :
  ```typescript
  setEntries(timeData?.items || []);
  setCases(caseData?.items || []);
  ```
- Meme correction dans `apps/web/app/dashboard/billing/InvoiceList.tsx` ligne 64
- Meme correction dans `apps/web/app/dashboard/billing/ThirdPartyView.tsx` ligne 73

---

### BUG #3 — Calendrier : "C is not iterable" (CRITIQUE)

**Symptome** : `/dashboard/calendar` affiche "Erreur de chargement - C is not iterable"
**Localisation** : `apps/web/app/dashboard/calendar/page.tsx` + `apps/api/routers/calendar.py`

**Cause racine confirmee — 3 mismatches API/Frontend** :

**Mismatch 1 (CRASH)** : `GET /calendar/events`
- **Frontend** (ligne 200-204) : `apiFetch<CalendarEvent[]>(...)` attend un tableau plat
- **Backend** (calendar.py lignes 67-86) : retourne `{"events": [...], "total": N, "page": N, "per_page": N}`
- Le frontend fait `setEvents(res)` avec un objet au lieu d'un tableau → `events.map()` crash → "C is not iterable" en build minifie

**Fix** :
```typescript
// page.tsx ligne 200-204 : changer
const res = await apiFetch<{events: CalendarEvent[]}>(`/calendar/events${query}`, accessToken);
setEvents(res.events || []);
```

**Mismatch 2** : `GET /calendar/stats`
- **Frontend** attend : `{ total_events, today_events, upcoming_week }`
- **Backend** retourne : `{ total, today, upcoming }`
- **Fix** : Renommer les cles dans `calendar.py` lignes 147-151

**Mismatch 3** : Champs manquants dans les events
- Frontend attend : `date`, `time`, `attendees[]`
- Backend ne retourne que : `start_time`, `end_time`, `location`, `provider`
- **Fix** : Ajouter les champs derives dans la serialisation backend

**Fichiers a corriger** :
1. `apps/web/app/dashboard/calendar/page.tsx` — ligne 200-204 : unwrap `res.events`
2. `apps/api/routers/calendar.py` — lignes 67-86 : ajouter `date`, `time`, `attendees` dans la reponse
3. `apps/api/routers/calendar.py` — lignes 147-151 : renommer `total`→`total_events`, `today`→`today_events`, `upcoming`→`upcoming_week`

---

### BUG #4 — Appels : API 500 (CRITIQUE)

**Symptome** : `/dashboard/calls` affiche "API 500: Internal Server Error", 100% reproductible
**Localisation** : `apps/api/routers/calls.py`

**Cause racine confirmee — Colonnes inexistantes** :
Le router `calls.py` reference 5 colonnes qui N'EXISTENT PAS sur le modele `InteractionEvent` :

| Ligne | Colonne utilisee | Colonne reelle |
|-------|-----------------|----------------|
| 110 | `InteractionEvent.interaction_type` | `InteractionEvent.event_type` |
| 115 | `InteractionEvent.direction` | `InteractionEvent.metadata_["direction"]` (JSONB) |
| 131 | `event.duration_seconds` | `event.metadata_.get("duration_seconds")` |
| 132 | `event.transcript` | `event.metadata_.get("transcript")` |
| 126 | `event.contact_id` | `event.metadata_.get("contact_id")` |

Le modele `InteractionEvent` (`packages/db/models/interaction_event.py`) a ces colonnes :
`id, tenant_id, case_id, source, event_type, title, body, occurred_at, metadata_, created_by, created_at`

Le router `ringover.py` utilise CORRECTEMENT le meme modele (reference) :
- `InteractionEvent.event_type == "CALL"` (ligne 198)
- `InteractionEvent.metadata_["direction"].astext` (ligne 202)

**Fichiers a corriger** :
1. `apps/api/routers/calls.py` — Fonction `get_calls()` : remplacer toutes les references aux colonnes inexistantes par les champs corrects de `InteractionEvent`
2. `apps/api/routers/calls.py` — Fonction `get_call_stats()` : reecrire completement (impossible de faire `func.avg()` sur JSONB — calculer en Python comme dans `ringover.py` lignes 416-448)

---

## SECTION 3 — RAPPORT DE TEST TERRAIN COMPLET

### 3.1 Fonctionnalites testees et operationnelles

| # | Module | Pages testees | Status | Notes |
|---|--------|--------------|--------|-------|
| 1 | **Login/Auth** | Login page | OK | Branding, JWT, session refresh |
| 2 | **Dashboard** | /dashboard | OK | KPIs, Brain summary, deadlines, workload chart |
| 3 | **Dossiers** | /cases, /cases/new, /cases/[id] | OK | CRUD complet, 7 etapes creation, 12 types de droit |
| 4 | **Intelligence IA** | /brain, /ai, /ai/* | OK | Actions IA, feedback, insights dismissable |
| 5 | **Legal RAG** | /legal | OK | 5 onglets, chat juridique, prediction, articles |
| 6 | **SENTINEL** | /sentinel, /sentinel/conflicts | OK | Detection conflits, workflow resolution |
| 7 | **Knowledge Graph** | /graph | OK | Cytoscape, relations entites |
| 8 | **Inbox** | /inbox | OK | AI triage, validation/refus, suggestion dossier |
| 9 | **Emails** | /emails, /emails/[id] | OK | Liste, detail thread, sync Gmail/Outlook |
| 10 | **Documents** | /documents | OK | Cloud sync Drive/OneDrive, file browser |
| 11 | **Analytique** | /analytics | OK | Charts Recharts, KPIs, filtres temporels |
| 12 | **Recherche** | /search | OK | Barre de recherche, filtres |
| 13 | **Transcriptions** | /ai/transcription | OK | Upload audio |
| 14 | **Migration** | /migration | OK | Wizard 5 etapes, VeoCRM/CSV |
| 15 | **Admin** | /admin, /admin/settings, /admin/llm | OK | Gestion users/tenants, config LLM |
| 16 | **Parametres** | /admin/integrations | OK | 6 integrations configurables |
| 17 | **Timeline** | /timeline | OK | Evenements multi-sources |

### 3.2 Fonctionnalites en erreur

| # | Module | Page | Erreur | Severite |
|---|--------|------|--------|----------|
| 1 | **Contacts** | /contacts | API 500 | BLOQUANT |
| 2 | **Facturation** | /billing | "length" undefined | BLOQUANT |
| 3 | **Calendrier** | /calendar | "C is not iterable" | BLOQUANT |
| 4 | **Appels** | /calls | API 500 | BLOQUANT |

### 3.3 Donnees de test creees

- **Dossier** : DOS-2026-2178 "Contrat distribution - TechVendor SARL" (Droit commercial, Urgent)
- **Contacts** : Tentative de creation echouee (Bug #1)

---

## SECTION 4 — ROADMAP DE DEVELOPPEMENT PRIORISEE

### SPRINT 13 — CORRECTION BUGS CRITIQUES (Priorite MAXIMALE)

**Objectif** : Rendre les 4 pages cassees operationnelles

| Ticket | Titre | Fichiers | Effort |
|--------|-------|----------|--------|
| LXB-071 | Fix Contacts API 500 | `packages/db/models/contact.py`, `apps/api/services/contact_service.py` | 0.5j |
| LXB-072 | Fix Billing "length" undefined | `apps/web/app/dashboard/billing/TimesheetView.tsx`, `InvoiceList.tsx`, `ThirdPartyView.tsx` | 0.5j |
| LXB-073 | Fix Calendar "C is not iterable" | `apps/web/app/dashboard/calendar/page.tsx`, `apps/api/routers/calendar.py` | 1j |
| LXB-074 | Fix Calls API 500 — rewrite calls.py | `apps/api/routers/calls.py` | 1j |

### SPRINT 14 — STABILISATION & TESTS

| Ticket | Titre | Fichiers | Effort |
|--------|-------|----------|--------|
| LXB-075 | Gardes defensifs frontend (?.items \|\| []) | Tous les composants qui appellent apiFetch | 1j |
| LXB-076 | Refactor brain.py (2523 lignes → modules) | `apps/api/routers/brain.py` → split en 5+ sous-modules | 2j |
| LXB-077 | Supprimer placeholders dashboard | `apps/web/app/dashboard/page.tsx` | 0.5j |
| LXB-078 | Rate limit Redis (actuellement in-memory) | `apps/api/middleware/` | 0.5j |
| LXB-079 | Tests E2E frontend (Playwright) | Nouveau : `apps/web/tests/` | 3j |

### SPRINT 15 — FONCTIONNALITES MANQUANTES ESSENTIELLES

| Ticket | Titre | Fichiers | Effort |
|--------|-------|----------|--------|
| LXB-080 | Forgot password / reset password | Backend: nouveau router, Frontend: nouvelle page | 1j |
| LXB-081 | Onboarding tenant self-service | Backend + Frontend wizard | 2-3j |
| LXB-082 | MinIO upload/download fonctionnel | `apps/api/services/document_service.py` | 2j |
| LXB-083 | Notifications email (deadlines, actions IA) | Nouveau service + Celery tasks | 2j |
| LXB-084 | DPA e-Deposit tribunal connecte | `apps/api/routers/dpa.py` + webhook | 2j |

### SPRINT 16 — PRODUCTION-READY

| Ticket | Titre | Fichiers | Effort |
|--------|-------|----------|--------|
| LXB-085 | Backup/restore automatise (cron) | `apps/api/services/backup_service.py` | 1j |
| LXB-086 | Monitoring Grafana + alerting | Docker: Prometheus + Grafana | 2j |
| LXB-087 | Logs centralises (Loki/ELK) | Docker + middleware | 2j |
| LXB-088 | Peppol e-invoicing envoi reel | `apps/api/services/invoice_service.py` | 2j |
| LXB-089 | GDPR data export/delete (Art. 17) | Nouveau service | 2j |

### SPRINT 17 — DIFFERENTIATION COMMERCIALE

| Ticket | Titre | Fichiers | Effort |
|--------|-------|----------|--------|
| LXB-090 | Pricing/billing SaaS (plans, abonnements) | Frontend + Stripe integration | 5j |
| LXB-091 | BCE enrichment (Banque-Carrefour Entreprises) | `apps/api/services/sentinel/enrichment.py` | 2j |
| LXB-092 | i18n NL (neerlandais) | Frontend: next-intl | 5-10j |
| LXB-093 | Export PDF dossiers/factures | Nouveau service + WeasyPrint | 2j |
| LXB-094 | PWA / responsive mobile | Frontend responsive | 3j |

---

## SECTION 5 — PROMPT CLAUDE CODE MULTI-AGENTS

Voici le prompt optimise pour lancer Claude Code en mode autonome multi-agents :

```
Tu es un lead developer senior travaillant sur LexiBel, une plateforme SaaS
de gestion de cabinet d'avocats belge AI-native.

## CONTEXTE
- Stack: FastAPI 0.109+ / Next.js 14.2 / PostgreSQL 16 + RLS / Redis / Qdrant / Neo4j / MinIO
- 12 sprints completes, 420 tests, architecture multi-tenant RLS
- 4 BUGS CRITIQUES bloques en production (voir ci-dessous)
- CLAUDE.md contient les conventions du projet

## MISSION IMMEDIATE — SPRINT 13 : CORRIGER LES 4 BUGS CRITIQUES

Tu dois corriger les 4 bugs suivants. Pour chaque bug, AVANT de coder :
1. Lis le fichier source complet
2. Lis le test associe si existant
3. Comprends la cause racine
4. Corrige
5. Lance les tests: python -m pytest apps/api/tests/ -v --timeout=300 -x
6. Lance le lint: python -m ruff check apps/api/ packages/ apps/workers/

### BUG 1 — Contacts API 500
- Fichier: apps/api/routers/contacts.py + packages/db/models/contact.py
- Cause: Le modele Contact herite de TenantMixin (qui definit tenant_id)
  MAIS redefinit aussi tenant_id manuellement (lignes 30-34). Conflit SQLAlchemy.
- Fix: Supprimer la redefinition de tenant_id dans contact.py (garder celle du mixin).
  Verifier que d'autres modeles n'ont pas le meme probleme.

### BUG 2 — Facturation "Cannot read properties of undefined (reading 'length')"
- Fichier: apps/web/app/dashboard/billing/TimesheetView.tsx (ligne 77, 385)
- Cause: setEntries(timeData.items) peut recevoir undefined si l'API repond
  differemment. entries.length crash ensuite.
- Fix: Ajouter des gardes defensifs dans TOUS les composants billing :
  setEntries(timeData?.items ?? [])
  Appliquer aussi dans InvoiceList.tsx (ligne 64) et ThirdPartyView.tsx (lignes 73, 88)
- Bug secondaire dans InvoiceList.tsx : l'interface Invoice utilise `vat_cents`
  mais le backend retourne `vat_amount_cents` (schema billing.py ligne 117).
  Renommer dans le frontend pour matcher.

### BUG 3 — Calendrier "C is not iterable"
- Fichier: apps/web/app/dashboard/calendar/page.tsx + apps/api/routers/calendar.py
- Cause: 3 mismatches API/Frontend :
  1. Frontend attend CalendarEvent[] (tableau), backend retourne {events: [], total, page, per_page}
  2. Stats: frontend attend total_events/today_events/upcoming_week, backend retourne total/today/upcoming
  3. Events manquent les champs date, time, attendees
- Fix: Corriger le frontend pour unwrap res.events, corriger le backend pour
  renommer les stats et ajouter les champs manquants.

### BUG 4 — Appels API 500
- Fichier: apps/api/routers/calls.py
- Cause: Le router utilise 5 colonnes INEXISTANTES sur InteractionEvent :
  interaction_type (→ event_type), direction (→ metadata_["direction"]),
  duration_seconds (→ metadata_), transcript (→ metadata_), contact_id (→ metadata_)
- Reference: apps/api/routers/ringover.py utilise CORRECTEMENT le meme modele.
  Copier le pattern de ringover.py pour les queries.
- Fix: Reecrire get_calls() et get_call_stats() avec les bons noms de colonnes.
  Pour stats, calculer en Python (pas de func.avg() sur JSONB).

## REGLES
- Respecter CLAUDE.md (RLS, tenant_id, conventions)
- Zero erreurs ruff
- Tous les tests doivent passer
- Ne PAS creer de fichiers inutiles
- Committer chaque fix separement avec message descriptif
- Build frontend apres corrections: cd apps/web && pnpm build

## APRES LES FIXES
1. Lancer la suite de tests complete
2. Verifier le build frontend
3. Lister tout probleme residuel detecte
```

---

## SECTION 6 — SCORE FINAL

| Critere | Score | Commentaire |
|---------|-------|-------------|
| Architecture | 9/10 | Multi-tenant RLS, separation propre, design solide |
| Backend API | 8/10 | 33 routes actives mais 2 cassees (contacts, calls) |
| Frontend UI | 7/10 | Riche et bien designe mais 0 tests + 2 bugs rendering |
| Base de donnees | 9/10 | 38 modeles, RLS, append-only, migrations propres |
| Tests backend | 8/10 | 420+ tests mais pas de coverage % mesure |
| Tests frontend | 1/10 | Aucun test |
| DevOps / CI/CD | 8/10 | GitHub Actions complet, Docker, deploy auto |
| Pret a l'usage | 5/10 | 4 bugs critiques bloquent 4 pages essentielles |
| Documentation | 9/10 | 90+ fichiers markdown, CLAUDE.md, guides |
| **Score global** | **7.1/10** | Solide mais 4 bugs critiques a corriger en priorite |

---

*Rapport genere le 01/03/2026 — LexiBel v12 (Sprint 12 complet)*
