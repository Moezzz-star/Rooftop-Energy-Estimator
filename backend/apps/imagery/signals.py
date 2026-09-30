"""Signal handlers for the imagery app.

On :class:`ImageryAsset` deletion, remove the backing raster from object
storage so orphaned bytes do not accumulate (code-architecture §3 cleanup).
Storage errors are logged and swallowed here: the row is already gone and a
missing/stale object must not break the delete transaction.
"""

from __future__ import annotations

from typing import Any

from django.db.models.signals import post_delete
from django.dispatch import receiver

from common.errors import InfrastructureError
from common.logging import get_logger
from common.storage import get_storage

from .models import ImageryAsset

logger = get_logger("imagery.signals")


@receiver(post_delete, sender=ImageryAsset, dispatch_uid="imagery_asset_storage_cleanup")
def delete_imagery_storage(sender: type[ImageryAsset], instance: ImageryAsset, **_: Any) -> None:
    """Delete the stored raster bytes when an :class:`ImageryAsset` is removed."""
    if not instance.storage_key:
        return
    try:
        get_storage().delete(instance.storage_key)
        logger.info("Deleted imagery storage object on asset delete")
    except InfrastructureError:
        logger.warning("Failed to delete imagery storage object on asset delete")
