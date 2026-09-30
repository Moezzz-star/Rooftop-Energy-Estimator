"""App configuration for the audit app."""

from __future__ import annotations

from django.apps import AppConfig


class AuditConfig(AppConfig):
    """Django application config for :mod:`apps.audit`."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.audit"
    label = "audit"
    verbose_name = "Audit"
