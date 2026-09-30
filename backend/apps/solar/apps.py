"""App configuration for the solar app."""

from __future__ import annotations

from django.apps import AppConfig


class SolarConfig(AppConfig):
    """Django application config for :mod:`apps.solar`."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.solar"
    label = "solar"
    verbose_name = "Solar"
