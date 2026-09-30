"""App configuration for the jobs app."""

from __future__ import annotations

from django.apps import AppConfig


class JobsConfig(AppConfig):
    """Django application config for :mod:`apps.jobs`."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.jobs"
    label = "jobs"
    verbose_name = "Processing jobs"
