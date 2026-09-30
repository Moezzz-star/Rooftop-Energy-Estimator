"""Signal handlers for the exports app.

On :class:`ExportArtifact` deletion, remove the backing bytes from object
storage so orphaned artifacts do not accumulate (code-architecture §3 cleanup).
Storage errors are logged and swallowed: the row is already gone and a
missing/stale object must not break the delete transaction.
"""

from __future__ import annotations

from typing import Any

from django.db.models.signals import post_delete
from django.dispatch import receiver

from common.errors import InfrastructureError
from common.logging import get_logger
from common.storage import get_storage

from .models import ExportArtifact

logger = get_logger("exports.signals")


@receiver(post_delete, sender=ExportArtifact, dispatch_uid="export_artifact_storage_cleanup")
def delete_export_storage(sender: type[ExportArtifact], instance: ExportArtifact, **_: Any) -> None:
    """Delete the stored bytes when an :class:`ExportArtifact` is removed."""
    if not instance.storage_key:
        return
    try:
        get_storage().delete(instance.storage_key)
        logger.info("Deleted export storage object on artifact delete")
    except InfrastructureError:
        logger.warning("Failed to delete export storage object on artifact delete")
