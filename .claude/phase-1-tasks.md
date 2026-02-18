# Phase 1 Tasks

## Task 1: Setup Neo4j for SENTINEL
- Create: infra/neo4j/docker-compose.yml
- Create: infra/neo4j/.env.example
- Create: infra/neo4j/init.cypher
- Create: apps/api/services/neo4j_client.py
- Create: apps/api/tests/test_neo4j_client.py
- Test with docker compose up and pytest
- Commit

## Task 2: Setup Qdrant for BRAIN
- Create: infra/qdrant/docker-compose.yml
- Create: apps/api/services/qdrant_client.py
- Create: apps/api/tests/test_qdrant_client.py
- Test with docker compose up and pytest
- Commit

## Task 3: Setup Monitoring (Prometheus + Grafana)
- Create: infra/monitoring/docker-compose.yml
- Create: infra/monitoring/prometheus.yml
- Create: infra/monitoring/grafana/dashboards/lexibel.json
- Create: apps/api/services/metrics.py
- Modify: apps/api/main.py (add /metrics endpoint)
- Test with docker compose up and verify endpoints
- Commit

## Task 4: Create BRAIN Models
- Create: packages/db/models/brain_action.py
- Create: packages/db/models/brain_insight.py
- Create: packages/db/models/brain_memory.py
- Create: apps/api/tests/test_brain_models.py
- Test model instantiation
- Commit

## Task 5: Create PROPHET Models
- Create: packages/db/models/prophet_prediction.py
- Create: packages/db/models/prophet_simulation.py
- Create: apps/api/tests/test_prophet_models.py
- Test model instantiation
- Commit

## Task 6: Create SENTINEL Models
- Create: packages/db/models/sentinel_conflict.py
- Create: packages/db/models/sentinel_entity.py
- Create: apps/api/tests/test_sentinel_models.py
- Test model instantiation
- Commit

## Task 7: Create TIMELINE Models
- Create: packages/db/models/timeline_event.py
- Create: packages/db/models/timeline_document.py
- Create: apps/api/tests/test_timeline_models.py
- Test model instantiation
- Commit

## Task 8: Create Alembic Migrations
- Create: packages/db/migrations/versions/011_create_brain_tables.py
- Create: packages/db/migrations/versions/012_create_prophet_tables.py
- Create: packages/db/migrations/versions/013_create_sentinel_tables.py
- Create: packages/db/migrations/versions/014_create_timeline_tables.py
- Test with alembic upgrade/downgrade
- Commit

## Task 9: Setup CI/CD Pipeline
- Create: .github/workflows/test.yml
- Create: .github/workflows/deploy-staging.yml
- Commit

## Task 10: Documentation
- Create: docs/infrastructure/README.md
- Create: docs/infrastructure/neo4j-setup.md
- Create: docs/infrastructure/qdrant-setup.md
- Create: docs/infrastructure/monitoring.md
- Create: docs/database/models-overview.md
- Commit
