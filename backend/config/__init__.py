"""Config project package.

Ensures the Celery application is imported when Django starts so that the
``@shared_task`` decorator across the domain apps uses the configured app.
"""

from __future__ import annotations

from config.celery import celery_app

__all__ = ("celery_app",)
