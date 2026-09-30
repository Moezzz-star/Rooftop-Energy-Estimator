"""App configuration for the projects app."""

from __future__ import annotations

from django.apps import AppConfig


class ProjectsConfig(AppConfig):
    """Django application config for :mod:`apps.projects`."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.projects"
    label = "projects"
    verbose_name = "Projects"
