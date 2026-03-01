# SPRINT 13 — COMMANDES WINDOWS POWERSHELL

## OPTION A — Commande unique PowerShell (copie-colle tel quel)

```powershell
claude --dangerously-skip-permissions -p "Tu es un LEAD DEVELOPER SENIOR specialise SaaS/full-stack. Tu travailles sur LexiBel, plateforme de gestion de cabinet d'avocats belge AI-native. Lis CLAUDE.md pour les conventions du projet. Lis AUDIT_DEV_ROADMAP.md pour le contexte complet des 4 bugs critiques. Execute le SPRINT 13 : corrige les 4 bugs critiques en mode multi-agents paralleles (un agent par bug). Apres les 4 fixes, lance les tests (python -m pytest apps/api/tests/ -v --timeout=300 -x), le lint (python -m ruff check apps/api/ packages/ apps/workers/), le format (python -m ruff format apps/api/ packages/ apps/workers/), et le build frontend (cd apps/web && pnpm build). Commite chaque fix separement. Voici le resume des 4 bugs : BUG 1 CONTACTS API 500 : Le migration runner dans apps/api/main.py (lignes 86-95) est casse car alembic env.py utilise asyncio.run() dans un event loop deja actif. Fix: utiliser await loop.run_in_executor(None, command.upgrade, alembic_cfg, head) dans main.py. BUG 2 BILLING length undefined : TimesheetView.tsx ligne 76-78 fait setEntries(timeData.items) sans garde defensif. Fix: setEntries(timeData?.items ?? []) dans TimesheetView.tsx, InvoiceList.tsx et ThirdPartyView.tsx. Plus renommer vat_cents en vat_amount_cents dans InvoiceList.tsx. BUG 3 CALENDAR C is not iterable : Frontend attend un tableau CalendarEvent[] mais backend retourne un objet {events: [], total, page}. Fix: unwrap res.events dans page.tsx, renommer stats keys dans calendar.py, ajouter champs date/time/attendees. BUG 4 CALLS API 500 : calls.py utilise 5 colonnes inexistantes sur InteractionEvent (interaction_type, direction, duration_seconds, transcript, contact_id). Fix: utiliser event_type et metadata_ JSONB comme dans ringover.py."
```

## OPTION B — Mode interactif (plus simple)

```powershell
claude
```

Puis colle ce texte dans la session :

```
Lis AUDIT_DEV_ROADMAP.md et SPRINT13_PROMPT.md. Execute le Sprint 13 en multi-agents paralleles. Lance 4 agents, un par bug. Commite chaque fix separement. Lance tests + lint + build a la fin.
```

## OPTION C — Bug par bug (un a la fois)

```powershell
# Bug 1 — Migration runner
claude -p "Lis AUDIT_DEV_ROADMAP.md section BUG 1. Corrige le migration runner casse dans apps/api/main.py (utilise run_in_executor) et packages/db/migrations/env.py. Lance les tests et commite."

# Bug 2 — Billing
claude -p "Lis AUDIT_DEV_ROADMAP.md section BUG 2. Ajoute les gardes defensifs dans TimesheetView.tsx InvoiceList.tsx ThirdPartyView.tsx. Fix le mismatch vat_cents vers vat_amount_cents. Build frontend et commite."

# Bug 3 — Calendar
claude -p "Lis AUDIT_DEV_ROADMAP.md section BUG 3. Corrige les 3 mismatches API/Frontend dans calendar.py et calendar/page.tsx. Lance tests plus build et commite."

# Bug 4 — Calls
claude -p "Lis AUDIT_DEV_ROADMAP.md section BUG 4. Reecris get_calls et get_call_stats dans calls.py en utilisant les bonnes colonnes de InteractionEvent. Utilise ringover.py comme reference. Lance tests et commite."
```
