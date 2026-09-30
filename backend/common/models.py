"""Abstract base model shared by all persisted domain entities.

Provides a UUID primary key plus creation/update timestamps as mandated by
``docs/architecture/code-architecture.md`` §3.
"""

from __future__ import annotations

import uuid

from django.db import models


class BaseModel(models.Model):
    """Abstract base with a UUID primary key and audit timestamps.

    Attributes:
        id: UUID v4 primary key (non-sequential, safe to expose in URLs).
        created_at: Set once on creation.
        updated_at: Refreshed on every save.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]
