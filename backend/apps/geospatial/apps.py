"""App configuration for the geospatial app."""

from __future__ import annotations

from django.apps import AppConfig


class GeospatialConfig(AppConfig):
    """Django application config for :mod:`apps.geospatial`."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.geospatial"
    label = "geospatial"
    verbose_name = "Geospatial"
