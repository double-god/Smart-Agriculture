"""
Celery workers and heavy-lifting logic for Smart Agriculture system.

This module contains background task handlers for CV processing,
RAG retrieval, and LLM inference.
"""

from app.worker.chains import GenerateReport, create_report_chain

__all__ = [
    "GenerateReport",
    "create_report_chain",
]
