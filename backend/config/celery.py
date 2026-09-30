"""Celery application for the Rooftop Energy Estimator.

Defines the ``rooftop`` Celery app, loads configuration from Django settings
using the ``CELERY`` namespace, and autodiscovers ``tasks`` modules across the
installed domain apps.
"""

from __future__ import annotations

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

celery_app = Celery("rooftop")

# All Celery settings live in Django settings under the ``CELERY_`` prefix.
celery_app.config_from_object("django.conf:settings", namespace="CELERY")

# Discover ``tasks.py`` in each app listed in INSTALLED_APPS.
celery_app.autodiscover_tasks()


@celery_app.task(bind=True, ignore_result=True)  # type: ignore[misc]  # celery is untyped
def debug_task(self: object) -> None:  # pragma: no cover - operational helper
    """No-op task used to verify worker connectivity."""
    return None
