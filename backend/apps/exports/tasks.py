"""Celery tasks for the exports app (THIN wrappers -> services).

Routed to the ``cpu-heavy`` queue by ``CELERY_TASK_ROUTES``. The task resolves
the artifact and delegates building to :class:`ExportService`; no branching
logic lives here (code-architecture §6).
"""

from __future__ import annotations

from celery import shared_task

from common.logging import get_logger

from .models import ExportArtifact
from .services import ExportService

logger = get_logger("exports.tasks")


@shared_task(name="apps.exports.tasks.generate_export")  # type: ignore[misc]  # celery is untyped
def generate_export(artifact_id: str) -> str:
    """Build the export artifact identified by ``artifact_id``.

    Args:
        artifact_id: Primary key of the pending :class:`ExportArtifact`.

    Returns:
        The artifact id as a string.
    """
    artifact = ExportArtifact.objects.select_related("analysis").get(pk=artifact_id)
    logger.info("Generating export", extra={"analysis_id": str(artifact.analysis_id)})
    ExportService().build(artifact)
    return str(artifact.pk)
