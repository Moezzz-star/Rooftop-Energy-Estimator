"""App configuration for the ml_models app."""

from __future__ import annotations

from django.apps import AppConfig


class MlModelsConfig(AppConfig):
    """Django application config for :mod:`apps.ml_models`."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ml_models"
    label = "ml_models"
    verbose_name = "ML Models"
