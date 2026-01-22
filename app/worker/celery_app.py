"""
Celery Application Configuration for Smart Agriculture System.

This module initializes the Celery application with broker and backend configuration.
"""

from celery import Celery

from app.core.config import get_settings

# Initialize settings
settings = get_settings()

# Create Celery app
celery_app = Celery(
    "smart_agriculture_worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.worker.tasks"],  # Import tasks module
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)


# Example task to verify worker is running
@celery_app.task(name="app.worker.tasks.health_check")
def health_check():
    """Health check task for Celery worker."""
    return {"status": "healthy", "service": "smart-agriculture-worker"}
