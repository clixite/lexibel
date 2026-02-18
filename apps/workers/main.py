"""LexiBel Celery Workers"""

from celery import Celery
import os

app = Celery(
    "lexibel",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Brussels",
    enable_utc=True,
    task_queues={
        "default": {},
        "indexing": {},
        "migration": {},
        "peppol": {},
    },
    beat_schedule={
        "incremental-sync-every-15min": {
            "task": "scheduled_incremental_sync",
            "schedule": 900,
        },
        "refresh-tokens-every-45min": {
            "task": "refresh_expiring_tokens",
            "schedule": 2700,
        },
    },
)

app.autodiscover_tasks(["apps.workers.tasks"])
