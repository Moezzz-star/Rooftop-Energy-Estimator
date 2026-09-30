"""Celery tasks for the imagery app (THIN wrappers -> services).

Tasks deserialize ids, resolve objects, call a service method, and return; no
branching domain logic lives here (code-architecture §6, rule after §1). Routed
to the ``cpu-heavy`` queue by ``CELERY_TASK_ROUTES``.

The processing pipeline reads imagery through the provider directly, so this
task is minimal: it records an :class:`ImageryAsset` for a raster already
present in object storage (e.g. an out-of-band ingest).
"""

from __future__ import annotations

from typing import Any

from celery import shared_task
from django.apps import apps as django_apps

from common.logging import get_logger

from .services import ImageryService

logger = get_logger("imagery.tasks")


@shared_task(name="apps.imagery.tasks.ingest_imagery")  # type: ignore[misc]  # celery is untyped
def ingest_imagery(analysis_id: str, storage_key: str) -> str:
    """Record an :class:`ImageryAsset` for ``storage_key`` under ``analysis_id``.

    Args:
        analysis_id: Primary key of the owning ``analyses.Analysis``.
        storage_key: Existing object-storage key for the raster bytes.

    Returns:
        The created asset's primary key as a string.
    """
    analysis_model = django_apps.get_model("analyses", "Analysis")
    analysis: Any = analysis_model.objects.get(pk=analysis_id)
    logger.info("Ingesting imagery", extra={"analysis_id": str(analysis_id)})
    asset = ImageryService().register_from_storage(analysis, storage_key)
    return str(asset.pk)
