"""App configuration for the exports app."""

from __future__ import annotations

from django.apps import AppConfig


class ExportsConfig(AppConfig):
    """Django application config for :mod:`apps.exports`."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.exports"
    label = "exports"
    verbose_name = "Exports"

    def ready(self) -> None:
        """Wire post-delete signal handlers (storage cleanup)."""
        from . import signals  # noqa: F401  (import registers receivers)
