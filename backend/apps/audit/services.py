"""Domain service for writing audit events.

:class:`AuditService.record` is the single write path other apps' services call
to append to the immutable audit log (code-architecture §1). It denormalizes the
actor's email so the event remains meaningful after a user is deleted (DEC-03).
"""

from __future__ import annotations

from typing import Any

from common.logging import get_logger

from .models import AuditEvent

logger = get_logger("audit.service")


class AuditService:
    """Append-only writer for :class:`AuditEvent` records."""

    def record(
        self,
        action: str,
        actor: Any | None = None,
        target: Any | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEvent:
        """Persist an audit event describing ``action`` by ``actor`` on ``target``.

        Args:
            action: Machine-readable action key (e.g. ``project.created``).
            actor: The acting user (or ``None`` for system actions).
            target: The affected domain object; its type name and ``id``/``pk``
                are recorded. May be ``None``.
            metadata: Optional structured context (must not contain secrets).

        Returns:
            The persisted :class:`AuditEvent`.
        """
        actor_email = getattr(actor, "email", "") or ""
        target_type = type(target).__name__ if target is not None else ""
        target_id = self._resolve_target_id(target)

        event = AuditEvent.objects.create(
            action=action,
            actor=actor,
            actor_email=actor_email,
            target_type=target_type,
            target_id=target_id,
            metadata=metadata or {},
        )
        logger.info("Audit event recorded", extra={"trace_id": None})
        return event

    @staticmethod
    def _resolve_target_id(target: Any | None) -> str:
        """Best-effort stringified identifier for ``target``."""
        if target is None:
            return ""
        identifier = getattr(target, "id", None) or getattr(target, "pk", None)
        return str(identifier) if identifier is not None else ""
