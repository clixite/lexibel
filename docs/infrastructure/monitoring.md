# Monitoring with Prometheus & Grafana

Complete observability stack for LexiBel infrastructure and application metrics.

## Overview

- **Prometheus**: Time-series metrics collection and alerting
- **Grafana**: Metrics visualization and dashboards
- **Use Cases**:
  - Track API performance
  - Monitor database health
  - Alert on anomalies
  - Custom metrics for BRAIN/PROPHET/SENTINEL/TIMELINE

## Architecture

```
┌──────────────┐
│   LexiBel    │ ──metrics──> ┌─────────────┐
│     API      │              │ Prometheus  │
└──────────────┘              │   :9090     │
                              └──────┬──────┘
┌──────────────┐                     │
│    Neo4j     │ ──metrics──>        │
│   :7474      │                     │
└──────────────┘                     │
                                     │ scrapes
┌──────────────┐                     │
│    Redis     │ ──metrics──>        │
│   :6379      │                     │
└──────────────┘                     │
                                     ▼
                              ┌─────────────┐
                              │   Grafana   │
                              │   :3200     │
                              └─────────────┘
```

## Quick Start

### 1. Start Monitoring Stack

```bash
cd /f/LexiBel
docker compose up -d prometheus grafana
```

### 2. Access Dashboards

- **Prometheus**: `http://localhost:9090`
- **Grafana**: `http://localhost:3200`

**Grafana Default Credentials**:
- Username: `admin`
- Password: `admin` (change on first login)

### 3. Add Prometheus Data Source in Grafana

1. Go to Configuration → Data Sources
2. Add Prometheus
3. URL: `http://prometheus:9090`
4. Save & Test

## Prometheus Configuration

### File: `infra/monitoring/prometheus.yml`

```yaml
global:
  scrape_interval: 15s      # Scrape targets every 15s
  evaluation_interval: 15s  # Evaluate rules every 15s

scrape_configs:
  # LexiBel API metrics
  - job_name: 'lexibel-api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/metrics'

  # Neo4j metrics
  - job_name: 'neo4j'
    static_configs:
      - targets: ['neo4j:7474']
    metrics_path: '/metrics'

  # Redis metrics (via redis-exporter)
  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
```

## Custom Metrics for LexiBel

### BRAIN Metrics

**Purpose**: Track proactive action generation and execution

```python
from prometheus_client import Counter, Histogram, Gauge

# Actions generated
brain_actions_generated = Counter(
    'brain_actions_generated_total',
    'Total number of BRAIN actions generated',
    ['action_type', 'priority']
)

# Actions executed
brain_actions_executed = Counter(
    'brain_actions_executed_total',
    'Total number of BRAIN actions executed',
    ['action_type', 'status']
)

# Action generation latency
brain_action_latency = Histogram(
    'brain_action_generation_seconds',
    'Time to generate BRAIN action',
    ['action_type']
)

# Pending actions gauge
brain_pending_actions = Gauge(
    'brain_pending_actions',
    'Number of pending BRAIN actions',
    ['priority']
)

# Usage
brain_actions_generated.labels(action_type='alert', priority='critical').inc()
with brain_action_latency.labels(action_type='draft').time():
    generate_draft()
```

### PROPHET Metrics

**Purpose**: Track ML predictions and model performance

```python
# Predictions generated
prophet_predictions = Counter(
    'prophet_predictions_total',
    'Total number of PROPHET predictions',
    ['prediction_type']
)

# Prediction confidence
prophet_confidence = Histogram(
    'prophet_confidence_score',
    'PROPHET prediction confidence scores',
    ['prediction_type'],
    buckets=[0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 1.0]
)

# Model accuracy (when actual outcome known)
prophet_accuracy = Histogram(
    'prophet_accuracy',
    'PROPHET prediction accuracy',
    ['prediction_type', 'model_version']
)

# Feature importance
prophet_feature_importance = Gauge(
    'prophet_feature_importance',
    'SHAP feature importance',
    ['feature_name', 'prediction_type']
)

# Usage
prophet_predictions.labels(prediction_type='outcome').inc()
prophet_confidence.labels(prediction_type='outcome').observe(0.85)
```

### SENTINEL Metrics

**Purpose**: Track conflict detection and resolution

```python
# Conflicts detected
sentinel_conflicts_detected = Counter(
    'sentinel_conflicts_detected_total',
    'Total conflicts detected by SENTINEL',
    ['conflict_type', 'severity']
)

# Conflicts resolved
sentinel_conflicts_resolved = Counter(
    'sentinel_conflicts_resolved_total',
    'Total conflicts resolved',
    ['conflict_type', 'resolution']
)

# Graph traversal time
sentinel_graph_query_latency = Histogram(
    'sentinel_graph_query_seconds',
    'Neo4j graph query latency',
    ['query_type']
)

# Active conflicts gauge
sentinel_active_conflicts = Gauge(
    'sentinel_active_conflicts',
    'Number of unresolved conflicts',
    ['severity']
)

# Usage
sentinel_conflicts_detected.labels(
    conflict_type='direct_adversary',
    severity='high'
).inc()

with sentinel_graph_query_latency.labels(query_type='ownership').time():
    detect_ownership_conflicts()
```

### TIMELINE Metrics

**Purpose**: Track event extraction and validation

```python
# Events extracted
timeline_events_extracted = Counter(
    'timeline_events_extracted_total',
    'Total TIMELINE events extracted',
    ['category', 'source_type']
)

# Events validated
timeline_events_validated = Counter(
    'timeline_events_validated_total',
    'Total events validated by users',
    ['category', 'validation_result']
)

# Extraction confidence
timeline_confidence = Histogram(
    'timeline_extraction_confidence',
    'NLP extraction confidence scores',
    ['category'],
    buckets=[0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 1.0]
)

# NLP processing time
timeline_nlp_latency = Histogram(
    'timeline_nlp_processing_seconds',
    'NLP processing time per document',
    ['source_type']
)

# Usage
timeline_events_extracted.labels(
    category='meeting',
    source_type='email'
).inc()

timeline_confidence.labels(category='meeting').observe(0.92)
```

## Standard API Metrics

### HTTP Request Metrics

```python
from prometheus_client import Counter, Histogram

# Request count
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

# Request latency
http_request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint']
)

# Active requests
http_requests_in_progress = Gauge(
    'http_requests_in_progress',
    'Active HTTP requests',
    ['method', 'endpoint']
)

# Usage in FastAPI middleware
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    method = request.method
    endpoint = request.url.path

    http_requests_in_progress.labels(method=method, endpoint=endpoint).inc()

    with http_request_duration.labels(method=method, endpoint=endpoint).time():
        response = await call_next(request)

    http_requests_in_progress.labels(method=method, endpoint=endpoint).dec()
    http_requests_total.labels(
        method=method,
        endpoint=endpoint,
        status=response.status_code
    ).inc()

    return response
```

### Database Metrics

```python
# Query latency
db_query_duration = Histogram(
    'db_query_duration_seconds',
    'Database query latency',
    ['query_type', 'table']
)

# Connection pool
db_pool_size = Gauge(
    'db_pool_size',
    'Database connection pool size',
    ['state']  # 'active', 'idle'
)

# Transaction rate
db_transactions_total = Counter(
    'db_transactions_total',
    'Total database transactions',
    ['operation', 'table']
)
```

## Example Queries (PromQL)

### Request Rate (QPS)

```promql
# Total requests per second
rate(http_requests_total[5m])

# Requests per endpoint
sum by (endpoint) (rate(http_requests_total[5m]))
```

### Error Rate

```promql
# 5xx error rate
sum(rate(http_requests_total{status=~"5.."}[5m]))
  /
sum(rate(http_requests_total[5m]))

# Error percentage
100 * sum(rate(http_requests_total{status=~"[45].."}[5m]))
  /
sum(rate(http_requests_total[5m]))
```

### Latency Percentiles

```promql
# 95th percentile latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# 99th percentile by endpoint
histogram_quantile(0.99,
  sum by (endpoint, le) (rate(http_request_duration_seconds_bucket[5m]))
)
```

### BRAIN Actions

```promql
# Actions generated per minute
rate(brain_actions_generated_total[1m])

# Critical actions pending
brain_pending_actions{priority="critical"}

# Action success rate
sum(rate(brain_actions_executed_total{status="executed"}[5m]))
  /
sum(rate(brain_actions_executed_total[5m]))
```

### PROPHET Predictions

```promql
# Prediction rate
rate(prophet_predictions_total[5m])

# Average confidence by type
avg by (prediction_type) (prophet_confidence_score)

# High confidence predictions (>90%)
prophet_predictions_total{confidence_score > 0.9}
```

### SENTINEL Conflicts

```promql
# Conflicts detected per hour
increase(sentinel_conflicts_detected_total[1h])

# Active high-severity conflicts
sentinel_active_conflicts{severity="high"}

# Conflict resolution time
rate(sentinel_conflicts_resolved_total[5m])
```

### TIMELINE Events

```promql
# Events extracted per minute
rate(timeline_events_extracted_total[1m])

# Validation rate
rate(timeline_events_validated_total[5m])

# Average confidence by category
avg by (category) (timeline_extraction_confidence)
```

## Grafana Dashboards

### Create LexiBel Dashboard

1. Go to Dashboards → New Dashboard
2. Add Panel
3. Select Prometheus data source
4. Enter PromQL query
5. Configure visualization

### Sample Panel Configurations

#### API Request Rate
- **Query**: `sum(rate(http_requests_total[5m])) by (endpoint)`
- **Type**: Graph
- **Legend**: `{{endpoint}}`

#### Error Rate
- **Query**: `100 * sum(rate(http_requests_total{status=~"[45].."}[5m])) / sum(rate(http_requests_total[5m]))`
- **Type**: Stat
- **Unit**: percent (0-100)
- **Thresholds**: Green <1%, Yellow <5%, Red ≥5%

#### BRAIN Actions Pending
- **Query**: `sum(brain_pending_actions) by (priority)`
- **Type**: Gauge
- **Legend**: `{{priority}}`

#### PROPHET Prediction Confidence
- **Query**: `avg(prophet_confidence_score) by (prediction_type)`
- **Type**: Time series
- **Legend**: `{{prediction_type}}`

## Alerting Rules

### File: `infra/monitoring/alerts.yml`

```yaml
groups:
  - name: lexibel_alerts
    interval: 30s
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: |
          100 * sum(rate(http_requests_total{status=~"5.."}[5m]))
            /
          sum(rate(http_requests_total[5m])) > 5
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }}%"

      # High latency
      - alert: HighLatency
        expr: |
          histogram_quantile(0.95,
            rate(http_request_duration_seconds_bucket[5m])
          ) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High request latency"
          description: "95th percentile is {{ $value }}s"

      # BRAIN actions stuck
      - alert: BrainActionsPending
        expr: brain_pending_actions{priority="critical"} > 10
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Too many pending BRAIN actions"
          description: "{{ $value }} critical actions pending"

      # SENTINEL conflicts unresolved
      - alert: SentinelConflictsUnresolved
        expr: sentinel_active_conflicts{severity="high"} > 5
        for: 30m
        labels:
          severity: warning
        annotations:
          summary: "High-severity conflicts unresolved"
          description: "{{ $value }} high-severity conflicts active"
```

## Health Checks

### Prometheus

```bash
# Check Prometheus is running
curl http://localhost:9090/-/healthy

# Check targets
curl http://localhost:9090/api/v1/targets
```

### Grafana

```bash
# Check Grafana is running
curl http://localhost:3200/api/health
```

## Troubleshooting

### Prometheus Not Scraping

Check targets status:
```bash
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job, health, lastError}'
```

Common issues:
1. Service not exposing `/metrics` endpoint
2. Network connectivity between containers
3. Incorrect port in `prometheus.yml`

### Grafana Dashboard Not Loading

1. Verify Prometheus data source is configured
2. Check PromQL query syntax
3. Ensure time range includes data

### Missing Metrics

Verify metric is being exported:
```bash
curl http://localhost:8000/metrics | grep brain_actions
```

## Best Practices

1. **Cardinality**: Avoid high-cardinality labels (e.g., user IDs, request IDs)
2. **Naming**: Use descriptive metric names with units (e.g., `_seconds`, `_total`)
3. **Labels**: Use labels for dimensions, not values
4. **Histograms**: Use appropriate buckets for latency metrics
5. **Retention**: Configure Prometheus retention based on storage

## Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [PromQL Cheat Sheet](https://promlabs.com/promql-cheat-sheet/)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/naming/)
