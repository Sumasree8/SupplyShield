"""
Celery application entrypoint.

This is the module referenced by `celery -A src.tasks.celery_app` in
docker-compose (worker and beat). It re-exports the configured Celery instance
and imports the task modules so their @task decorators register on startup.
"""
from src.tasks.ingestion import celery_app, CELERY_AVAILABLE

# Importing src.tasks.ingestion (above) registers the ingestion tasks and the
# beat schedule on `celery_app`. Add future task module imports here so the
# worker/beat process discovers them.

if not CELERY_AVAILABLE:  # pragma: no cover - defensive
    raise RuntimeError(
        "Celery is not installed but the worker entrypoint was invoked. "
        "Install requirements.txt before running the worker/beat process."
    )

__all__ = ["celery_app"]
