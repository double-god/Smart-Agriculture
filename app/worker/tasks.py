"""
Celery Tasks for Smart Agriculture System.

This module defines async tasks for CV processing and report generation.
"""

from app.worker.celery_app import celery_app


@celery_app.task(name="app.worker.tasks.health_check")
def health_check():
    """Health check task for Celery worker."""
    return {"status": "healthy", "service": "smart-agriculture-worker"}
