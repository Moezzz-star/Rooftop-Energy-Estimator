"""Read-side query helpers for the projects app.

Selectors keep read queries out of write-focused services (code-architecture
§8). They return querysets scoped to the requesting owner (DEC-08).
"""

from __future__ import annotations

from typing import Any

from django.db.models import QuerySet

from .models import Project


def list_for_owner(user: Any) -> QuerySet[Project]:
    """Return the projects owned by ``user``, newest first.

    Args:
        user: The owning user.

    Returns:
        A queryset of that user's projects (ordered by ``-created_at``).
    """
    return Project.objects.filter(owner=user).order_by("-created_at")
