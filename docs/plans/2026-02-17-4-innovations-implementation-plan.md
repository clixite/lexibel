# 4 Innovations Legal-Tech Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans OR superpowers:subagent-driven-development to implement this plan phase-by-phase.

**Goal:** Implement 4 groundbreaking legal-tech innovations (BRAIN, PROPHET, SENTINEL, TIMELINE MAGIC) that transform LexiBel into the most advanced legal practice management platform in Belgium.

**Architecture:** Microservices-oriented with shared data layer. FastAPI backend, Next.js frontend, Neo4j graph DB, Qdrant vector DB, PostgreSQL relational DB, Redis cache/queue, Celery workers. AI-powered with Claude 3.5, embeddings, and ML models.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Celery, Redis, PostgreSQL 16, Neo4j 5.15, Qdrant 1.7, spaCy, scikit-learn, PyTorch, Next.js 14, TypeScript, shadcn/ui

**Timeline:** 18 weeks (4.5 months) across 8 phases

**Design Document:** See `docs/plans/2026-02-17-innovations-legal-tech-design.md` for complete architecture

---

## Project Structure

This master plan is divided into **8 phases**. Each phase has its own detailed sub-plan that will be created just-in-time for execution.

**Execution Strategy:**
- Phase-by-phase execution
- Multiple parallel agents per phase
- Each phase has 5-10 agents working concurrently
- Review checkpoints after each phase
- TDD throughout (test first, implement, commit)

---

## Phase 1: Foundations (Weeks 1-2)

**Objective:** Set up infrastructure and data models for all 4 innovations

**Sub-Plan:** `docs/plans/phase-1-foundations.md` (to be created)

### Overview

**Infrastructure:**
- Setup Neo4j cluster for SENTINEL
- Setup Qdrant instance for BRAIN
- Configure Celery + Redis for async tasks
- Setup monitoring (Prometheus + Grafana)
- Configure logging (ELK stack)

**Data Models:**
- 20 new PostgreSQL tables
- Alembic migrations
- Neo4j graph schema
- Qdrant collections

**Files to Create:**
```
packages/db/models/brain_action.py
packages/db/models/brain_insight.py
packages/db/models/brain_memory.py
packages/db/models/prophet_prediction.py
packages/db/models/prophet_simulation.py
packages/db/models/sentinel_conflict.py
packages/db/models/sentinel_entity.py
packages/db/models/timeline_event.py
packages/db/models/timeline_document.py
packages/db/migrations/versions/011_create_brain_tables.py
packages/db/migrations/versions/012_create_prophet_tables.py
packages/db/migrations/versions/013_create_sentinel_tables.py
packages/db/migrations/versions/014_create_timeline_tables.py
infra/neo4j/docker-compose.yml
infra/qdrant/docker-compose.yml
infra/monitoring/prometheus.yml
infra/monitoring/grafana-dashboards/
```

**Agents:**
1. Agent Neo4j Setup
2. Agent Qdrant Setup
3. Agent Monitoring Setup
4. Agent DB Models (Brain)
5. Agent DB Models (Prophet)
6. Agent DB Models (Sentinel)
7. Agent DB Models (Timeline)
8. Agent Migrations
9. Agent CI/CD Pipeline
10. Agent Documentation

**Tests:**
- Database connection tests
- Migration rollback tests
- Model validation tests
- Infra health checks

**Success Criteria:**
- All databases running and accessible
- All 20 tables created successfully
- Monitoring dashboards operational
- CI/CD pipeline green

---

## Phase 2: SENTINEL — Conflict Detection (Weeks 3-4)

**Objective:** Build complete conflict of interest detection system

**Sub-Plan:** `docs/plans/phase-2-sentinel.md` (to be created)

### Overview

**Components:**
- Graph ingest pipeline (PostgreSQL → Neo4j sync)
- Cypher queries for conflict detection (8 patterns)
- Enrichment service (BCE API integration)
- Alert system (real-time + digest)
- Frontend UI (graph viz + alerts dashboard)

**Files to Create:**
```
apps/api/services/sentinel/
apps/api/services/sentinel/__init__.py
apps/api/services/sentinel/graph_sync.py
apps/api/services/sentinel/conflict_detector.py
apps/api/services/sentinel/enrichment.py
apps/api/services/sentinel/alerter.py
apps/api/routers/sentinel.py
apps/api/tests/test_sentinel.py
apps/web/app/dashboard/sentinel/
apps/web/app/dashboard/sentinel/page.tsx
apps/web/app/dashboard/sentinel/conflicts/[id]/page.tsx
apps/web/components/sentinel/ConflictAlert.tsx
apps/web/components/sentinel/GraphVisualization.tsx
```

**Agents:**
1. Agent Sentinel Graph Sync
2. Agent Sentinel Conflict Detector
3. Agent Sentinel Enrichment (BCE)
4. Agent Sentinel Alerter
5. Agent Sentinel Backend API
6. Agent Sentinel Frontend UI
7. Agent Sentinel Tests
8. Agent Sentinel Documentation

**Key Cypher Queries:**

```cypher
// Direct adversary conflict
MATCH (new:Person {id: $new_person_id})
MATCH (lawyer:Lawyer {bar_number: $our_bar_number})
MATCH (lawyer)-[:REPRESENTS]->(client)-[:OPPOSES]-(new)
WHERE client <> new
RETURN client, new, type(OPPOSES) as conflict_type

// Indirect ownership conflict
MATCH (new:Company {id: $new_company_id})
MATCH (lawyer:Lawyer)-[:REPRESENTS]->(client:Company)
MATCH path = (new)-[:SUBSIDIARY_OF|OWNS_SHARES_IN*1..3]-(client)
WHERE new <> client
RETURN path, length(path) as degrees_separation

// Director overlap conflict
MATCH (new:Company {id: $new_company_id})
MATCH (lawyer:Lawyer)-[:REPRESENTS]->(client:Company)-[:OPPOSES]-(adversary:Company)
MATCH (person:Person)-[:IS_DIRECTOR_OF]->(new)
MATCH (person)-[:IS_DIRECTOR_OF]->(adversary)
RETURN person, new, adversary
```

**Tests:**
- Unit tests: Each Cypher query with fixtures
- Integration tests: Full conflict detection flow
- API tests: All endpoints (check, resolve, list)
- UI tests: Graph visualization, alerts

**Success Criteria:**
- < 500ms for conflict check
- 100% direct conflicts detected in test suite
- 95% indirect conflicts detected
- < 10% false positives
- BCE enrichment working for Belgian companies

---

## Phase 3: TIMELINE MAGIC — Auto-Chronology (Weeks 5-6)

**Objective:** Build NLP-powered automatic timeline generation

**Sub-Plan:** `docs/plans/phase-3-timeline-magic.md` (to be created)

### Overview

**Components:**
- NLP extraction pipeline (spaCy + custom models)
- Normalization & deduplication engine
- Document generator (Word/PDF)
- Interactive timeline UI (vis.js)
- Collaborative editing

**Files to Create:**
```
apps/api/services/timeline/
apps/api/services/timeline/__init__.py
apps/api/services/timeline/extractor.py
apps/api/services/timeline/normalizer.py
apps/api/services/timeline/deduplicator.py
apps/api/services/timeline/document_generator.py
apps/api/services/timeline/nlp_models.py
apps/api/routers/timeline.py
apps/api/tests/test_timeline.py
apps/web/app/dashboard/timeline/
apps/web/app/dashboard/timeline/[caseId]/page.tsx
apps/web/components/timeline/InteractiveTimeline.tsx
apps/web/components/timeline/EventCard.tsx
apps/web/components/timeline/DocumentExport.tsx
```

**NLP Pipeline:**

```python
# apps/api/services/timeline/extractor.py
import spacy
from spacy.tokens import Doc

nlp = spacy.load("fr_core_news_lg")

def extract_events(text: str, source_type: str, source_id: str) -> list[dict]:
    """Extract temporal events from text."""
    doc = nlp(text)
    events = []

    for sent in doc.sents:
        # Extract date
        dates = [ent for ent in sent.ents if ent.label_ == "DATE"]
        if not dates:
            continue

        # Extract actors (PER, ORG)
        actors = [ent.text for ent in sent.ents if ent.label_ in ["PER", "ORG"]]

        # Extract main verb (action)
        action = get_main_verb(sent)

        # Extract location
        location = [ent.text for ent in sent.ents if ent.label_ == "LOC"]

        events.append({
            "date": normalize_date(dates[0].text),
            "actors": actors,
            "action": action,
            "location": location[0] if location else None,
            "source_text": sent.text,
            "source_type": source_type,
            "source_id": source_id,
            "confidence": calculate_confidence(sent)
        })

    return events
```

**Agents:**
1. Agent Timeline NLP Extractor
2. Agent Timeline Normalizer
3. Agent Timeline Deduplicator
4. Agent Timeline Document Generator
5. Agent Timeline Backend API
6. Agent Timeline Frontend UI
7. Agent Timeline Tests
8. Agent Timeline Documentation

**Tests:**
- NLP extraction accuracy tests (precision/recall)
- Date normalization tests (various formats)
- Deduplication tests (fuzzy matching)
- Document generation tests (Word/PDF)
- UI integration tests

**Success Criteria:**
- 85% event extraction accuracy
- 90% date parsing accuracy
- < 15% events need manual editing
- Word/PDF generation works flawlessly
- Interactive timeline loads < 2s for 500 events

---

## Phase 4: BRAIN Core (Weeks 7-9)

**Objective:** Build autonomous AI agent with watchers, analyzers, and basic actions

**Sub-Plan:** `docs/plans/phase-4-brain-core.md` (to be created)

### Overview

**Components:**
- Event stream (Redis Streams)
- Watchers (Call, Email, Document, Calendar, Deadline)
- Analyzers (Fact, Sentiment, Risk, Opportunity, Contradiction)
- Actions Queue (Celery)
- Basic actors (Reminder, Alert, Suggestion)
- Dashboard UI

**Files to Create:**
```
apps/api/services/brain/
apps/api/services/brain/__init__.py
apps/api/services/brain/event_stream.py
apps/api/services/brain/watchers/
apps/api/services/brain/watchers/call_watcher.py
apps/api/services/brain/watchers/email_watcher.py
apps/api/services/brain/watchers/document_watcher.py
apps/api/services/brain/watchers/calendar_watcher.py
apps/api/services/brain/watchers/deadline_watcher.py
apps/api/services/brain/analyzers/
apps/api/services/brain/analyzers/fact_extractor.py
apps/api/services/brain/analyzers/sentiment_analyzer.py
apps/api/services/brain/analyzers/risk_detector.py
apps/api/services/brain/analyzers/opportunity_finder.py
apps/api/services/brain/analyzers/contradiction_checker.py
apps/api/services/brain/actors/
apps/api/services/brain/actors/reminder_sender.py
apps/api/services/brain/actors/alert_generator.py
apps/api/services/brain/actors/suggestion_engine.py
apps/api/routers/brain.py
apps/api/tests/test_brain.py
apps/web/app/dashboard/brain/
apps/web/app/dashboard/brain/page.tsx
apps/web/app/dashboard/brain/feed/page.tsx
apps/web/components/brain/ActionCard.tsx
apps/web/components/brain/InsightCard.tsx
apps/web/components/brain/BrainFeed.tsx
```

**Architecture:**

```
Event Stream (Redis) → Watchers → Analyzers → Actions Queue (Celery) → Actors
                                                      ↓
                                            BrainAction (DB)
                                            BrainInsight (DB)
```

**Agents:**
1. Agent Brain Event Stream
2. Agent Brain Watchers (5 watchers)
3. Agent Brain Analyzers (5 analyzers)
4. Agent Brain Actors (3 actors)
5. Agent Brain Actions Queue
6. Agent Brain Backend API
7. Agent Brain Frontend UI
8. Agent Brain Tests
9. Agent Brain Documentation

**Tests:**
- Watcher tests (event detection)
- Analyzer tests (fact extraction, sentiment, risk)
- Actor tests (reminder sending, alert generation)
- Integration tests (end-to-end flow)
- Performance tests (latency < 2s)

**Success Criteria:**
- All 5 watchers operational
- All 5 analyzers working
- 3 basic actors functional
- < 2s latency for action generation
- 90% uptime for event stream

---

## Phase 5: BRAIN Advanced (Weeks 10-11)

**Objective:** Add content generation, jurisprudence search, and learning capabilities

**Sub-Plan:** `docs/plans/phase-5-brain-advanced.md` (to be created)

### Overview

**Components:**
- Draft generator (Claude 3.5 integration)
- Jurisprudence search (vector DB + RAG)
- Memory system (Qdrant)
- Learning engine (feedback loop)
- Advanced actors (AutoResponder, DocumentPreparer)

**Files to Create:**
```
apps/api/services/brain/actors/draft_generator.py
apps/api/services/brain/actors/jurisprudence_searcher.py
apps/api/services/brain/actors/auto_responder.py
apps/api/services/brain/actors/document_preparer.py
apps/api/services/brain/memory/
apps/api/services/brain/memory/vector_store.py
apps/api/services/brain/memory/rag_engine.py
apps/api/services/brain/learning/
apps/api/services/brain/learning/feedback_collector.py
apps/api/services/brain/learning/model_updater.py
apps/api/tests/test_brain_advanced.py
```

**Draft Generation Example:**

```python
# apps/api/services/brain/actors/draft_generator.py
from anthropic import Anthropic

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

async def generate_draft(action: BrainAction, context: dict) -> str:
    """Generate draft document using Claude."""

    # Prepare prompt
    prompt = f"""
    Tu es un avocat belge expérimenté. Rédige un {action.action_data['document_type']}.

    Contexte du dossier:
    {context['case_summary']}

    Faits récents:
    {context['recent_events']}

    Instructions:
    {action.action_data['instructions']}

    Format: Formel, juridique belge, français.
    """

    # Call Claude
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    draft = response.content[0].text

    # Store for review
    action.generated_content = draft
    action.status = "pending_review"
    await db.commit()

    return draft
```

**Agents:**
1. Agent Brain Draft Generator
2. Agent Brain Jurisprudence Searcher
3. Agent Brain Memory System
4. Agent Brain Learning Engine
5. Agent Brain Advanced Actors (2)
6. Agent Brain Tests Advanced
7. Agent Brain Documentation Update

**Tests:**
- Draft generation quality tests
- Jurisprudence search relevance tests
- Memory retrieval accuracy tests
- Learning feedback loop tests
- End-to-end advanced action tests

**Success Criteria:**
- 80% draft quality (human review)
- 90% jurisprudence relevance (human rating)
- < 3s for draft generation
- Learning improves suggestions by 20% after 100 feedbacks

---

## Phase 6: PROPHET — Outcome Prediction (Weeks 12-14)

**Objective:** Build ML-powered case outcome prediction system

**Sub-Plan:** `docs/plans/phase-6-prophet.md` (to be created)

### Overview

**Components:**
- Feature engineering pipeline
- Training pipeline (3 models: Classification, Regression, Survival)
- MLflow setup for model versioning
- Inference API
- SHAP explanations
- Simulation engine
- Frontend UI

**Files to Create:**
```
apps/api/services/prophet/
apps/api/services/prophet/__init__.py
apps/api/services/prophet/feature_engineering.py
apps/api/services/prophet/training/
apps/api/services/prophet/training/classification_model.py
apps/api/services/prophet/training/regression_model.py
apps/api/services/prophet/training/survival_model.py
apps/api/services/prophet/training/ensemble.py
apps/api/services/prophet/inference.py
apps/api/services/prophet/explanations.py
apps/api/services/prophet/simulation.py
apps/api/routers/prophet.py
apps/api/tests/test_prophet.py
apps/api/scripts/train_prophet_models.py
apps/web/app/dashboard/prophet/
apps/web/app/dashboard/prophet/[caseId]/page.tsx
apps/web/components/prophet/PredictionCard.tsx
apps/web/components/prophet/SimulationTable.tsx
apps/web/components/prophet/ShapExplanation.tsx
```

**Feature Engineering:**

```python
# apps/api/services/prophet/feature_engineering.py
def engineer_features(case: Case) -> pd.DataFrame:
    """Extract 50-100 features from case."""

    features = {}

    # Basic features
    features['case_type'] = case.type
    features['opened_duration_days'] = (datetime.now() - case.opened_at).days
    features['amount_claimed'] = case.metadata.get('amount_claimed', 0)

    # Document features
    features['doc_count'] = len(case.documents)
    features['doc_total_pages'] = sum(d.page_count for d in case.documents)
    features['has_expert_report'] = any('expert' in d.title.lower() for d in case.documents)

    # Communication features
    features['email_count'] = len(case.email_threads)
    features['call_count'] = len(case.call_records)
    features['avg_sentiment'] = np.mean([c.metadata.get('sentiment_score', 0) for c in case.call_records])

    # Timeline features
    features['event_count'] = len(case.timeline_events)
    features['key_event_count'] = sum(1 for e in case.timeline_events if e.is_key_event)

    # Adversary features
    features['adversary_type'] = case.adversary_type  # 'person', 'company'
    features['adversary_has_lawyer'] = case.adversary_has_representation

    # Judge features (if known)
    if case.judge_id:
        judge_history = get_judge_history(case.judge_id)
        features['judge_avg_ruling_time_days'] = judge_history['avg_days']
        features['judge_plaintiff_win_rate'] = judge_history['plaintiff_wins'] / judge_history['total']

    return pd.DataFrame([features])
```

**ML Models:**

```python
# apps/api/services/prophet/training/classification_model.py
from xgboost import XGBClassifier
from sklearn.model_selection import cross_val_score

def train_outcome_classifier(X_train, y_train):
    """Train XGBoost for success/failure prediction."""

    model = XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42
    )

    # Cross-validation
    scores = cross_val_score(model, X_train, y_train, cv=5, scoring='roc_auc')
    print(f"Cross-val AUC: {scores.mean():.3f} (+/- {scores.std():.3f})")

    # Train final model
    model.fit(X_train, y_train)

    # Log to MLflow
    mlflow.log_params(model.get_params())
    mlflow.log_metric("cv_auc", scores.mean())
    mlflow.sklearn.log_model(model, "outcome_classifier")

    return model
```

**Agents:**
1. Agent Prophet Feature Engineering
2. Agent Prophet Classification Model
3. Agent Prophet Regression Model
4. Agent Prophet Survival Model
5. Agent Prophet Ensemble
6. Agent Prophet Inference API
7. Agent Prophet SHAP Explanations
8. Agent Prophet Simulation Engine
9. Agent Prophet Frontend UI
10. Agent Prophet Tests
11. Agent Prophet Documentation

**Tests:**
- Feature engineering tests (50+ features extracted)
- Model accuracy tests (AUC > 0.80, R² > 0.70)
- SHAP explanation tests (top features make sense)
- Simulation tests (3 strategies compared)
- API latency tests (< 2s inference)

**Success Criteria:**
- Classification AUC-ROC > 0.80
- Regression R² > 0.70, MAE < 2000€
- Survival C-index > 0.75
- SHAP explanations human-validated
- < 2s for prediction + explanation

---

## Phase 7: Integration & Polish (Weeks 15-16)

**Objective:** Integrate all 4 innovations, optimize performance, perfect UX

**Sub-Plan:** `docs/plans/phase-7-integration.md` (to be created)

### Overview

**Integrations:**
- BRAIN ↔ PROPHET: BRAIN uses predictions for prioritization
- BRAIN ↔ SENTINEL: BRAIN triggers conflict checks
- BRAIN ↔ TIMELINE: BRAIN feeds events to TIMELINE
- PROPHET ↔ TIMELINE: PROPHET uses timeline density as feature
- SENTINEL ↔ TIMELINE: SENTINEL enriches graph from timeline

**Performance Optimizations:**
- Redis caching strategy
- Database query optimization
- Async/await optimization
- Celery task prioritization
- Frontend code splitting

**UX Polish:**
- Consistent design system
- Loading states everywhere
- Error handling & retry UX
- Onboarding flow
- Help tooltips & guided tours

**Files to Create:**
```
apps/api/services/integrations/
apps/api/services/integrations/brain_prophet.py
apps/api/services/integrations/brain_sentinel.py
apps/api/services/integrations/brain_timeline.py
apps/api/services/integrations/prophet_timeline.py
apps/api/services/integrations/sentinel_timeline.py
apps/api/tests/test_integrations_full.py
apps/web/components/common/OnboardingTour.tsx
apps/web/components/common/ErrorBoundary.tsx
apps/web/components/common/LoadingStates.tsx
docs/user-guide/
docs/user-guide/brain-guide.md
docs/user-guide/prophet-guide.md
docs/user-guide/sentinel-guide.md
docs/user-guide/timeline-guide.md
```

**Integration Example:**

```python
# apps/api/services/integrations/brain_prophet.py
async def prioritize_brain_actions_with_prophet(case_id: UUID) -> list[BrainAction]:
    """Use PROPHET predictions to prioritize BRAIN actions."""

    # Get pending actions for case
    actions = await get_pending_actions(case_id)

    # Get PROPHET prediction
    prediction = await prophet_service.predict(case_id)

    # Reprioritize based on risk
    for action in actions:
        if prediction.success_probability < 0.5:  # High risk case
            if action.action_type in ['deadline_reminder', 'risk_alert']:
                action.priority = 'critical'  # Escalate
        else:  # Low risk case
            if action.action_type in ['suggestion', 'opportunity']:
                action.priority = 'normal'  # Deprioritize

    # Sort by priority
    actions.sort(key=lambda a: {'critical': 0, 'urgent': 1, 'normal': 2}[a.priority])

    return actions
```

**Agents:**
1. Agent Integrations (5 integration pairs)
2. Agent Performance Optimization
3. Agent Caching Strategy
4. Agent UX Polish
5. Agent Onboarding Flow
6. Agent User Documentation
7. Agent Integration Tests
8. Agent Load Testing

**Tests:**
- Integration tests (all 5 pairs)
- Load tests (1000 concurrent users)
- Performance tests (all APIs < 200ms p95)
- UX tests (onboarding completion rate)
- Accessibility tests (WCAG 2.1 AA)

**Success Criteria:**
- All 5 integrations working seamlessly
- API p95 latency < 200ms
- Frontend loads < 2s
- Onboarding completion rate > 80%
- WCAG 2.1 AA compliant

---

## Phase 8: Beta & Feedback (Weeks 17-18)

**Objective:** Deploy to staging, beta test with pilot users, iterate based on feedback

**Sub-Plan:** `docs/plans/phase-8-beta.md` (to be created)

### Overview

**Deployment:**
- Setup staging environment (identical to prod)
- Deploy all 4 innovations
- Configure monitoring & alerting
- Setup backup & disaster recovery

**Beta Testing:**
- Recruit 5-7 lawyer pilot users
- Daily check-ins for first week
- Weekly feedback sessions
- Bug tracking & prioritization
- Rapid iteration on feedback

**Production Readiness:**
- Security audit
- Performance audit
- GDPR compliance review
- Documentation completion
- Training materials

**Files to Create:**
```
infra/staging/
infra/staging/docker-compose.yml
infra/staging/nginx.conf
infra/prod/
infra/prod/docker-compose.yml
infra/prod/nginx.conf
infra/prod/backup.sh
infra/monitoring/alerts.yml
docs/deployment/
docs/deployment/staging-setup.md
docs/deployment/prod-setup.md
docs/deployment/backup-restore.md
docs/security/
docs/security/security-audit.md
docs/security/gdpr-compliance.md
docs/training/
docs/training/lawyer-training.md
docs/training/admin-training.md
```

**Agents:**
1. Agent Staging Deploy
2. Agent Monitoring & Alerting
3. Agent Backup & DR
4. Agent Security Audit
5. Agent GDPR Compliance
6. Agent Beta Coordination
7. Agent Feedback Analysis
8. Agent Bug Fixes
9. Agent Training Materials
10. Agent Production Checklist

**Beta Testing Protocol:**

```markdown
# Beta Testing Week 1 - Daily Check-ins

**Day 1:**
- Onboarding session (1h)
- First use of each innovation
- Feedback: First impressions

**Day 2:**
- Use SENTINEL on 5 new contacts
- Use TIMELINE MAGIC on 1 complex case
- Feedback: Ease of use

**Day 3:**
- Use BRAIN for 1 full day
- Track time saved
- Feedback: Usefulness

**Day 4:**
- Use PROPHET on 3 cases
- Compare predictions to expectations
- Feedback: Accuracy perception

**Day 5:**
- Free use (all innovations)
- Feedback: Top 3 issues + Top 3 wins

**Week 2-3:**
- Weekly feedback sessions (2h)
- Bug fixes deployed daily
- Feature iterations based on feedback
```

**Tests:**
- Staging deployment smoke tests
- Backup & restore tests
- Security penetration tests
- GDPR compliance tests
- Beta user acceptance tests

**Success Criteria:**
- Staging deployment successful
- 5-7 beta users onboarded
- > 80% beta user satisfaction
- < 10 critical bugs remaining
- Production readiness checklist 100% complete

---

## Execution Strategy

### Parallel Agents Per Phase

Each phase uses 8-10 agents working concurrently on independent components.

**Example (Phase 4 - BRAIN Core):**
- Agent 1: Event Stream (Redis Streams)
- Agent 2: Call Watcher + Email Watcher
- Agent 3: Document Watcher + Calendar Watcher
- Agent 4: Deadline Watcher
- Agent 5: Fact Extractor + Sentiment Analyzer
- Agent 6: Risk Detector + Opportunity Finder
- Agent 7: Contradiction Checker
- Agent 8: Actors (Reminder, Alert, Suggestion)
- Agent 9: Backend API + Tests
- Agent 10: Frontend UI + Tests

**Timeline:**
- Week 7: Agents 1-5 (infrastructure + watchers + analyzers)
- Week 8: Agents 6-8 (analyzers + actors)
- Week 9: Agents 9-10 (API + UI + integration)

### TDD Throughout

Every agent follows TDD:
1. Write failing test
2. Implement minimal code
3. Run test to verify pass
4. Commit
5. Repeat

### Commit Frequency

Commit every 30-60 minutes of work. Small, focused commits.

**Commit Message Format:**
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:** feat, fix, test, refactor, docs, style, chore

**Examples:**
```
feat(brain): add call watcher with event detection

Implements CallWatcher that listens to Redis stream for new call events.
Extracts call metadata and triggers FactExtractor analyzer.

Closes #42

test(sentinel): add cypher query tests for director overlap

Adds test fixtures for Neo4j with sample companies and directors.
Tests detect_director_overlap query with 3 scenarios.

fix(prophet): correct feature engineering for judge history

Judge history was using wrong table join causing NULL values.
Fixed join condition to use judge_id correctly.

Fixes #156
```

### Review Checkpoints

**After each phase:**
1. Run full test suite
2. Manual QA of new features
3. Performance benchmarks
4. Security review (if applicable)
5. Code review by PM
6. Decision: Proceed to next phase or iterate

**GO/NO-GO Criteria:**
- All tests passing
- No P0/P1 bugs
- Performance targets met
- Security issues resolved

---

## Sub-Plans to Be Created

As each phase begins, create its detailed sub-plan:

1. `docs/plans/phase-1-foundations.md` - Before Week 1
2. `docs/plans/phase-2-sentinel.md` - Before Week 3
3. `docs/plans/phase-3-timeline-magic.md` - Before Week 5
4. `docs/plans/phase-4-brain-core.md` - Before Week 7
5. `docs/plans/phase-5-brain-advanced.md` - Before Week 10
6. `docs/plans/phase-6-prophet.md` - Before Week 12
7. `docs/plans/phase-7-integration.md` - Before Week 15
8. `docs/plans/phase-8-beta.md` - Before Week 17

**Each sub-plan should:**
- Break phase into bite-sized tasks (2-5 minutes each)
- Include complete code snippets
- Specify exact file paths
- Include test commands with expected output
- Follow TDD rigorously
- Include commit messages

---

## Tech Stack Reference

### Backend

| Component | Technology | Installation |
|-----------|-----------|--------------|
| Language | Python 3.12 | `python --version` |
| API Framework | FastAPI | `pip install fastapi[all]` |
| ORM | SQLAlchemy 2.0 | `pip install sqlalchemy[asyncio]` |
| Migrations | Alembic | `pip install alembic` |
| Task Queue | Celery | `pip install celery[redis]` |
| Message Broker | Redis | `docker run -d -p 6379:6379 redis` |
| Database | PostgreSQL 16 | `docker run -d -p 5432:5432 postgres:16` |
| Graph DB | Neo4j 5.15 | `docker run -d -p 7474:7474 -p 7687:7687 neo4j:5.15` |
| Vector DB | Qdrant 1.7 | `docker run -d -p 6333:6333 qdrant/qdrant:v1.7` |
| ML | scikit-learn, XGBoost, LightGBM | `pip install scikit-learn xgboost lightgbm` |
| DL | PyTorch | `pip install torch` |
| NLP | spaCy | `pip install spacy && python -m spacy download fr_core_news_lg` |
| LLM | Anthropic Claude | `pip install anthropic` |

### Frontend

| Component | Technology | Installation |
|-----------|-----------|--------------|
| Framework | Next.js 14 | `npx create-next-app@latest` |
| Language | TypeScript | Built-in with Next.js |
| UI Library | shadcn/ui | `npx shadcn-ui@latest init` |
| Charts | Recharts | `npm install recharts` |
| Timeline | vis.js | `npm install vis-timeline` |
| Graph | cytoscape.js | `npm install cytoscape` |
| State | Zustand | `npm install zustand` |
| Forms | React Hook Form | `npm install react-hook-form` |
| API Client | TanStack Query | `npm install @tanstack/react-query` |

### DevOps

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Container | Docker | Containerization |
| Orchestration | Docker Compose | Local dev |
| CI/CD | GitHub Actions | Automation |
| Monitoring | Prometheus | Metrics |
| Dashboards | Grafana | Visualization |
| Logging | Elasticsearch | Log aggregation |
| Error Tracking | Sentry | Error monitoring |

---

## Cost Estimate

### Infrastructure (Monthly)

| Component | Cost |
|-----------|------|
| OVH Cloud (8 vCPU, 16GB RAM) | €60 |
| PostgreSQL (managed) | €40 |
| Neo4j (self-hosted) | €0 |
| Qdrant (self-hosted) | €0 |
| Redis (managed) | €20 |
| Backup storage (100GB) | €5 |
| **Total Infrastructure** | **€125/month** |

### AI APIs (Monthly)

| Service | Usage | Cost |
|---------|-------|------|
| Anthropic Claude (500k tokens/day) | Generation | €300 |
| OpenAI Embeddings (1M embeddings) | Vector search | €100 |
| **Total AI APIs** | | **€400/month** |

### Development (One-time)

| Item | Cost |
|------|------|
| Developer time (18 weeks @ €500/day) | €45,000 |
| Testing & QA | €3,000 |
| Security audit | €2,000 |
| **Total Development** | **€50,000** |

### Grand Total

- **Development:** €50,000 (one-time)
- **Operational:** €525/month (€6,300/year)
- **Year 1 Total:** €56,300

---

## Success Metrics

### BRAIN

- 90% adoption by lawyers (after 1 month)
- 70% suggestion acceptance rate
- 2-3h saved per lawyer per day
- < 5% false positives
- < 2s action generation latency

### PROPHET

- AUC-ROC > 0.80 (classification)
- R² > 0.70 (regression)
- C-index > 0.75 (survival)
- 60% of cases predicted
- 40% lawyers use before strategy decision

### SENTINEL

- 100% direct conflicts detected
- 95% indirect conflicts detected
- < 10% false positives
- < 500ms check time
- 0 undetected conflicts (after 3 months)

### TIMELINE MAGIC

- 85% events auto-extracted
- < 15% need manual editing
- 90% date/actor accuracy
- 50% complex cases use it
- 80% time reduction (10h → 2h)

### Global

- 99.9% uptime
- < 200ms API p95 latency
- < 2s frontend load time
- Break-even at 6 months
- 3x ROI at 12 months

---

## Risk Mitigation

### Technical Risks

| Risk | Mitigation |
|------|-----------|
| LLM latency | Aggressive caching, fallback to faster models |
| High AI API costs | Rate limiting, quotas per tenant, local models for simple tasks |
| Poor ML accuracy | Require 500+ cases dataset, rigorous validation, disclaimers |
| Graph DB scaling | Sharding, read replicas, Redis cache |
| NLP extraction errors | Human-in-the-loop validation, continuous learning |

### Business Risks

| Risk | Mitigation |
|------|-----------|
| Lawyer resistance | Progressive onboarding, quick wins, training |
| Low AI trust | Explainability (SHAP), human validation, disclaimers |
| Legal liability | "Decision support tool" framing, insurance, legal review |
| Insufficient data | Seed with anonymized data, partnerships |

### Legal Risks

| Risk | Mitigation |
|------|-----------|
| GDPR violation | Privacy by design, DPO, regular audits |
| Professional secrecy | End-to-end encryption, EU hosting, no data export |
| Bar Association rules | Consultation with Bar, compliance review |

---

## Next Steps

**Plan complete and saved to `docs/plans/2026-02-17-4-innovations-implementation-plan.md`.**

**Two execution options:**

### 1. Subagent-Driven (This Session)
- I dispatch fresh subagent per phase
- Code review between phases
- Fast iteration and feedback
- **REQUIRED SUB-SKILL:** superpowers:subagent-driven-development

### 2. Parallel Session (Separate)
- Open new session with executing-plans
- Batch execution with checkpoints
- Phase-by-phase execution
- **REQUIRED SUB-SKILL:** In new session, use superpowers:executing-plans

**Which execution approach do you prefer?**

---

**Note:** This master plan provides the high-level structure. Each phase (1-8) will have its own detailed sub-plan created just-in-time with bite-sized tasks (2-5 minutes each), complete code snippets, exact file paths, test commands, and TDD throughout.
