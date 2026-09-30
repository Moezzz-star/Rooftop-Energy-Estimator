"""Signal handlers for the analyses app (DEC-03 / DEC-08 delete auditing).

Deleting a :class:`~apps.projects.models.Project` cascades (FK ``CASCADE``) to
its analyses, and each analysis in turn cascades to its imagery assets and
export artifacts. Those child apps own ``post_delete`` handlers that remove the
backing storage objects, so no orphaned bytes remain — this module deliberately
does **not** duplicate that storage-deletion logic.

What this module adds is the durable audit trail: on every ``Analysis`` delete
(direct or via project cascade) it records an :class:`~apps.audit.models.
AuditEvent`. Because ``AuditEvent`` has no FK back to Project/Analysis (only a
``SET_NULL`` actor), the event is retained independently of the data it
describes (DEC-03) and survives the cascade.

The acting user is threaded in via an optional ``_audit_actor`` attribute set by
the view before ``delete()``; a cascade delete has no such attribute and records
a ``None`` actor (system action), which is expected.
"""

from __future__ import annotations

from typing import Any

from django.db.models.signals import post_delete, pre_delete
from django.dispatch import receiver

from apps.audit.services import AuditService
from common.logging import get_logger

from .models import Analysis

logger = get_logger("analyses.signals")

_AUDIT_ACTOR_ATTR = "_audit_actor"
_AUDIT_PROJECT_ID_ATTR = "_audit_project_id"


@receiver(pre_delete, sender=Analysis, dispatch_uid="analysis_delete_audit_capture")
def capture_analysis_project_id(sender: type[Analysis], instance: Analysis, **_: Any) -> None:
    """Stash the analysis's ``project_id`` before the delete clears the FK.

    During a project-cascade delete the FK is nulled out before ``post_delete``
    fires, so we capture it here (``pre_delete`` runs while the value is still
    present) for the audit handler to read.
    """
    instance._audit_project_id = instance.project_id  # type: ignore[attr-defined]  # signal hand-off


@receiver(post_delete, sender=Analysis, dispatch_uid="analysis_delete_audit")
def record_analysis_deletion(sender: type[Analysis], instance: Analysis, **_: Any) -> None:
    """Record an immutable audit event when an :class:`Analysis` is deleted.

    Fires for both direct deletes and project-cascade deletes. Storage cleanup
    for the analysis's artifacts is handled by the imagery/exports post_delete
    handlers as their rows cascade; this handler only writes the audit trail.

    Failures to write the audit event are logged and swallowed so a best-effort
    audit never breaks the delete transaction.
    """
    actor = getattr(instance, _AUDIT_ACTOR_ATTR, None)
    project_id = getattr(instance, _AUDIT_PROJECT_ID_ATTR, None)
    logger.warning("PD_DEBUG stash=%r has=%r direct=%r", project_id, hasattr(instance, _AUDIT_PROJECT_ID_ATTR), instance.project_id)
    if project_id is None:
        project_id = instance.project_id
    try:
        AuditService().record(
            action="analysis.deleted",
            actor=actor,
            target=instance,
            metadata={
                "analysis_id": str(instance.pk),
                "project_id": str(project_id),
                "name": instance.name,
                "status": instance.status,
            },
        )
        logger.info("Recorded analysis deletion audit event")
    except Exception:  # audit is best-effort and must never block the delete
        logger.warning(
            "Failed to record analysis deletion audit event",
            extra={"analysis_id": str(instance.pk)},
        )
