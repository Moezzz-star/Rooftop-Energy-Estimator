"""Domain services for the projects app.

:class:`ProjectService` owns project creation and archival. Views delegate to
it; no business logic lives in views/serializers (code-architecture §6).
"""

from __future__ import annotations

from typing import Any

from common.errors import ValidationError
from common.logging import get_logger

from .models import Project

logger = get_logger("projects.service")


class ProjectService:
    """Create and archive projects for an owning user."""

    def create(self, owner: Any, name: str, description: str = "") -> Project:
        """Create and persist a project owned by ``owner``.

        Args:
            owner: The owning user instance.
            name: Project name; must be non-empty after trimming.
            description: Optional description.

        Returns:
            The created :class:`Project`.

        Raises:
            ValidationError: If ``name`` is empty.
        """
        clean_name = (name or "").strip()
        if not clean_name:
            raise ValidationError("Project name is required.", details={"name": "required"})

        project = Project.objects.create(
            owner=owner,
            name=clean_name,
            description=description or "",
        )
        logger.info("Project created", extra={"trace_id": None})
        return project

    def archive(self, project: Project) -> Project:
        """Archive a project (idempotent) and persist the change.

        Args:
            project: The project to archive.

        Returns:
            The updated :class:`Project`.
        """
        if not project.is_archived:
            project.archive()
            project.save(update_fields=["is_archived", "updated_at"])
            logger.info("Project archived")
        return project
