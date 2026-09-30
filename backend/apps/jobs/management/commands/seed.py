"""``python manage.py seed`` — idempotent baseline data for dev/demo.

Registers the canonical ML model version and the default solar methodology, and
(optionally) creates a demo user + project. Safe to run repeatedly. Used by
``make seed``. No secrets are hardcoded: the demo password is read from
``DEMO_PASSWORD`` (default ``demo12345`` for local dev only).
"""

from __future__ import annotations

import os
from typing import Any

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

_DEMO_EMAIL = "demo@example.com"
_DEMO_PROJECT_NAME = "Demo Project"


class Command(BaseCommand):
    """Seed the registries and a demo user/project idempotently."""

    help = "Idempotently seed the model registry, solar method, and demo data."

    def add_arguments(self, parser: Any) -> None:
        """Register command-line options."""
        parser.add_argument(
            "--no-demo-user",
            action="store_true",
            help="Skip creating the demo user and project.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Run the idempotent seed operations."""
        from apps.ml_models.services import ModelRegistryService
        from apps.solar.services import SolarMethodRegistry

        model = ModelRegistryService.get_or_create_default()
        method = SolarMethodRegistry.get_or_create_default()
        self.stdout.write(f"model registry: {model.name}@{model.version} ({model.status})")
        self.stdout.write(f"solar method:   {method.name}@{method.version}")

        if options.get("no_demo_user"):
            return
        user, project = self._ensure_demo(str(model.pk))
        self.stdout.write(f"demo user:      {user.email}")
        self.stdout.write(f"demo project:   {project.name} ({project.pk})")

    def _ensure_demo(self, _model_id: str) -> tuple[Any, Any]:
        """Create (idempotently) the demo user and a demo project."""
        from django.apps import apps as django_apps

        user_model = get_user_model()
        password = os.environ.get("DEMO_PASSWORD", "demo12345")
        user = user_model.objects.filter(email=_DEMO_EMAIL).first()
        if user is None:
            user = user_model.objects.create_user(email=_DEMO_EMAIL, password=password)

        project_model = django_apps.get_model("projects", "Project")
        project, _ = project_model.objects.get_or_create(
            owner=user,
            name=_DEMO_PROJECT_NAME,
            defaults={"description": "Auto-created demo project."},
        )
        return user, project
