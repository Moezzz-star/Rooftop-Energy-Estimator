"""Persistence models for async orchestration (code-architecture §3, §7).

* :class:`ProcessingJob` is the authoritative, PostgreSQL-backed state of a
  single analysis pipeline run (ADR-0002): overall status, the Celery task id,
  worker info, reproducibility provenance, timing, error envelope, the
  cooperative cancellation flag, and a retry counter.
* :class:`JobStage` is a durable per-stage progress row (real transitions, not
  simulated percentages) ordered by ``sequence``.

The durable stage list for this thin vertical slice is :data:`STAGE_SEQUENCE`
(ten machine keys). It intentionally condenses the granular 20-stage pipeline
described in code-architecture §7 (super-resolution, separate normalize/tile/
reassemble/threshold/morphology/filter/repair/simplify/aggregate steps) into
ten durable checkpoints; the finer granularity is deferred. The frontend mirrors
these keys + labels for its progress UI.

Models hold persistence and simple invariants only; all orchestration logic
lives in :mod:`apps.jobs.services` (code-architecture §6). The
``analyses.Analysis`` reference is a string label so this app is import-safe.
"""

from __future__ import annotations

from django.db import models
from django.utils import timezone

from common.models import BaseModel


class JobStatus(models.TextChoices):
    """Overall lifecycle state of a :class:`ProcessingJob`."""

    QUEUED = "queued", "Queued"
    RUNNING = "running", "Running"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"
    CANCELLED = "cancelled", "Cancelled"


class StageStatus(models.TextChoices):
    """Lifecycle state of a single :class:`JobStage`."""

    PENDING = "pending", "Pending"
    RUNNING = "running", "Running"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"
    SKIPPED = "skipped", "Skipped"


class CleanupStatus(models.TextChoices):
    """Disposition of temp-file / resource cleanup on terminal transitions.

    ``NOT_REQUIRED`` is the resting state; :meth:`JobOrchestrator.cancel` moves
    it to ``PENDING`` (cleanup will happen when the worker observes the flag or
    is revoked); the pipeline's ``finally`` cleanup records ``DONE`` (or
    ``FAILED`` if a temp file could not be removed).
    """

    NOT_REQUIRED = "not_required", "Not required"
    PENDING = "pending", "Pending"
    DONE = "done", "Done"
    FAILED = "failed", "Failed"


class StageName(models.TextChoices):
    """The ten durable pipeline stages, in execution order (§7, condensed).

    Values are the machine keys mirrored by the frontend; labels are the
    human-readable UI strings.
    """

    VALIDATE_REQUEST = "validate_request", "Validate request"
    LOAD_IMAGERY = "load_imagery", "Load imagery"
    VALIDATE_RASTER = "validate_raster", "Validate raster"
    TILE = "tile", "Tile imagery"
    SEGMENT = "segment", "Segment (U-Net inference)"
    POSTPROCESS_MASK = "postprocess_mask", "Post-process mask"
    EXTRACT_POLYGONS = "extract_polygons", "Extract polygons"
    SOLAR_CALC = "solar_calc", "Solar calculation"
    PERSIST_RESULTS = "persist_results", "Persist results"
    PREPARE_REPORT = "prepare_report", "Prepare report"


# Ordered ``(key, label)`` tuples; the frontend mirrors this list verbatim.
STAGE_SEQUENCE: list[tuple[str, str]] = [(choice.value, choice.label) for choice in StageName]

# Convenience label lookup for services/serializers.
STAGE_LABELS: dict[str, str] = dict(STAGE_SEQUENCE)

# Terminal job states — no further work or cancellation is possible.
TERMINAL_JOB_STATUSES: frozenset[str] = frozenset(
    {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED}
)


class ProcessingJob(BaseModel):
    """Authoritative state of one analysis pipeline run (PostgreSQL, ADR-0002).

    Attributes:
        analysis: The owning analysis (1:1; ownership chain root for perms).
        status: Overall lifecycle state (default ``queued``).
        celery_task_id: Broker task id once enqueued (nullable).
        worker_info: Free-form worker diagnostics (hostname, pid, queue).
        provenance: Reproducibility record (code commit, imagery checksum,
            model name/checksum, preprocessing + inference config, stage
            timings) — DEC-09 / MUST-ADD.
        queued_at: When the job graph was created.
        started_at: When a worker began executing (nullable).
        finished_at: When the job reached a terminal state (nullable).
        error: User-safe error envelope ``{code, message, detail}`` (nullable).
        failure_code: Flat mirror of ``error.code`` for quick querying/filtering
            of failed jobs (nullable).
        cleanup_status: Disposition of temp-file/resource cleanup on terminal
            transitions (:class:`CleanupStatus`).
        cancel_requested: Cooperative cancellation flag checked between stages.
        retry_count: Number of transient retries recorded on the job.
    """

    analysis = models.OneToOneField(
        "analyses.Analysis",
        on_delete=models.CASCADE,
        related_name="job",
    )
    status = models.CharField(
        max_length=16,
        choices=JobStatus.choices,
        default=JobStatus.QUEUED,
    )
    celery_task_id = models.CharField(max_length=255, null=True, blank=True)
    worker_info = models.JSONField(default=dict, blank=True)
    provenance = models.JSONField(default=dict, blank=True)
    queued_at = models.DateTimeField(default=timezone.now)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    error = models.JSONField(null=True, blank=True)
    failure_code = models.CharField(max_length=64, null=True, blank=True)
    cleanup_status = models.CharField(
        max_length=16,
        choices=CleanupStatus.choices,
        default=CleanupStatus.NOT_REQUIRED,
    )
    cancel_requested = models.BooleanField(default=False)
    retry_count = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "processing job"
        verbose_name_plural = "processing jobs"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        """Return a human-readable identifier."""
        return f"ProcessingJob<{self.analysis_id}> ({self.status})"

    @property
    def is_terminal(self) -> bool:
        """Return whether the job is in a terminal state."""
        return self.status in TERMINAL_JOB_STATUSES


class JobStage(BaseModel):
    """A durable per-stage progress record for a :class:`ProcessingJob`.

    Attributes:
        job: The owning job (CASCADE).
        name: Stage machine key (one of :class:`StageName`).
        sequence: 1-based execution order.
        status: Stage lifecycle state (default ``pending``).
        started_at: When the stage began (nullable).
        finished_at: When the stage finished (nullable).
        duration_ms: Wall-clock duration in milliseconds (nullable).
        detail: Small structured summary (counts, ids) — never sensitive data.
    """

    job = models.ForeignKey(
        ProcessingJob,
        on_delete=models.CASCADE,
        related_name="stages",
    )
    name = models.CharField(max_length=32, choices=StageName.choices)
    sequence = models.PositiveIntegerField()
    status = models.CharField(
        max_length=16,
        choices=StageStatus.choices,
        default=StageStatus.PENDING,
    )
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    detail = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "job stage"
        verbose_name_plural = "job stages"
        ordering = ["sequence"]
        constraints = [
            models.UniqueConstraint(
                fields=["job", "name"],
                name="uq_jobstage_job_name",
            ),
        ]

    def __str__(self) -> str:
        """Return a human-readable identifier."""
        return f"JobStage({self.name}={self.status})"
