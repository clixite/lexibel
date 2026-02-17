"""Prometheus metrics for LexiBel."""
import logging
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response

logger = logging.getLogger(__name__)

# API metrics
api_requests_total = Counter(
    'lexibel_api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status']
)

api_request_duration_seconds = Histogram(
    'lexibel_api_request_duration_seconds',
    'API request duration',
    ['method', 'endpoint']
)

# BRAIN metrics
brain_actions_total = Counter(
    'lexibel_brain_actions_total',
    'Total BRAIN actions',
    ['action_type', 'status']
)

brain_insights_total = Counter(
    'lexibel_brain_insights_total',
    'Total BRAIN insights',
    ['insight_type', 'severity']
)

# PROPHET metrics
prophet_predictions_total = Counter(
    'lexibel_prophet_predictions_total',
    'Total PROPHET predictions',
    ['prediction_type']
)

prophet_prediction_duration_seconds = Histogram(
    'lexibel_prophet_prediction_duration_seconds',
    'PROPHET prediction duration'
)

# SENTINEL metrics
sentinel_conflicts_detected = Counter(
    'lexibel_sentinel_conflicts_detected',
    'Total conflicts detected',
    ['conflict_type', 'severity']
)

sentinel_check_duration_seconds = Histogram(
    'lexibel_sentinel_check_duration_seconds',
    'SENTINEL conflict check duration'
)

# TIMELINE metrics
timeline_events_extracted = Counter(
    'lexibel_timeline_events_extracted',
    'Total timeline events extracted',
    ['source_type']
)

timeline_extraction_duration_seconds = Histogram(
    'lexibel_timeline_extraction_duration_seconds',
    'Timeline extraction duration'
)

# Database metrics
db_connections_active = Gauge(
    'lexibel_db_connections_active',
    'Active database connections',
    ['database']
)


async def metrics_endpoint() -> Response:
    """Prometheus metrics endpoint."""
    try:
        content = generate_latest()
        logger.debug("Generated Prometheus metrics successfully")
        return Response(
            content=content,
            media_type=CONTENT_TYPE_LATEST
        )
    except Exception as e:
        logger.error(f"Failed to generate Prometheus metrics: {e}")
        raise
