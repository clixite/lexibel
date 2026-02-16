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
)
