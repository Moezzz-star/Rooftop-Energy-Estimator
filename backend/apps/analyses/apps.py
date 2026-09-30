"""App configuration for the analyses app."""

from __future__ import annotations

from django.apps import AppConfig


class AnalysesConfig(AppConfig):
    """Django application config for :mod:`apps.analyses`."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.analyses"
    label = "analyses"
    verbose_name = "Analyses"

    def ready(self) -> None:
        """Wire post-delete signal handlers (delete auditing, DEC-03)."""
        from . import signals  # noqa: F401  (import registers receivers)
