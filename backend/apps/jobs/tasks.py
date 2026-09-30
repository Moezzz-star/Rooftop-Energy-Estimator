"""Celery tasks for the jobs app (THIN wrappers -> services).

The task deserializes the job id, resolves the :class:`ProcessingJob`, marks it
running, and delegates the entire pipeline to :class:`PipelineRunner`. All
branching lives in :mod:`apps.jobs.services`: :func:`is_transient_error`
classifies a failure and :class:`JobOrchestrator` owns the retry/reset and
terminal-failure bookkeeping (code-architecture §6).

Retries (system-arch §3): transient failures (I/O, DB deadlock, most
``InfrastructureError``) are retried with exponential backoff up to
:data:`~apps.jobs.services.MAX_PIPELINE_RETRIES`, incrementing the persisted
``ProcessingJob.retry_count``; deterministic failures (``ValidationError`` /
``DomainError``) and ``SoftTimeLimitExceeded`` fail fast with a recorded
``failure_code``.

``acks_late`` / reject-on-lost and the global default time limits are configured
in settings; ``soft_time_limit`` / ``time_limit`` are pinned on this task's
decorator so a runaway pipeline is stopped gracefully regardless of globals.
This task is routed to the ``orchestration`` queue by ``CELERY_TASK_ROUTES``.
"""

from __future__ import annotations

from typing import Any

from celery import shared_task

from common.logging import get_logger

from .models import ProcessingJob
from .services import (
    MAX_PIPELINE_RETRIES,
    JobOrchestrator,
    PipelineRunner,
    is_transient_error,
)

logger = get_logger("jobs.tasks")

# Per-task time limits (seconds). Soft raises ``SoftTimeLimitExceeded`` inside
# the task for graceful handling; hard kills the worker as a backstop. Pinned
# here (not only in settings) so the pipeline task is bounded independently.
_SOFT_TIME_LIMIT = 1500
_HARD_TIME_LIMIT = 1800


@shared_task(  # type: ignore[misc]  # celery is untyped
    name="apps.jobs.tasks.run_analysis_pipeline",
    bind=True,
    max_retries=MAX_PIPELINE_RETRIES,
    soft_time_limit=_SOFT_TIME_LIMIT,
    time_limit=_HARD_TIME_LIMIT,
)
def run_analysis_pipeline(self: Any, job_id: str) -> str:
    """Run the analysis pipeline for ``job_id`` with bounded transient retries.

    Args:
        self: The bound Celery task instance (worker metadata + ``retry``).
        job_id: Primary key of the :class:`ProcessingJob` to execute.

    Returns:
        The job id as a string (for result introspection).

    Raises:
        Exception: Re-raises a terminal (non-transient) failure after it has
            been recorded on the job, so the task result reflects the failure.
    """
    job = ProcessingJob.objects.select_related("analysis").get(pk=job_id)
    logger.info("Pipeline task received", extra={"job_id": str(job_id)})

    request = getattr(self, "request", None)
    if request is not None:
        job.worker_info = {
            "task_id": str(getattr(request, "id", "") or ""),
            "hostname": str(getattr(request, "hostname", "") or ""),
        }
        job.save(update_fields=["worker_info", "updated_at"])

    orchestrator = JobOrchestrator()
    orchestrator.mark_running(job)
    try:
        PipelineRunner(orchestrator=orchestrator).run(job)
    except Exception as exc:
        attempt = int(getattr(request, "retries", 0) or 0)
        if is_transient_error(exc) and attempt < MAX_PIPELINE_RETRIES:
            countdown = orchestrator.register_retry(job, attempt)
            logger.warning(
                "Pipeline transient failure; retrying",
                extra={"job_id": str(job.pk)},
            )
            raise self.retry(exc=exc, countdown=countdown)
        orchestrator.mark_failed(job, exc)
        logger.error("Pipeline failed terminally", extra={"job_id": str(job.pk)})
        raise
    return str(job.pk)
