# 🚀 LexiBel - Quick Start Guide

**Dernière mise à jour**: 2026-02-17
**Version**: Post-consolidation end-to-end

---

## ⚡ Démarrage Rapide (15 minutes)

### 1. Prérequis

- ✅ Docker Desktop installé et démarré
- ✅ Node.js 18+ installé
- ✅ Python 3.11+ installé
- ✅ Git installé

### 2. Clone & Setup (2 min)

```bash
cd F:/LexiBel  # Déjà cloné
```

### 3. Configuration Environnement (3 min)

```bash
# Copier les variables d'environnement
cp .env.example .env

# Éditer .env et configurer au minimum:
# - POSTGRES_PASSWORD
# - MINIO_PASSWORD
# - SECRET_KEY (générer avec: openssl rand -hex 64)
# - OAUTH_ENCRYPTION_KEY (générer avec: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
```

### 4. Lancer les Services (5 min)

```bash
# Démarrer tous les services
docker compose up -d

# Attendre que PostgreSQL soit prêt (environ 10 secondes)
sleep 10

# Lancer les migrations
bash run_migrations.sh
```

### 5. Seed les Données de Démo (3 min)

```bash
# Insérer les données de démo
docker exec -it lexibel-api-1 python -m apps.api.scripts.seed_demo_data
```

### 6. Accéder à l'Application (2 min)

```bash
# Frontend
open http://localhost:3000

# Backend API
open http://localhost:8000/docs

# Login
Email: nicolas@clixite.be
Password: LexiBel2026!
```

---

## 🎯 Vérification du Fonctionnement

### Test 1: API Health

```bash
curl http://localhost:8000/api/v1/admin/health
# Devrait retourner: {"status": "healthy", ...}
```

### Test 2: Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"nicolas@clixite.be","password":"LexiBel2026!"}'
# Devrait retourner un JWT token
```

### Test 3: Liste des Dossiers

```bash
# Remplacer YOUR_JWT_TOKEN par le token obtenu ci-dessus
curl http://localhost:8000/api/v1/cases \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
# Devrait retourner 5 dossiers
```

### Test 4: Frontend

1. Ouvrir http://localhost:3000
2. Login avec `nicolas@clixite.be` / `LexiBel2026!`
3. Vérifier que le dashboard affiche:
   - 5 dossiers
   - 10 contacts
   - 10 prestations
   - 2 factures
   - 5 inbox items

---

## 📊 Fonctionnalités Disponibles

### ✅ Core Business
- **Dossiers**: CRUD complet, timeline, documents, conflits
- **Contacts**: CRUD, recherche, validation BCE/téléphone
- **Facturation**: Time tracking, approval, invoices Peppol
- **Documents**: Upload/download, GED
- **Timeline**: Events de toutes sources
- **Inbox**: Validation workflow

### ✅ Intégrations (Backend Prêt)
- **Google OAuth**: Gmail + Google Calendar
- **Microsoft OAuth**: Outlook + Microsoft Calendar
- **Ringover**: Appels téléphoniques
- **Plaud.ai**: Transcriptions AI
- **OpenAI**: GPT-4, Whisper, Embeddings

### ✅ AI Features (Backend Prêt)
- **Legal RAG**: Recherche juridique sémantique
- **AI Hub**: Génération, résumé, analyse de documents
- **GraphRAG**: Détection de conflits avancée
- **Agents**: Due diligence, emotional radar
- **Transcriptions**: Audio vers texte avec insights

### ⚠️ À Configurer
- **OAuth**: Configurer les clés Google/Microsoft (voir docs/INTEGRATIONS_SETUP.md)
- **API Keys**: Configurer Ringover, Plaud.ai, OpenAI dans .env

---

## 🔧 Commandes Utiles

### Développement

```bash
# Voir les logs
docker compose logs -f api
docker compose logs -f web

# Redémarrer un service
docker compose restart api

# Reconstruire après changement de code
docker compose up -d --build api
```

### Base de Données

```bash
# Accéder à PostgreSQL
docker exec -it lexibel-postgres-1 psql -U lexibel -d lexibel

# Lister les tables
\dt

# Voir les données d'une table
SELECT * FROM cases LIMIT 5;

# Nouvelle migration
cd packages/db
alembic revision -m "description"
alembic upgrade head
```

### Tests

```bash
# Backend tests
cd /f/LexiBel
python -m pytest apps/api/tests/ -v

# Frontend build
cd apps/web
npm run build

# Linting
ruff check apps/api --fix
ruff format apps/api
```

---

## 🐛 Troubleshooting

### Problème: "Connection refused" API

```bash
# Vérifier que les services tournent
docker compose ps

# Redémarrer les services
docker compose restart
```

### Problème: Migrations échouent

```bash
# Reset la base de données (ATTENTION: perte de données)
docker compose down -v
docker compose up -d postgres
sleep 10
bash run_migrations.sh
```

### Problème: Frontend "Erreur de chargement"

```bash
# Vérifier que l'API tourne
curl http://localhost:8000/api/v1/admin/health

# Vérifier les variables d'environnement frontend
cat apps/web/.env.local
# Devrait contenir: NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

### Problème: OAuth ne fonctionne pas

1. Vérifier que OAUTH_ENCRYPTION_KEY est défini dans .env
2. Configurer les credentials Google/Microsoft (voir docs/INTEGRATIONS_SETUP.md)
3. Vérifier les redirect URIs dans les consoles OAuth

---

## 📚 Documentation Complète

- **Architecture**: `docs/02_LexiBel_Architecture.docx`
- **Backend Guide**: `docs/03_LexiBel_Backend_Guide.docx`
- **Frontend Guide**: `docs/04_LexiBel_Frontend_Guide.docx`
- **Intégrations**: `docs/INTEGRATIONS_SETUP.md`
- **Audit Complet**: `PM_AUDIT_RESULTS.md`
- **Plan d'Action**: `NEXT_STEPS.md`
- **Rapport de Session**: `SESSION_REPORT_2026-02-17.md`

---

## 🎉 Prochaines Étapes

1. **Configurer OAuth** (optionnel):
   - Google: docs/INTEGRATIONS_SETUP.md#google-oauth
   - Microsoft: docs/INTEGRATIONS_SETUP.md#microsoft-oauth

2. **Tester toutes les pages**:
   - Dashboard, Cases, Contacts, Timeline
   - Billing, Inbox, Emails, Calls
   - AI Hub, Legal Search, Graph

3. **Personnaliser**:
   - Créer votre tenant
   - Ajouter vos utilisateurs
   - Importer vos données

---

**Besoin d'aide?**
- Documentation: `/docs`
- Issues: https://github.com/clixite/lexibel/issues
- Email: support@lexibel.be

**Bon développement!** 🚀
