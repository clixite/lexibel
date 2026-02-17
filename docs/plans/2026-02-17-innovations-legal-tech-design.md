# Design Document: 4 Innovations Legal-Tech LexiBel

**Date:** 2026-02-17
**Auteur:** PM + Claude Sonnet 4.5
**Statut:** Draft → Review → Approved
**Version:** 1.0

---

## Executive Summary

Ce document décrit l'architecture complète de **4 innovations majeures** pour LexiBel qui transformeront le cabinet d'avocats en une organisation augmentée par l'IA. Ces innovations exploitent l'ensemble des données disponibles (appels, emails, transcriptions, calendrier, documents) pour fournir des capacités inédites dans la legal-tech.

**Les 4 Innovations:**

1. **BRAIN** — Agent IA Proactif Multi-Dossiers (autonome 24/7)
2. **PROPHET** — Prédiction d'Issue de Dossier (ML-powered)
3. **SENTINEL** — Détection Temps Réel de Conflits d'Intérêts (graph-based)
4. **TIMELINE MAGIC** — Auto-Génération de Chronologie Juridique (NLP-powered)

**Impact attendu:**
- Réduction de 40% du temps administratif
- Augmentation de 25% de la productivité des avocats
- Élimination de 95% des risques de conflits d'intérêts non détectés
- Différenciation compétitive majeure sur le marché belge

---

## Table des Matières

1. [BRAIN — Agent IA Proactif](#1-brain--agent-ia-proactif)
2. [PROPHET — Prédiction d'Issue](#2-prophet--prédiction-dissue)
3. [SENTINEL — Détection Conflits](#3-sentinel--détection-conflits)
4. [TIMELINE MAGIC — Chronologie Auto](#4-timeline-magic--chronologie-auto)
5. [Architecture Globale](#5-architecture-globale)
6. [Stack Technique](#6-stack-technique)
7. [Séquençage d'Implémentation](#7-séquençage-dimplémentation)
8. [Métriques de Succès](#8-métriques-de-succès)

---

## 1. BRAIN — Agent IA Proactif

### 1.1 Vision

Un agent IA autonome qui surveille **tous les dossiers 24/7** et agit comme un associé junior ultra-vigilant. Contrairement aux chatbots passifs, BRAIN **prend des initiatives** pour aider les avocats.

### 1.2 Capacités Clés

**Surveillance Continue:**
- Scanne toutes les interactions (appels, emails, transcriptions) en temps réel
- Analyse tous les documents uploadés pour extraire les faits/dates/obligations
- Monitore les calendriers pour anticiper les deadlines

**Détection Proactive:**
- **Deadlines imminentes:** Alerte 7j, 3j, 1j avant + suggère actions
- **Contradictions factuelles:** Détecte incohérences entre différentes sources
- **Opportunités de négociation:** Identifie les moments favorables (sentiment positif)
- **Risques juridiques:** Signale les clauses dangereuses, prescriptions, etc.
- **Tâches oubliées:** Rappelle les actions promises lors d'appels/emails

**Actions Autonomes:**
- **Rédaction de brouillons:** Mise en demeure, lettre de rappel, conclusions simples
- **Préparation de documents:** Draft d'ordre du jour de réunion avec points clés
- **Recherche jurisprudentielle:** Trouve automatiquement les arrêts pertinents
- **Envoi de rappels:** Email/SMS aux clients pour documents manquants
- **Suggestions d'actions:** "Il serait opportun d'envoyer une mise en demeure aujourd'hui"

**Apprentissage Continu:**
- Apprend des décisions de l'avocat (accepter/rejeter suggestions)
- S'adapte au style de travail de chaque avocat
- Améliore ses prédictions au fil du temps

### 1.3 Architecture Technique

```
┌─────────────────────────────────────────────────────┐
│                    BRAIN CORE                       │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │   Watchers   │  │  Analyzers   │  │  Actors   │ │
│  │   (Inbox)    │→ │   (Rules)    │→ │ (Actions) │ │
│  └──────────────┘  └──────────────┘  └───────────┘ │
└─────────────────────────────────────────────────────┘
         ↓                   ↓                  ↓
    ┌─────────┐       ┌──────────┐      ┌────────────┐
    │ Events  │       │  Memory  │      │  Actions   │
    │ Stream  │       │  Vector  │      │   Queue    │
    │ (Redis) │       │   DB     │      │  (Celery)  │
    └─────────┘       └──────────┘      └────────────┘
```

**Composants:**

1. **Watchers (Surveillants):**
   - `CallWatcher`: Écoute les nouveaux appels + transcriptions
   - `EmailWatcher`: Monitore les nouveaux emails
   - `DocumentWatcher`: Détecte les nouveaux documents
   - `CalendarWatcher`: Surveille les événements à venir
   - `DeadlineWatcher`: Calcule les échéances en continu

2. **Analyzers (Analyseurs):**
   - `FactExtractor`: Extrait faits, dates, montants, parties
   - `SentimentAnalyzer`: Analyse le ton des communications
   - `RiskDetector`: Identifie les risques juridiques
   - `OpportunityFinder`: Détecte les opportunités (négociation, etc.)
   - `ContradictionChecker`: Compare les faits entre sources
   - `JurisprudenceLinker`: Trouve la jurisprudence applicable

3. **Actors (Acteurs):**
   - `DraftGenerator`: Génère des brouillons de documents
   - `ReminderSender`: Envoie des rappels automatiques
   - `SuggestionEngine`: Propose des actions aux avocats
   - `AutoResponder`: Répond automatiquement (emails simples)
   - `DocumentPreparer`: Prépare des documents complexes

4. **Memory (Mémoire):**
   - Vector DB (Qdrant/Chroma) pour RAG sur tous les dossiers
   - Graph DB (Neo4j) pour relations entre entités
   - Redis pour cache et état en temps réel

5. **Actions Queue:**
   - Celery pour tâches asynchrones
   - Prioritization: critique > urgent > normal
   - Retry logic avec backoff exponentiel

### 1.4 Règles de Décision

**Matrice de Priorité:**

| Type d'Action | Autonomie | Validation Requise |
|---------------|-----------|-------------------|
| Alerte deadline < 24h | Immédiate | Non (notification) |
| Draft document simple | Automatique | Oui (review avocat) |
| Envoi email client | Automatique | Oui (approbation) |
| Recherche jurisprudence | Immédiate | Non (info) |
| Détection contradiction | Immédiate | Non (alerte) |
| Suggestion stratégique | Automatique | Oui (décision avocat) |

**Seuils de Confiance:**
- Confiance > 90% → Action automatique + notification
- Confiance 70-90% → Suggestion avec explication
- Confiance < 70% → Log pour apprentissage uniquement

### 1.5 Interface Utilisateur

**Dashboard BRAIN:**
- **Feed d'activité:** Toutes les actions de BRAIN en temps réel
- **Suggestions pendantes:** Actions en attente de validation
- **Insights du jour:** Top 3 insights les plus importants
- **Statistiques:** Actions automatisées, temps économisé, suggestions acceptées

**Notifications:**
- Push notifications (web + mobile)
- Email digest quotidien (configurable)
- SMS pour urgences critiques (deadline < 24h)

**Contrôles:**
- Toggle ON/OFF par dossier
- Niveau d'autonomie réglable (conservateur → agressif)
- Whitelist/blacklist d'actions automatiques

### 1.6 Modèles de Données

**Nouveaux modèles DB:**

```python
# packages/db/models/brain_action.py
class BrainAction:
    id: UUID
    case_id: UUID
    action_type: str  # 'alert', 'draft', 'suggestion', 'auto_send'
    priority: str  # 'critical', 'urgent', 'normal'
    status: str  # 'pending', 'approved', 'rejected', 'executed'
    confidence_score: float  # 0.0-1.0
    trigger_source: str  # 'call', 'email', 'document', 'deadline'
    trigger_id: UUID
    action_data: dict  # JSON with action details
    generated_content: str  # Draft text, email body, etc.
    executed_at: datetime
    reviewed_by: UUID  # user_id who reviewed
    feedback: str  # User feedback for learning
    created_at: datetime

# packages/db/models/brain_insight.py
class BrainInsight:
    id: UUID
    case_id: UUID
    insight_type: str  # 'risk', 'opportunity', 'contradiction', 'deadline'
    severity: str  # 'low', 'medium', 'high', 'critical'
    title: str
    description: str
    evidence_ids: list[UUID]  # Links to calls/emails/docs
    suggested_actions: list[str]
    dismissed: bool
    created_at: datetime

# packages/db/models/brain_memory.py
class BrainMemory:
    id: UUID
    case_id: UUID
    memory_type: str  # 'fact', 'preference', 'pattern', 'learning'
    content: str
    embedding: list[float]  # Vector for similarity search
    source_ids: list[UUID]
    confidence: float
    created_at: datetime
```

### 1.7 APIs

**Endpoints:**

```
POST /api/v1/brain/actions                    — Crée une action BRAIN
GET  /api/v1/brain/actions?status=pending     — Liste actions en attente
PUT  /api/v1/brain/actions/{id}/approve       — Approuve une action
PUT  /api/v1/brain/actions/{id}/reject        — Rejette une action
GET  /api/v1/brain/insights?case_id={id}      — Insights pour un dossier
POST /api/v1/brain/insights/{id}/dismiss      — Dismiss un insight
GET  /api/v1/brain/feed?limit=50              — Feed d'activité temps réel
GET  /api/v1/brain/stats                      — Statistiques globales
POST /api/v1/brain/config                     — Configuration par dossier
```

### 1.8 Stack Technique BRAIN

- **Core:** Python 3.12 + FastAPI
- **Task Queue:** Celery + Redis
- **Vector DB:** Qdrant (embeddings OpenAI Ada-002)
- **LLM:** Claude 3.5 Sonnet (via API Anthropic)
- **NLP:** spaCy fr_core_news_lg + transformers
- **Monitoring:** Prometheus + Grafana
- **Logs:** Structured logging (JSON) → Elasticsearch

---

## 2. PROPHET — Prédiction d'Issue

### 2.1 Vision

Un système ML qui prédit l'issue probable d'un dossier, le montant potentiel, et la durée estimée. Aide à la prise de décision stratégique (négociation vs procès).

### 2.2 Capacités Clés

**Prédictions:**
- **Probabilité de succès:** 0-100% avec intervalle de confiance
- **Montant estimé:** Range (min-max) + médiane
- **Durée prévue:** Timeline en mois (date de clôture estimée)
- **Risques identifiés:** Liste des facteurs de risque avec poids

**Simulations:**
- Comparer 2-3 stratégies différentes (ex: procès vs négociation)
- Impact de chaque stratégie sur probabilité/montant/durée
- Recommandation basée sur critères (max gain, min risque, min temps)

**Facteurs Analysés:**
- Type de litige (divorce, immobilier, commercial, etc.)
- Juge assigné (si connu) → historique des décisions
- Partie adverse (historique si déjà rencontrée)
- Solidité des preuves (analyse des documents)
- Sentiment des communications (niveau de conflit)
- Jurisprudence applicable (précédents similaires)
- Contexte économique (pour dommages-intérêts)

### 2.3 Architecture Technique

```
┌──────────────────────────────────────────────────┐
│             PROPHET ML PIPELINE                  │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐ │
│  │  Feature   │→ │   Model    │→ │  Output    │ │
│  │ Extraction │  │ Inference  │  │ Generator  │ │
│  └────────────┘  └────────────┘  └────────────┘ │
└──────────────────────────────────────────────────┘
         ↓                ↓                ↓
    ┌─────────┐    ┌──────────┐    ┌──────────┐
    │ Feature │    │  Models  │    │  Cache   │
    │  Store  │    │ Registry │    │  (Redis) │
    └─────────┘    └──────────┘    └──────────┘
```

**Composants:**

1. **Feature Extraction:**
   - Extrait 50-100 features par dossier:
     - Textuelles: Nombre de mots dans documents, sentiment moyen, mots-clés juridiques
     - Numériques: Montant réclamé, durée depuis ouverture, nombre d'audiences
     - Catégorielles: Type de litige, juridiction, juge, avocat adverse
     - Temporelles: Jour de la semaine d'ouverture, saison, période judiciaire
     - Relationnelles: Historique avec partie adverse, historique du juge

2. **Models:**
   - **Modèle de classification:** Succès vs Échec (Random Forest + XGBoost)
   - **Modèle de régression:** Montant obtenu (Gradient Boosting + Neural Net)
   - **Modèle de durée:** Temps jusqu'à clôture (Survival Analysis + LSTM)
   - **Ensemble:** Combine les 3 modèles avec stacking

3. **Training Pipeline:**
   - Dataset: Tous les dossiers fermés (minimum 200 pour démarrer)
   - Features: Engineered + auto-learned (embeddings)
   - Cross-validation: 5-fold stratified
   - Hyperparameter tuning: Optuna
   - Re-training: Mensuel automatique avec nouveaux dossiers

4. **Explainability:**
   - SHAP values pour expliquer chaque prédiction
   - Feature importance globale et locale
   - Counterfactual explanations ("Si X changeait, alors Y")

### 2.4 Modèles ML

**Algorithmes utilisés:**

| Tâche | Algorithme Principal | Backup | Métriques |
|-------|---------------------|--------|-----------|
| Classification (succès) | XGBoost | Random Forest | AUC-ROC, F1-score |
| Régression (montant) | LightGBM | Neural Net | MAE, R² |
| Durée (temps) | Cox Survival | LSTM | C-index, Brier score |

**Pipeline:**
1. Preprocessing: Imputation, scaling, encoding
2. Feature selection: Recursive feature elimination
3. Training: Grid search + cross-validation
4. Evaluation: Hold-out test set (20%)
5. Deployment: MLflow pour versioning

### 2.5 Interface Utilisateur

**Page PROPHET par dossier:**

```
┌─────────────────────────────────────────────────┐
│  PROPHET — Prédiction Dossier 2026/042         │
├─────────────────────────────────────────────────┤
│  📊 PROBABILITÉ DE SUCCÈS                       │
│       73%  [65% - 81%]  ████████░░              │
│       Confiance: Élevée (95%)                   │
│                                                  │
│  💰 MONTANT ESTIMÉ                              │
│       Médiane: 12.500 €                         │
│       Range: 8.000 € - 18.000 €                 │
│                                                  │
│  ⏱️  DURÉE ESTIMÉE                               │
│       8 mois (Clôture: Oct 2026)                │
│       Range: 6-12 mois                          │
│                                                  │
│  ⚠️  FACTEURS DE RISQUE                         │
│       • Juge peu favorable (poids: 0.3)         │
│       • Preuves documentaires faibles (0.4)     │
│       • Partie adverse agressive (0.2)          │
│                                                  │
│  ✅ FACTEURS POSITIFS                           │
│       • Jurisprudence favorable (poids: 0.5)    │
│       • Témoignages solides (0.3)               │
│                                                  │
│  🎯 RECOMMANDATION                              │
│       Négociation à l'amiable recommandée       │
│       Économie estimée: 4 mois + 2.000 € frais │
│                                                  │
│  📈 SIMULATION STRATÉGIES                       │
│  ┌─────────────┬──────────┬─────────┬─────────┐│
│  │ Stratégie   │ Succès   │ Montant │ Durée   ││
│  ├─────────────┼──────────┼─────────┼─────────┤│
│  │ Procès      │ 73%      │ 12.5k € │ 8 mois  ││
│  │ Négociation │ 85%      │ 10k €   │ 4 mois  ││
│  │ Médiation   │ 90%      │ 9k €    │ 3 mois  ││
│  └─────────────┴──────────┴─────────┴─────────┘│
└─────────────────────────────────────────────────┘
```

### 2.6 Modèles de Données

```python
# packages/db/models/prophet_prediction.py
class ProphetPrediction:
    id: UUID
    case_id: UUID
    prediction_type: str  # 'outcome', 'amount', 'duration'
    predicted_value: float  # 0-1 for outcome, euros for amount, days for duration
    confidence_interval_low: float
    confidence_interval_high: float
    confidence_score: float  # 0-1
    model_version: str
    features_used: dict  # JSON with all features
    shap_values: dict  # SHAP explanation
    risk_factors: list[dict]  # [{"factor": "...", "weight": 0.3}]
    positive_factors: list[dict]
    created_at: datetime
    is_current: bool  # Most recent prediction for this case

# packages/db/models/prophet_simulation.py
class ProphetSimulation:
    id: UUID
    case_id: UUID
    strategy_name: str  # 'procès', 'négociation', 'médiation'
    success_probability: float
    estimated_amount_median: float
    estimated_amount_range_low: float
    estimated_amount_range_high: float
    estimated_duration_months: float
    estimated_costs: float
    recommendation_score: float  # 0-1 (higher = better)
    created_at: datetime
```

### 2.7 APIs

```
POST /api/v1/prophet/predict/{case_id}           — Génère prédiction
GET  /api/v1/prophet/predictions/{case_id}       — Récupère prédiction actuelle
POST /api/v1/prophet/simulate/{case_id}          — Simule stratégies
GET  /api/v1/prophet/simulations/{case_id}       — Récupère simulations
GET  /api/v1/prophet/explanations/{prediction_id} — SHAP explanations
POST /api/v1/prophet/retrain                     — Déclenche re-training (admin)
GET  /api/v1/prophet/model/metrics               — Métriques du modèle actuel
```

---

## 3. SENTINEL — Détection Conflits

### 3.1 Vision

Système de détection en temps réel des conflits d'intérêts basé sur un graph database. Analyse instantanée de TOUS les nouveaux contacts/dossiers avant acceptation.

### 3.2 Types de Conflits Détectés

**Conflits directs:**
- Nouveau client = adversaire d'un client actuel/passé
- Nouveau client = ancien client avec contentieux non résolu
- Administrateurs/actionnaires en commun entre parties opposées

**Conflits indirects:**
- Nouveau client = concurrent commercial d'un client actuel
- Société apparentée (filiale, maison-mère, groupe)
- Relations familiales entre parties (même nom de famille)
- Anciens employés devenus adversaires

**Conflits cachés:**
- Actionnariat croisé (A possède 10% de B, B possède 15% de C)
- Administrateurs communs non évidents
- Relations contractuelles existantes (fournisseur-client)
- Dossiers passés avec outcome défavorable pour partie similaire

### 3.3 Architecture Technique

```
┌──────────────────────────────────────────────────┐
│           SENTINEL GRAPH ENGINE                  │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────┐ │
│  │   Ingest    │→ │  Analyzer    │→ │ Alerts  │ │
│  │  (Events)   │  │  (Queries)   │  │ (Rules) │ │
│  └─────────────┘  └──────────────┘  └─────────┘ │
└──────────────────────────────────────────────────┘
         ↓                  ↓                ↓
    ┌─────────┐       ┌──────────┐    ┌──────────┐
    │  Neo4j  │       │  Redis   │    │  Action  │
    │  Graph  │       │  Cache   │    │  Queue   │
    └─────────┘       └──────────┘    └──────────┘
```

**Composants:**

1. **Graph Database (Neo4j):**
   - Nodes: Person, Company, Case, Lawyer
   - Relationships: REPRESENTS, OPPOSES, OWNS_SHARES_IN, IS_DIRECTOR_OF, IS_RELATED_TO, SUPPLIES_TO

2. **Ingest Pipeline:**
   - Écoute: Nouveaux contacts, nouveaux dossiers, nouveaux liens
   - Enrichissement: BCE (Belgian Company Registry), LinkedIn, Open Corporates
   - Graph update: Création de nodes + relationships en temps réel

3. **Analyzer:**
   - Cypher queries pour détecter patterns de conflits
   - Algorithmes de graphe: Shortest path, community detection, centrality
   - Scoring: Gravité du conflit (0-100)

4. **Alert System:**
   - Instant alerts pour conflits directs (gravité > 80)
   - Daily digest pour conflits indirects (gravité 50-80)
   - Génération automatique de mémo de conflit pour l'Ordre

### 3.4 Graph Schema

```cypher
// Nodes
(:Person {id, name, email, phone, dob, national_id})
(:Company {id, name, vat, bce_number, sector, size})
(:Lawyer {id, name, bar_number, firm})
(:Case {id, number, type, status, opened_at, closed_at})

// Relationships
(:Lawyer)-[:REPRESENTS {since, until, role}]->(:Person|Company)
(:Person|Company)-[:OPPOSES {in_case, role}]->(:Person|Company)
(:Person)-[:IS_DIRECTOR_OF {since, until, role}]->(:Company)
(:Person)-[:OWNS_SHARES_IN {percentage, since}]->(:Company)
(:Company)-[:SUBSIDIARY_OF {percentage}]->(:Company)
(:Person)-[:RELATED_TO {type: 'spouse'|'child'|'sibling'}]->(:Person)
(:Company)-[:SUPPLIES_TO {since, amount_yearly}]->(:Company)
(:Company)-[:COMPETES_WITH {sector}]->(:Company)
```

### 3.5 Queries de Détection

**Conflit direct (adversaire existant):**
```cypher
MATCH (new:Person {id: $new_person_id})
MATCH (lawyer:Lawyer {bar_number: $our_bar_number})
MATCH (lawyer)-[:REPRESENTS]->(client)-[:OPPOSES]-(new)
WHERE client <> new
RETURN client, new, type(OPPOSES) as conflict_type
```

**Conflit indirect (actionnariat):**
```cypher
MATCH (new:Company {id: $new_company_id})
MATCH (lawyer:Lawyer)-[:REPRESENTS]->(client:Company)
MATCH path = (new)-[:SUBSIDIARY_OF|OWNS_SHARES_IN*1..3]-(client)
WHERE new <> client
RETURN path, length(path) as degrees_separation
```

**Conflit caché (administrateur commun):**
```cypher
MATCH (new:Company {id: $new_company_id})
MATCH (lawyer:Lawyer)-[:REPRESENTS]->(client:Company)-[:OPPOSES]-(adversary:Company)
MATCH (person:Person)-[:IS_DIRECTOR_OF]->(new)
MATCH (person)-[:IS_DIRECTOR_OF]->(adversary)
RETURN person, new, adversary
```

### 3.6 Interface Utilisateur

**Alerte SENTINEL (popup):**
```
╔══════════════════════════════════════════════════╗
║  🚨 CONFLIT D'INTÉRÊTS DÉTECTÉ                   ║
╠══════════════════════════════════════════════════╣
║  Gravité: 🔴 ÉLEVÉE (87/100)                     ║
║                                                  ║
║  Nouveau Contact:                                ║
║    Jean Dupont (jdupont@example.com)            ║
║                                                  ║
║  Conflit avec:                                   ║
║    Marie Martin (client actif)                   ║
║    Dossier 2026/023 - Divorce                    ║
║                                                  ║
║  Type: ADVERSAIRE DIRECT                         ║
║    Jean Dupont = partie adverse dans            ║
║    dossier 2026/023 (depuis 2025-11-15)         ║
║                                                  ║
║  Actions:                                        ║
║    □ Refuser le dossier                          ║
║    □ Demander waiver au client existant         ║
║    □ Générer mémo de conflit (Ordre)            ║
║    □ Marquer comme faux positif                  ║
╚══════════════════════════════════════════════════╝
```

**Dashboard SENTINEL:**
- Graph visualization interactif des relations
- Timeline des conflits détectés
- Stats: Conflits évités, faux positifs, temps économisé

### 3.7 Modèles de Données

```python
# packages/db/models/sentinel_conflict.py
class SentinelConflict:
    id: UUID
    trigger_entity_id: UUID  # Contact ou Case qui a déclenché
    trigger_entity_type: str  # 'contact', 'case'
    conflict_type: str  # 'direct_adversary', 'indirect_ownership', 'director_overlap', etc.
    severity_score: int  # 0-100
    description: str
    conflicting_entity_id: UUID
    conflicting_entity_type: str
    conflicting_case_id: UUID | None
    graph_path: list[dict]  # Le chemin dans le graph
    auto_resolved: bool
    resolution: str | None  # 'refused', 'waiver_obtained', 'false_positive'
    resolved_by: UUID | None
    resolved_at: datetime | None
    created_at: datetime

# packages/db/models/sentinel_entity.py
class SentinelEntity:
    id: UUID
    entity_type: str  # 'person', 'company'
    lexibel_id: UUID  # Link to Contact or Case
    neo4j_id: str  # Node ID in Neo4j
    enrichment_data: dict  # BCE data, LinkedIn, etc.
    last_synced_at: datetime
    created_at: datetime
```

### 3.8 APIs

```
POST /api/v1/sentinel/check-conflict           — Check avant création contact/dossier
GET  /api/v1/sentinel/conflicts?status=active  — Liste conflits actifs
PUT  /api/v1/sentinel/conflicts/{id}/resolve   — Résoudre un conflit
GET  /api/v1/sentinel/graph/{entity_id}        — Visualisation graph
POST /api/v1/sentinel/entities/enrich          — Enrichir avec BCE/LinkedIn
GET  /api/v1/sentinel/stats                    — Statistiques
POST /api/v1/sentinel/memo/{conflict_id}       — Générer mémo Ordre
```

---

## 4. TIMELINE MAGIC — Chronologie Auto

### 4.1 Vision

Système NLP qui extrait automatiquement TOUS les événements factuels de toutes les sources (emails, appels, documents) et génère une chronologie juridique structurée prête à annexer aux conclusions.

### 4.2 Capacités Clés

**Extraction Automatique:**
- Scanne tous les emails du dossier
- Parse toutes les transcriptions d'appels
- Analyse tous les documents PDF/Word
- Extrait les événements avec: date, heure, acteurs, action, lieu

**Normalisation:**
- Déduplique les événements (même fait mentionné dans 2 sources)
- Normalise les dates (formats variés → ISO 8601)
- Identifie les acteurs (matching avec contacts)
- Catégorise les événements (réunion, paiement, signature, etc.)

**Structuration Juridique:**
- Tri chronologique strict
- Groupement par période (phases du dossier)
- Highlighting des événements clés (signatures, délais, prescriptions)
- Cross-référencement avec pièces

**Génération Document:**
- Export Word (.docx) formaté avocat
- Export PDF avec table des matières
- Timeline interactive HTML pour le dossier
- Édition collaborative avec suggestions IA

### 4.3 Architecture Technique

```
┌──────────────────────────────────────────────────┐
│          TIMELINE MAGIC PIPELINE                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │ Extractor│→ │Normalizer│→ │   Generator  │   │
│  │  (NLP)   │  │ (Rules)  │  │  (Template)  │   │
│  └──────────┘  └──────────┘  └──────────────┘   │
└──────────────────────────────────────────────────┘
       ↓              ↓                 ↓
  ┌─────────┐   ┌──────────┐     ┌──────────┐
  │  NLP    │   │ Timeline │     │ Document │
  │ Models  │   │   DB     │     │ Generator│
  └─────────┘   └──────────┘     └──────────┘
```

**Composants:**

1. **Extractor (NLP):**
   - spaCy NER (Named Entity Recognition) pour personnes, organisations, lieux, dates
   - Dependency parsing pour identifier l'action (verbe principal)
   - Temporal expression extraction (SUTime, HeidelTime)
   - Custom rules pour vocabulaire juridique belge

2. **Normalizer:**
   - Date parsing: dateutil + custom rules (ex: "lundi dernier", "le 3")
   - Entity matching: Fuzzy matching avec contacts existants (fuzzywuzzy)
   - Deduplication: Embeddings similarity (cosine > 0.9 = duplicate)
   - Categorization: ML classifier (15 catégories: réunion, paiement, signature, etc.)

3. **Generator:**
   - Template engine: Jinja2
   - Word generation: python-docx
   - PDF generation: WeasyPrint
   - Interactive timeline: vis.js

### 4.4 Extraction NLP

**Pipeline spaCy:**
```python
nlp = spacy.load("fr_core_news_lg")
nlp.add_pipe("temporal_extractor")  # Custom component
nlp.add_pipe("legal_entities")  # Belgian legal vocabulary

doc = nlp(text)
events = []
for sent in doc.sents:
    date = extract_date(sent)  # SUTime
    actors = [ent for ent in sent.ents if ent.label_ in ["PER", "ORG"]]
    action = get_main_verb(sent)  # Dependency parsing
    location = [ent for ent in sent.ents if ent.label_ == "LOC"]

    if date and action:
        events.append({
            "date": date,
            "actors": actors,
            "action": action,
            "location": location[0] if location else None,
            "source_text": sent.text
        })
```

**Catégories d'événements:**
- Réunion / Rendez-vous
- Appel téléphonique
- Email / Correspondance
- Signature de document
- Paiement / Transaction
- Audience / Comparution
- Dépôt de conclusions / Acte
- Expertise / Constat
- Notification / Signification
- Délai / Échéance
- Incident / Dommage
- Décision / Jugement
- Accord / Règlement
- Autre

### 4.5 Interface Utilisateur

**Page TIMELINE MAGIC:**

```
┌─────────────────────────────────────────────────┐
│  TIMELINE MAGIC — Dossier 2026/042             │
├─────────────────────────────────────────────────┤
│  📊 STATISTIQUES                                │
│     127 événements extraits                     │
│     23 sources analysées (18 emails, 5 appels)  │
│     14 déduplications                           │
│     Période: 2024-03-15 → 2026-02-10           │
│                                                  │
│  🔄 STATUT                                      │
│     ✅ Extraction complète                       │
│     ⏳ Review en cours (23 événements pendants) │
│                                                  │
│  📅 TIMELINE INTERACTIVE                        │
│  [────•────────•────•──────────•──────•─────]   │
│   2024     2025      2026                       │
│                                                  │
│  📋 ÉVÉNEMENTS (tri chronologique)              │
│  ┌───────────────────────────────────────────┐ │
│  │ 2024-03-15 10:30                          │ │
│  │ 📧 Email de M. Dupont à Me. Lefebvre     │ │
│  │    "Demande de rendez-vous urgent"        │ │
│  │    Source: email_thread_42                │ │
│  │    [✓ Validé]  [Edit]  [Supprimer]       │ │
│  ├───────────────────────────────────────────┤ │
│  │ 2024-03-18 14:00                          │ │
│  │ 🤝 Réunion - Cabinet Lefebvre            │ │
│  │    Participants: Dupont, Lefebvre         │ │
│  │    Sujet: Litige immobilier Uccle         │ │
│  │    Source: transcription_call_89          │ │
│  │    [⏳ À valider]  [Edit]  [IA Suggest]   │ │
│  └───────────────────────────────────────────┘ │
│                                                  │
│  🔧 ACTIONS                                     │
│  [📥 Importer événements manuels]              │
│  [🔄 Re-scanner toutes les sources]            │
│  [📄 Générer document Word]                    │
│  [📊 Export Excel]                              │
│  [🖨️  Générer PDF pour conclusions]            │
└─────────────────────────────────────────────────┘
```

**Document généré (Word):**

```
CHRONOLOGIE DES FAITS
Dossier 2026/042 - Dupont c/ Immobel SA

══════════════════════════════════════════════

PHASE 1: PRÉCONTENTIEUX (Mars 2024 - Juin 2024)

Le 15 mars 2024
    Email de M. Jean DUPONT à Me. Sophie LEFEBVRE demandant un
    rendez-vous urgent concernant un litige immobilier.
    [Pièce 1: Email du 15/03/2024]

Le 18 mars 2024 à 14h00
    Réunion au cabinet entre M. DUPONT et Me. LEFEBVRE. Discussion
    sur les dommages constatés dans l'appartement sis avenue Louise
    142, 1050 Bruxelles.
    [Pièce 2: Note de réunion]

Le 22 mars 2024
    Réception du rapport d'expertise de M. Pierre DUBOIS (expert
    agréé) constatant des infiltrations d'eau dans les murs porteurs.
    Montant estimé des dégâts: 45.000 EUR.
    [Pièce 3: Rapport d'expertise du 22/03/2024]

...

PHASE 2: MISE EN DEMEURE (Juillet 2024)

Le 5 juillet 2024
    Envoi par courrier recommandé de mise en demeure à la SA IMMOBEL
    (siège social: Rue de la Loi 15, 1000 Bruxelles) demandant la
    réparation des dommages sous 30 jours.
    [Pièce 8: Mise en demeure du 05/07/2024]

...
```

### 4.6 Modèles de Données

```python
# packages/db/models/timeline_event.py
class TimelineEvent:
    id: UUID
    case_id: UUID
    event_date: date
    event_time: time | None
    category: str  # 'meeting', 'call', 'email', 'signature', etc.
    title: str
    description: str
    actors: list[str]  # List of person/company names
    location: str | None
    source_type: str  # 'email', 'call', 'document', 'manual'
    source_id: UUID | None
    source_excerpt: str  # Original text
    confidence_score: float  # 0-1
    is_validated: bool
    is_key_event: bool  # Highlighted in timeline
    evidence_links: list[UUID]  # Links to documents
    created_by: str  # 'ai' or user_id
    validated_by: UUID | None
    created_at: datetime
    updated_at: datetime

# packages/db/models/timeline_document.py
class TimelineDocument:
    id: UUID
    case_id: UUID
    timeline_id: UUID  # References a specific timeline version
    format: str  # 'docx', 'pdf', 'html'
    file_path: str
    generated_at: datetime
    generated_by: UUID
    events_count: int
    date_range_start: date
    date_range_end: date
```

### 4.7 APIs

```
POST /api/v1/timeline/extract/{case_id}        — Lance extraction complète
GET  /api/v1/timeline/events/{case_id}         — Liste événements
POST /api/v1/timeline/events                   — Crée événement manuel
PUT  /api/v1/timeline/events/{id}              — Édite événement
PUT  /api/v1/timeline/events/{id}/validate     — Valide événement
DELETE /api/v1/timeline/events/{id}            — Supprime événement
POST /api/v1/timeline/generate/{case_id}       — Génère document Word/PDF
GET  /api/v1/timeline/documents/{case_id}      — Liste documents générés
GET  /api/v1/timeline/stats/{case_id}          — Statistiques extraction
```

---

## 5. Architecture Globale

### 5.1 Vue d'Ensemble

```
┌────────────────────────────────────────────────────────────────┐
│                    LEXIBEL FRONTEND (Next.js)                  │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│   │  BRAIN   │  │ PROPHET  │  │ SENTINEL │  │ TIMELINE │     │
│   │   UI     │  │    UI    │  │    UI    │  │    UI    │     │
│   └──────────┘  └──────────┘  └──────────┘  └──────────┘     │
└────────────────────────────────────────────────────────────────┘
                              ↓ (API Gateway)
┌────────────────────────────────────────────────────────────────┐
│                   LEXIBEL API (FastAPI)                        │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│   │  BRAIN   │  │ PROPHET  │  │ SENTINEL │  │ TIMELINE │     │
│   │  Router  │  │  Router  │  │  Router  │  │  Router  │     │
│   └──────────┘  └──────────┘  └──────────┘  └──────────┘     │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────┐
│                      SERVICES LAYER                            │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│   │  BRAIN   │  │ PROPHET  │  │ SENTINEL │  │ TIMELINE │     │
│   │ Service  │  │ Service  │  │ Service  │  │ Service  │     │
│   └──────────┘  └──────────┘  └──────────┘  └──────────┘     │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────┐
│                      DATA LAYER                                │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│   │PostgreSQL│  │  Neo4j   │  │  Qdrant  │  │  Redis   │     │
│   │   (DB)   │  │ (Graph)  │  │ (Vector) │  │ (Cache)  │     │
│   └──────────┘  └──────────┘  └──────────┘  └──────────┘     │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────┐
│                   EXTERNAL SERVICES                            │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│   │ Anthropic│  │  OpenAI  │  │   BCE    │  │ LinkedIn │     │
│   │  Claude  │  │   API    │  │   API    │  │   API    │     │
│   └──────────┘  └──────────┘  └──────────┘  └──────────┘     │
└────────────────────────────────────────────────────────────────┘
```

### 5.2 Data Flow

**Exemple: Nouvel appel → Actions BRAIN**

```
1. Ringover webhook → POST /api/v1/webhooks/ringover
2. Create CallRecord in PostgreSQL
3. Event published to Redis stream: "new_call"
4. BRAIN CallWatcher receives event
5. BRAIN triggers transcription (Whisper API)
6. Transcription → BRAIN FactExtractor
7. Extract facts, dates, obligations
8. BRAIN RiskDetector analyzes facts
9. If risk detected → Create BrainInsight
10. If deadline mentioned → Create BrainAction (reminder)
11. Frontend polls /api/v1/brain/feed → displays alert
12. Lawyer approves action → Execute (send email/SMS)
```

### 5.3 Interactions Entre Modules

**BRAIN ↔ PROPHET:**
- BRAIN utilise PROPHET pour prioriser les actions (focus sur dossiers à haut risque)
- PROPHET utilise les insights BRAIN comme features additionnelles

**BRAIN ↔ SENTINEL:**
- BRAIN déclenche SENTINEL check lors de détection de nouveau contact dans appel/email
- SENTINEL alerte BRAIN en cas de conflit → BRAIN génère action "refuser dossier"

**BRAIN ↔ TIMELINE:**
- BRAIN envoie tous les événements détectés à TIMELINE pour auto-ajout
- TIMELINE notifie BRAIN des événements clés pour monitoring

**PROPHET ↔ TIMELINE:**
- PROPHET utilise la densité d'événements TIMELINE comme feature (activité du dossier)

**SENTINEL ↔ TIMELINE:**
- SENTINEL enrichit son graph avec les relations découvertes dans TIMELINE

### 5.4 Scaling & Performance

**Horizontal Scaling:**
- API: Multiple instances derrière load balancer (Traefik)
- Workers: Celery avec auto-scaling (Kubernetes HPA)
- Databases: Read replicas pour PostgreSQL, Neo4j cluster

**Caching Strategy:**
- Redis L1: API responses (TTL 5min)
- Redis L2: ML predictions (TTL 1h)
- CDN: Static assets, documents générés

**Queue Priority:**
- Critical: Conflits d'intérêts (SENTINEL)
- High: Deadlines < 24h (BRAIN)
- Normal: Prédictions (PROPHET), Timelines (TIMELINE MAGIC)
- Low: Background enrichment, re-training

---

## 6. Stack Technique

### 6.1 Backend

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| API Framework | FastAPI | 0.109+ | REST API + WebSockets |
| Language | Python | 3.12+ | Core backend |
| ORM | SQLAlchemy | 2.0+ | PostgreSQL interactions |
| Task Queue | Celery | 5.3+ | Async jobs |
| Message Broker | Redis | 7.2+ | Celery + caching |
| Database | PostgreSQL | 16+ | Primary data store |
| Graph DB | Neo4j | 5.15+ | SENTINEL graph |
| Vector DB | Qdrant | 1.7+ | BRAIN embeddings |
| ML Framework | scikit-learn | 1.4+ | PROPHET models |
| Deep Learning | PyTorch | 2.1+ | Neural nets |
| NLP | spaCy | 3.7+ | TIMELINE extraction |
| LLM | Claude 3.5 | API | BRAIN generation |
| Monitoring | Prometheus | 2.48+ | Metrics |
| Logging | ELK Stack | 8.11+ | Centralized logs |
| Container | Docker | 24+ | Containerization |
| Orchestration | Docker Compose | 2.23+ | Local dev |

### 6.2 Frontend

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Framework | Next.js | 14+ | React framework |
| Language | TypeScript | 5.3+ | Type safety |
| UI Library | shadcn/ui | latest | Components |
| Charts | Recharts | 2.10+ | Visualizations |
| Timeline | vis.js | 9.1+ | Interactive timeline |
| Graph | cytoscape.js | 3.28+ | SENTINEL graph viz |
| State | Zustand | 4.4+ | State management |
| Forms | React Hook Form | 7.49+ | Form handling |
| API Client | TanStack Query | 5.17+ | Data fetching |

### 6.3 Infrastructure

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Hosting | OVH Cloud / AWS | Production servers |
| CI/CD | GitHub Actions | Automated deployments |
| SSL | Let's Encrypt | HTTPS certificates |
| Load Balancer | Traefik | Reverse proxy |
| Backup | pg_dump + rclone | Daily backups to S3 |
| Monitoring | Grafana + Sentry | Dashboards + error tracking |

### 6.4 ML/AI Tools

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Embeddings | OpenAI Ada-002 | Text embeddings |
| LLM | Claude 3.5 Sonnet | Generation + reasoning |
| Speech-to-Text | Whisper API | Call transcriptions |
| NER | spaCy fr_core_news_lg | Named entity recognition |
| Date Parsing | SUTime | Temporal expressions |
| ML Tracking | MLflow | Model versioning |
| Feature Store | Feast | PROPHET features |
| AutoML | Optuna | Hyperparameter tuning |

---

## 7. Séquençage d'Implémentation

### 7.1 Phase 1: Fondations (Semaines 1-2)

**Objectif:** Infrastructure de base pour les 4 modules

**Livrables:**
- Setup Neo4j pour SENTINEL
- Setup Qdrant pour BRAIN
- Modèles de données (20 tables)
- Migrations Alembic
- CI/CD pipeline
- Monitoring de base

**Agents:**
- Agent Infra (Neo4j, Qdrant, monitoring)
- Agent DB (modèles, migrations)

### 7.2 Phase 2: SENTINEL (Semaines 3-4)

**Objectif:** Détection de conflits opérationnelle

**Livrables:**
- Graph ingest pipeline
- Cypher queries de détection
- API SENTINEL complète
- UI: Alertes + dashboard
- Enrichissement BCE automatique

**Agents:**
- Agent SENTINEL Backend
- Agent SENTINEL Frontend
- Agent Enrichment (BCE API)

### 7.3 Phase 3: TIMELINE MAGIC (Semaines 5-6)

**Objectif:** Auto-génération de chronologies

**Livrables:**
- NLP extraction pipeline
- Normalisation + déduplication
- Génération Word/PDF
- UI: Timeline interactive
- Édition collaborative

**Agents:**
- Agent NLP (spaCy, extraction)
- Agent Timeline Backend
- Agent Timeline Frontend
- Agent Document Generator

### 7.4 Phase 4: BRAIN Core (Semaines 7-9)

**Objectif:** Agent proactif de base

**Livrables:**
- Watchers (Call, Email, Document, Calendar)
- Analyzers (Fact, Sentiment, Risk, Opportunity)
- Actions Queue (Celery)
- UI: Feed + dashboard
- 5 types d'actions automatisées

**Agents:**
- Agent BRAIN Watchers
- Agent BRAIN Analyzers
- Agent BRAIN Actors
- Agent BRAIN Frontend

### 7.5 Phase 5: BRAIN Advanced (Semaines 10-11)

**Objectif:** Génération de contenu + apprentissage

**Livrables:**
- Draft generation (Claude)
- Jurisprudence search
- Memory system (vector DB)
- Learning from feedback
- 10 types d'actions totales

**Agents:**
- Agent BRAIN Generation
- Agent BRAIN Memory
- Agent BRAIN Learning

### 7.6 Phase 6: PROPHET (Semaines 12-14)

**Objectif:** Prédiction d'issue avec ML

**Livrables:**
- Feature engineering pipeline
- Training des 3 modèles (Classification, Régression, Durée)
- MLflow setup + versioning
- API PROPHET complète
- UI: Prédictions + simulations
- SHAP explanations

**Agents:**
- Agent PROPHET ML (feature engineering)
- Agent PROPHET Training
- Agent PROPHET Backend
- Agent PROPHET Frontend

### 7.7 Phase 7: Intégration & Polish (Semaines 15-16)

**Objectif:** Tout fonctionne ensemble + UX parfaite

**Livrables:**
- Intégrations BRAIN ↔ PROPHET ↔ SENTINEL ↔ TIMELINE
- Optimisations de performance
- Tests d'intégration complets
- Documentation utilisateur
- Onboarding interactif
- Video tutorials

**Agents:**
- Agent Integration Tests
- Agent Performance Optimization
- Agent Documentation
- Agent UX Polish

### 7.8 Phase 8: Beta & Feedback (Semaines 17-18)

**Objectif:** Déploiement beta + itération

**Livrables:**
- Déploiement sur serveur de staging
- Beta avec 3-5 avocats pilotes
- Collecte de feedback
- Itérations rapides
- Production readiness

**Agents:**
- Agent Deploy
- Agent Feedback Analysis
- Agent Iteration

---

## 8. Métriques de Succès

### 8.1 BRAIN

**Adoption:**
- 90% des avocats utilisent BRAIN quotidiennement (après 1 mois)
- 50+ actions automatisées par semaine par avocat

**Efficacité:**
- 70% des suggestions acceptées
- 2-3h économisées par avocat par jour
- 95% des deadlines détectées sans erreur

**Qualité:**
- < 5% faux positifs sur détection de risques
- Confiance moyenne > 85%
- Temps de réponse < 2s pour génération de suggestion

### 8.2 PROPHET

**Précision:**
- Classification (succès): AUC-ROC > 0.80
- Régression (montant): R² > 0.70, MAE < 2000€
- Durée: C-index > 0.75

**Adoption:**
- 60% des dossiers ont au moins 1 prédiction
- 40% des avocats consultent PROPHET avant décision stratégique

**Impact:**
- 20% d'amélioration sur taux de règlement amiable (vs historique)

### 8.3 SENTINEL

**Détection:**
- 100% des conflits directs détectés
- 95% des conflits indirects détectés
- < 10% faux positifs

**Vitesse:**
- < 500ms pour check complet
- Temps réel sur création contact/dossier

**Impact:**
- 0 conflits non détectés en production (après 3 mois)
- Réduction de 80% du temps de vérification manuelle

### 8.4 TIMELINE MAGIC

**Extraction:**
- 85% des événements extraits automatiquement
- < 15% événements nécessitant édition manuelle
- 90% de précision sur dates/acteurs

**Adoption:**
- 50% des dossiers complexes utilisent TIMELINE MAGIC
- 10+ chronologies générées par semaine

**Efficacité:**
- 80% de réduction du temps de création (10h → 2h)
- 95% satisfaction avocat sur qualité du document

### 8.5 Globales

**Performance:**
- 99.9% uptime
- < 200ms latence p95 API
- < 5s pour génération de contenu IA

**Sécurité:**
- 0 data breach
- 100% conformité RGPD
- Logs d'audit complets

**ROI:**
- Break-even à 6 mois
- 3x retour sur investissement à 12 mois
- 40% réduction coûts opérationnels cabinet

---

## 9. Risques & Mitigations

### 9.1 Risques Techniques

| Risque | Impact | Probabilité | Mitigation |
|--------|--------|------------|-----------|
| Performance LLM (latence) | Élevé | Moyenne | Cache agressif, fallback à modèles plus rapides |
| Coût API IA (Claude, OpenAI) | Élevé | Élevée | Rate limiting, quotas par tenant, modèles locaux pour tâches simples |
| Qualité prédictions PROPHET | Élevé | Moyenne | Dataset > 500 dossiers, validation rigoureuse, disclaimers |
| Graph DB scaling (Neo4j) | Moyen | Faible | Sharding, read replicas, cache Redis |
| NLP extraction errors | Moyen | Moyenne | Human-in-the-loop validation, apprentissage continu |

### 9.2 Risques Métier

| Risque | Impact | Probabilité | Mitigation |
|--------|--------|------------|-----------|
| Résistance au changement avocats | Élevé | Élevée | Onboarding progressif, quick wins, formation |
| Confiance dans IA faible | Élevé | Moyenne | Explainability (SHAP), validation humaine systématique |
| Responsabilité juridique | Critique | Faible | Disclaimers clairs, assurance, "outil d'aide à la décision" |
| Données insuffisantes (ML) | Élevé | Moyenne | Seed avec données anonymisées, partenariats cabinets |

### 9.3 Risques Légaux

| Risque | Impact | Probabilité | Mitigation |
|--------|--------|------------|-----------|
| RGPD violation | Critique | Faible | Privacy by design, DPO, audits réguliers |
| Secret professionnel | Critique | Faible | Encryption E2E, hébergement UE, no data export |
| Déontologie Ordre des Avocats | Élevé | Faible | Consultation Ordre, conformité règlement |

---

## 10. Conclusion

Ce design document présente **4 innovations majeures** qui positionnent LexiBel comme le **leader incontesté de la legal-tech en Belgique**. L'implémentation complète nécessite:

- **Durée:** 18 semaines (4,5 mois)
- **Équipe:** 1 PM + 7-10 agents spécialisés en parallèle
- **Budget:** ~50k€ (infra + API IA + testing)

**ROI attendu:**
- Break-even: 6 mois
- 3x ROI: 12 mois
- Différenciation compétitive: Immédiate

**Prochaines étapes:**
1. Validation de ce design par les stakeholders
2. Création du plan d'implémentation détaillé (via writing-plans skill)
3. Setup de l'infra (Phase 1)
4. Lancement des agents de développement en parallèle

---

**Signatures:**

PM: _______________  Date: 2026-02-17
Claude Sonnet 4.5: ✓  Date: 2026-02-17
