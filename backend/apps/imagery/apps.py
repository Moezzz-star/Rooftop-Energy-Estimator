"""App configuration for the imagery app."""

from __future__ import annotations

from django.apps import AppConfig


class ImageryConfig(AppConfig):
    """Django application config for :mod:`apps.imagery`."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.imagery"
    label = "imagery"
    verbose_name = "Imagery"

    def ready(self) -> None:
        """Wire post-delete signal handlers (storage cleanup)."""
        from . import signals  # noqa: F401  (import registers receivers)
