# SPRINT 13 — PROMPT CLAUDE CODE MULTI-AGENTS AUTONOME

## Comment utiliser ce prompt

Copie la commande ci-dessous dans ton terminal et lance-la.
Claude Code va operer en mode autonome avec des agents specialises en parallele.

---

## COMMANDE TERMINAL

```bash
claude --dangerously-skip-permissions -p "$(cat <<'PROMPT_EOF'

Tu es un LEAD DEVELOPER SENIOR specialise SaaS/full-stack. Tu travailles sur
LexiBel, plateforme de gestion de cabinet d'avocats belge AI-native.

Lis CLAUDE.md pour les conventions du projet.

## TA MISSION : SPRINT 13 — CORRIGER 4 BUGS CRITIQUES EN PRODUCTION

Tu vas travailler en MODE MULTI-AGENTS. Lance 4 agents EN PARALLELE, un par bug.
Chaque agent doit :
1. Lire le fichier source complet + le test associe
2. Comprendre la cause racine (documentee ci-dessous)
3. Coder le fix
4. Verifier que le code est coherent

Apres les 4 agents, toi (orchestrateur) tu :
5. Lances les tests : python -m pytest apps/api/tests/ -v --timeout=300 -x
6. Lances le lint : python -m ruff check apps/api/ packages/ apps/workers/
7. Lances le format : python -m ruff format apps/api/ packages/ apps/workers/
8. Build frontend : cd apps/web && pnpm build
9. Fixes tout ce qui casse
10. Commites chaque fix separement

---

## BUG 1 — CONTACTS API 500 + MIGRATION RUNNER CASSE (Agent Backend Infra)

### Probleme systemique : le migration runner ne fonctionne JAMAIS

Dans apps/api/main.py (lignes 83-95), le lifespan FastAPI appelle :
  command.upgrade(alembic_cfg, "head")
Mais packages/db/migrations/env.py (ligne 63) fait :
  asyncio.run(run_migrations_online())
Or on est DEJA dans un event loop FastAPI → RuntimeError attrapee silencieusement.
Les migrations ne s'appliquent JAMAIS au demarrage.

La migration 019 (ajout colonne metadata JSONB sur contacts) n'a jamais ete
appliquee → SQLAlchemy genere SELECT contacts.metadata → PostgreSQL leve
UndefinedColumn → 500.

### Fix requis (3 fichiers) :

**Fichier 1 : apps/api/main.py** — Remplacer le bloc lignes 86-95 par :
```python
    # Run Alembic migrations on startup
    try:
        import asyncio
        from alembic.config import Config
        from alembic import command

        alembic_cfg = Config("alembic.ini")
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, command.upgrade, alembic_cfg, "head")
        logger.info("Alembic migrations applied successfully")
    except Exception as e:
        logger.warning("Alembic migration skipped: %s", e)
```

**Fichier 2 : packages/db/migrations/env.py** — Remplacer les lignes 60-63 par :
```python
if context.is_offline_mode():
    run_migrations_offline()
else:
    try:
        loop = asyncio.get_running_loop()
        import nest_asyncio
        nest_asyncio.apply()
        asyncio.run(run_migrations_online())
    except RuntimeError:
        asyncio.run(run_migrations_online())
```

ATTENTION : nest_asyncio est une dependance optionnelle. La solution plus propre
est d'utiliser run_in_executor dans main.py (fichier 1), ce qui fait tourner
alembic dans un thread separe et evite le conflit event loop. Si tu choisis cette
approche, le env.py n'a PAS besoin de changer car il sera appele depuis un
nouveau thread sans event loop actif.

**Fichier 3 : packages/db/models/contact.py** — Optionnel : supprimer la
redefinition de tenant_id (lignes 30-34) car TenantMixin le fournit deja.
Verifier que les autres modeles suivent le meme pattern.

---

## BUG 2 — FACTURATION "length" UNDEFINED (Agent Frontend Billing)

### Cause racine
apps/web/app/dashboard/billing/TimesheetView.tsx ligne 76-78 :
  setEntries(timeData.items)   ← Si items est undefined, entries = undefined
  entries.length (ligne 385)   ← crash: Cannot read properties of undefined

Meme pattern dans InvoiceList.tsx et ThirdPartyView.tsx.

Bug secondaire : InvoiceList.tsx interface Invoice declare vat_cents mais le
backend (apps/api/schemas/billing.py) retourne vat_amount_cents.

### Fix requis (3 fichiers) :

**apps/web/app/dashboard/billing/TimesheetView.tsx** — Ligne 76-78, changer :
```typescript
setEntries(timeData?.items ?? []);
setCases(caseData?.items ?? []);
```
Et ligne 153, meme garde :
```typescript
setEntries(data?.items ?? []);
```

**apps/web/app/dashboard/billing/InvoiceList.tsx** — Ligne 64, changer :
```typescript
.then((data) => setInvoices(data?.items ?? []))
```
Et dans l'interface Invoice, renommer vat_cents → vat_amount_cents.
Mettre a jour toutes les references a inv.vat_cents → inv.vat_amount_cents.

**apps/web/app/dashboard/billing/ThirdPartyView.tsx** — Ligne 73, changer :
```typescript
.then((data) => setCases(data?.items ?? []))
```
Et ligne 88 :
```typescript
setEntries(entriesData?.items ?? []);
```

---

## BUG 3 — CALENDRIER "C is not iterable" (Agent Full-Stack Calendar)

### Cause racine : 3 mismatches API/Frontend

**Mismatch 1 (CRASH)** :
- Frontend (page.tsx ~ligne 200) : apiFetch<CalendarEvent[]>(...) attend un TABLEAU
- Backend (calendar.py lignes 67-86) : retourne {"events": [...], "total": N, ...}
- setEvents(res) stocke un OBJET → [...events] crash → "C is not iterable"

**Mismatch 2** :
- Frontend attend : { total_events, today_events, upcoming_week }
- Backend retourne : { total, today, upcoming }

**Mismatch 3** :
- Frontend attend : event.date, event.time, event.attendees[]
- Backend ne retourne que : start_time, end_time, location, provider

### Fix requis (2 fichiers) :

**apps/api/routers/calendar.py** :
1. Dans la serialisation events (lignes 67-86), ajouter les champs derives :
   "date": event.start_time.strftime("%Y-%m-%d") if event.start_time else None,
   "time": event.start_time.strftime("%H:%M") if event.start_time else None,
   "attendees": [],  (pas de table attendees, retourner liste vide)
2. Dans /stats (lignes 147-151), renommer les cles :
   "total" → "total_events"
   "today" → "today_events"
   "upcoming" → "upcoming_week"

**apps/web/app/dashboard/calendar/page.tsx** :
1. Changer le type de retour de l'appel events (~ligne 200) :
   const res = await apiFetch<{events: CalendarEvent[]}>(...);
   setEvents(res?.events ?? []);
2. Ajouter des gardes sur stats :
   setStats(res ?? { total_events: 0, today_events: 0, upcoming_week: 0 });

---

## BUG 4 — APPELS API 500 (Agent Backend Calls)

### Cause racine : 5 colonnes inexistantes dans calls.py

Le router apps/api/routers/calls.py utilise des colonnes qui N'EXISTENT PAS
sur le modele InteractionEvent :

  FAUX (calls.py)                    → CORRECT (modele reel)
  InteractionEvent.interaction_type  → InteractionEvent.event_type
  InteractionEvent.direction         → InteractionEvent.metadata_["direction"].astext
  event.duration_seconds             → (event.metadata_ or {}).get("duration_seconds")
  event.transcript                   → (event.metadata_ or {}).get("transcript")
  event.contact_id                   → (event.metadata_ or {}).get("contact_id")
  event.metadata                     → event.metadata_  (attention au underscore)

Le modele InteractionEvent (packages/db/models/interaction_event.py) a :
  id, tenant_id, case_id, source, event_type, title, body, occurred_at,
  metadata_, created_by, created_at

REFERENCE : apps/api/routers/ringover.py utilise CORRECTEMENT le meme modele.
Utilise le comme reference (lignes 190-210 pour les queries, 416-448 pour les stats).

### Fix requis (1 fichier) :

**apps/api/routers/calls.py** — Reecrire completement get_calls() et get_call_stats() :

Pour get_calls() :
- Filtrer : InteractionEvent.event_type == "CALL" (pas interaction_type)
- Direction : filtrer via metadata_ JSONB si direction param fourni
- Serialisation : extraire direction, duration_seconds, transcript, contact_id
  depuis event.metadata_ (dict JSONB), pas depuis des colonnes directes

Pour get_call_stats() :
- Impossible de faire func.avg() sur JSONB
- Charger les events en Python, puis calculer les stats manuellement
  (comme ringover.py lignes 416-448)

---

## REGLES STRICTES

1. Lis CLAUDE.md — toutes les conventions y sont
2. ZERO erreurs ruff (check + format)
3. TOUS les tests doivent passer (420+)
4. Le build frontend (pnpm build) doit passer
5. NE PAS creer de fichiers inutiles
6. NE PAS ajouter de dependances sans justification
7. Committer CHAQUE fix separement avec message descriptif en anglais :
   - "fix(contacts): repair Alembic migration runner — run_in_executor in lifespan"
   - "fix(billing): add defensive guards for API response shape"
   - "fix(calendar): align API response shape with frontend expectations"
   - "fix(calls): rewrite queries using correct InteractionEvent columns"
8. Apres tous les fixes, lancer la validation complete :
   python -m pytest apps/api/tests/ packages/db/tests/ -v --timeout=300
   python -m ruff check apps/api/ packages/ apps/workers/
   cd apps/web && pnpm build

PROMPT_EOF
)"
```

---

## VARIANTE : Mode interactif (si tu preferes controler etape par etape)

```bash
claude
```

Puis colle ce prompt dans la session interactive :

```
Lis le fichier AUDIT_DEV_ROADMAP.md et execute le Sprint 13 en multi-agents.
Lance 4 agents en parallele (un par bug). Respecte CLAUDE.md. Commite chaque fix.
```

---

## VARIANTE : Lancer UN SEUL bug a la fois

```bash
# Bug 1 — Migration runner
claude -p "Lis AUDIT_DEV_ROADMAP.md section BUG #1. Corrige le migration runner casse dans apps/api/main.py et packages/db/migrations/env.py. Lance les tests et commite."

# Bug 2 — Billing
claude -p "Lis AUDIT_DEV_ROADMAP.md section BUG #2. Ajoute les gardes defensifs ?.items ?? [] dans les 3 composants billing. Fix le mismatch vat_cents. Build frontend et commite."

# Bug 3 — Calendar
claude -p "Lis AUDIT_DEV_ROADMAP.md section BUG #3. Corrige les 3 mismatches API/Frontend dans calendar.py et calendar/page.tsx. Lance tests + build et commite."

# Bug 4 — Calls
claude -p "Lis AUDIT_DEV_ROADMAP.md section BUG #4. Reecris get_calls() et get_call_stats() dans calls.py en utilisant les bonnes colonnes de InteractionEvent. Utilise ringover.py comme reference. Lance tests et commite."
```
