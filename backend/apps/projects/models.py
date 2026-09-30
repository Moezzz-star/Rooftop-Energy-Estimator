"""Persistence models for the projects app.

A :class:`Project` is owned by exactly one :class:`~apps.accounts.models.User`
and is the parent of analyses (code-architecture §3). It exposes ``.owner`` so
that :func:`common.permissions.resolve_owner` can enforce object-level access.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models

from common.models import BaseModel


class Project(BaseModel):
    """A user-owned container for analyses.

    Attributes:
        name: Human-readable project name.
        description: Optional free-text description.
        is_archived: Soft-archive flag; archived projects are hidden by default.
        owner: The owning user; deleting the user cascades to their projects.
    """

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    is_archived = models.BooleanField(default=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="projects",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["owner", "is_archived"]),
            models.Index(fields=["owner", "-created_at"]),
        ]

    def __str__(self) -> str:
        """Return the project name for admin/log display."""
        return self.name

    def archive(self) -> None:
        """Mark this project as archived (invariant helper, no I/O policy)."""
        self.is_archived = True
