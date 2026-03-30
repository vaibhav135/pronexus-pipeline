from celery import Celery

from app.config import settings

celery_app = Celery(
    "pronexus",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    worker_hijack_root_logger=False,
)

# Explicit task imports (autodiscover can be flaky)
import app.tasks.enrich  # noqa: F401
