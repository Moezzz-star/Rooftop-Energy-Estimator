"""Persistence model for the audit log.

An :class:`AuditEvent` records who did what to which target. Per DEC-03 audit
events are retained independently of the domain data they describe: the only
FK is ``actor`` with ``on_delete=SET_NULL``, and ``actor_email`` is denormalized
so the record survives user deletion. There is no FK to Project/Analysis, so an
event is never cascade-deleted when those are removed.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone

from common.models import BaseModel


class AuditEvent(BaseModel):
    """An immutable record of a significant domain action.

    Attributes:
        action: Machine-readable action key (e.g. ``project.created``).
        actor_email: Denormalized email of the actor (survives user deletion).
        target_type: Type name of the affected resource (e.g. ``Project``).
        target_id: Identifier of the affected resource (stringified).
        metadata: Arbitrary structured context (no secrets/PII beyond email).
        at: When the action occurred.
        actor: The acting user; set to NULL if that user is later deleted.
    """

    action = models.CharField(max_length=100)
    actor_email = models.EmailField(blank=True, default="")
    target_type = models.CharField(max_length=100, blank=True, default="")
    target_id = models.CharField(max_length=64, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    at = models.DateTimeField(default=timezone.now, db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
    )

    objects: models.Manager[AuditEvent] = models.Manager()

    class Meta:
        ordering = ["-at"]
        indexes = [
            models.Index(fields=["action", "-at"]),
            models.Index(fields=["target_type", "target_id"]),
        ]

    def __str__(self) -> str:
        """Return a compact action/target descriptor."""
        return f"{self.action} {self.target_type}:{self.target_id}"
