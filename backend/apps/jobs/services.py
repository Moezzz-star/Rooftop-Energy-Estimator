"""Orchestration services for the async pipeline (code-architecture §1, §7).

* :class:`JobOrchestrator` owns the job/stage lifecycle: creating the durable
  job graph on submit (idempotently), enqueuing the Celery task, cooperative
  cancellation, and the :meth:`JobOrchestrator.stage` context manager that
  records durable per-stage transitions to PostgreSQL (ADR-0002).
* :class:`PipelineRunner` is the composition root (code-architecture §1): it
  wires the imagery, ml, geospatial and solar services and executes the
  deterministic OFFLINE CPU sample path (ADR-0007) stage by stage, writing real
  :class:`~apps.jobs.models.JobStage` progress (no simulated percentages).

Cross-app services are imported lazily inside methods to avoid import cycles
(``analyses`` submit lazily imports this module). Infrastructure/library errors
(rasterio, keras, pvlib) are wrapped as :class:`common.errors.InfrastructureError`
at the boundary; temp files are cleaned in ``finally``.
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, cast

from celery.exceptions import SoftTimeLimitExceeded
from django.conf import settings
from django.db import (
    IntegrityError,
    InterfaceError,
    OperationalError,
    transaction,
)
from django.utils import timezone

from common.errors import ConflictError, DomainError, InfrastructureError, ValidationError
from common.logging import LogContext, get_logger

from .models import (
    CleanupStatus,
    JobStage,
    JobStatus,
    ProcessingJob,
    StageName,
    StageStatus,
)

logger = get_logger("jobs.orchestrator")

# Documented sample-path defaults (ADR-0007). The bundled sample area sits near
# Stuttgart, Germany (~lon 9.0, lat 48.75); Europe/Berlin is the correct IANA
# zone. Overridable via settings for other deployments.
_DEFAULT_TIMEZONE = getattr(settings, "PIPELINE_DEFAULT_TIMEZONE", "Europe/Berlin")

# Tiling parameters (canonical, CONTEXT.md §1).
_TILE = 256
_STRIDE = 128
_HASH_CHUNK = 1024 * 1024

# Retry policy for the pipeline task (system-arch §3). Kept here so the Celery
# task stays a thin wrapper and the classification/limits are unit-testable.
MAX_PIPELINE_RETRIES = 3
RETRY_BACKOFF_BASE_SECONDS = 5
RETRY_BACKOFF_MAX_SECONDS = 300

# InfrastructureError codes that are deterministic (retrying cannot help) and so
# must fail fast despite being "infrastructure". A missing model artifact will
# not appear on its own between attempts.
_TERMINAL_INFRA_CODES: frozenset[str] = frozenset({"model_not_found"})

# Generic, user-safe fallback message (never leaks internal exception text).
_GENERIC_FAILURE_MESSAGE = "The processing pipeline failed. Please try again or contact support."

# Map stable error codes to friendly, user-safe messages. Internal diagnostics
# are preserved separately in the ``detail`` payload, never in ``message``.
_FRIENDLY_MESSAGES: dict[str, str] = {
    "time_limit_exceeded": "Processing took too long and was stopped. Try a smaller area.",
    "model_not_found": "The building-detection model is unavailable; please contact support.",
    "infrastructure_error": "A processing dependency was temporarily unavailable.",
    "io_error": "A processing dependency was temporarily unavailable.",
}


def is_transient_error(exc: BaseException) -> bool:
    """Classify ``exc`` as a transient (retryable) or terminal failure.

    Transient failures (I/O, DB deadlock, most :class:`InfrastructureError`)
    are worth retrying with backoff; deterministic failures
    (:class:`ValidationError` and other :class:`DomainError` subclasses, or an
    infrastructure error with a terminal code such as ``model_not_found``) must
    fail fast (system-arch §3).

    Args:
        exc: The exception raised by the pipeline.

    Returns:
        ``True`` if the failure is transient and the task should retry.
    """
    if isinstance(exc, ValidationError):
        return False
    if isinstance(exc, InfrastructureError):
        code = str(exc.details.get("code", exc.code))
        if code in _TERMINAL_INFRA_CODES:
            return False
        transient = exc.details.get("transient", True)
        return bool(transient)
    if isinstance(exc, DomainError):
        # ConflictError / NotFoundError / PermissionDeniedError are deterministic.
        return False
    if isinstance(exc, SoftTimeLimitExceeded):
        # A graceful time-limit stop is terminal; retrying would recur.
        return False
    if isinstance(exc, OperationalError | InterfaceError):
        # DB deadlock / dropped connection — retry.
        return True
    return isinstance(exc, OSError)


class _JobCancelledError(Exception):
    """Internal control-flow signal: a cooperative cancellation was observed."""


class JobOrchestrator:
    """Create, track, and cancel processing jobs (PostgreSQL authoritative)."""

    def submit(self, analysis: Any) -> ProcessingJob:
        """Create the job graph for ``analysis`` and enqueue the pipeline.

        Idempotent: an analysis has at most one job (enforced by the OneToOne),
        so a repeat submit returns the existing job without duplicating work.

        Args:
            analysis: The submitted ``analyses.Analysis`` instance.

        Returns:
            The new or pre-existing :class:`ProcessingJob`.
        """
        existing = self._existing_job(analysis)
        if existing is not None:
            logger.info(
                "Submit is idempotent; returning existing job",
                extra={"analysis_id": str(analysis.pk), "job_id": str(existing.pk)},
            )
            return existing

        try:
            with transaction.atomic():
                job = ProcessingJob.objects.create(analysis=analysis)
                self._create_stages(job)
        except IntegrityError:
            # Concurrent submit won the race; return the winner's job.
            existing = self._existing_job(analysis)
            if existing is None:  # pragma: no cover - defensive
                raise
            return existing

        logger.info(
            "Created job graph",
            extra={"analysis_id": str(analysis.pk), "job_id": str(job.pk)},
        )
        self._enqueue(job)
        return job

    def mark_running(self, job: ProcessingJob) -> ProcessingJob:
        """Transition ``job`` (and its analysis) into the running state."""
        job.status = JobStatus.RUNNING
        job.started_at = timezone.now()
        job.save(update_fields=["status", "started_at", "updated_at"])
        self._set_analysis_status(job, "running")
        logger.info("Job started", extra={"job_id": str(job.pk)})
        return job

    def cancel(self, job: ProcessingJob) -> ProcessingJob:
        """Request cooperative cancellation of a non-terminal ``job``.

        Args:
            job: The job to cancel.

        Returns:
            The updated job.

        Raises:
            ConflictError: If the job is already in a terminal state.
        """
        if job.is_terminal:
            raise ConflictError(
                "Job is already in a terminal state and cannot be cancelled.",
                details={"status": job.status},
            )
        job.cancel_requested = True
        job.cleanup_status = CleanupStatus.PENDING
        job.save(update_fields=["cancel_requested", "cleanup_status", "updated_at"])
        self._revoke_task(job)
        logger.info("Cancellation requested", extra={"job_id": str(job.pk)})
        return job

    @staticmethod
    def _revoke_task(job: ProcessingJob) -> None:
        """Best-effort revoke of the Celery task (guarded; never crashes).

        Cooperative cancellation (the ``cancel_requested`` flag checked between
        stages) remains the primary mechanism; revoke only prevents a not-yet-
        started task from running. ``terminate`` is intentionally NOT used so a
        mid-stage worker exits cleanly at the next checkpoint. Safe under eager
        execution / a down broker.
        """
        task_id = job.celery_task_id
        if not task_id:
            return
        # Broad guard on purpose: broker down / eager mode / unknown backend must
        # never turn a best-effort revoke into a request failure.
        try:
            from celery import current_app

            current_app.control.revoke(task_id)
            logger.info(
                "Requested best-effort task revoke",
                extra={"job_id": str(job.pk)},
            )
        except Exception:
            logger.warning(
                "Best-effort task revoke failed (broker unavailable?)",
                extra={"job_id": str(job.pk)},
            )

    @contextmanager
    def stage(self, job: ProcessingJob, name: str) -> Iterator[JobStage]:
        """Run a pipeline stage, recording durable transitions and timings.

        On entry the cooperative cancellation flag is re-read; if set, the
        remaining stages are marked ``skipped``, the job moves to ``cancelled``
        and :class:`_JobCancelledError` is raised to abort the run. On success the
        stage is marked ``succeeded`` with a ``duration_ms``. On any other
        exception the stage is marked ``failed``, the job's ``error`` envelope
        and ``failed`` status are recorded, and the exception is re-raised.

        Args:
            job: The owning job.
            name: The :class:`StageName` machine key.

        Yields:
            The :class:`JobStage` row (handlers may write ``detail``).
        """
        stage_row = job.stages.get(name=name)
        job.refresh_from_db(fields=["cancel_requested", "status"])
        if job.cancel_requested:
            self._mark_cancelled(job)
            raise _JobCancelledError

        self._begin_stage(stage_row)
        log = LogContext(logger, job_id=str(job.pk), analysis_id=str(job.analysis_id))
        log.info("Stage started", extra={"stage": name})
        started = time.monotonic()
        try:
            yield stage_row
        except _JobCancelledError:
            raise
        except Exception as exc:
            self._finish_stage_failed(job, stage_row, started, exc)
            log.error("Stage failed", extra={"stage": name})
            raise
        self._finish_stage_succeeded(stage_row, started)
        log.info("Stage finished", extra={"stage": name})

    # -- internal helpers ---------------------------------------------------

    @staticmethod
    def _create_stages(job: ProcessingJob) -> None:
        """Create the ten pending stage rows in canonical order."""
        rows = [
            JobStage(job=job, name=choice.value, sequence=index, status=StageStatus.PENDING)
            for index, choice in enumerate(StageName, start=1)
        ]
        JobStage.objects.bulk_create(rows)

    @staticmethod
    def _begin_stage(stage_row: JobStage) -> None:
        """Mark ``stage_row`` running with a start timestamp."""
        stage_row.status = StageStatus.RUNNING
        stage_row.started_at = timezone.now()
        stage_row.save(update_fields=["status", "started_at", "updated_at"])

    @staticmethod
    def _finish_stage_succeeded(stage_row: JobStage, started: float) -> None:
        """Mark ``stage_row`` succeeded and record its duration."""
        stage_row.status = StageStatus.SUCCEEDED
        stage_row.finished_at = timezone.now()
        stage_row.duration_ms = int((time.monotonic() - started) * 1000)
        stage_row.save(update_fields=["status", "finished_at", "duration_ms", "updated_at"])

    def _finish_stage_failed(
        self, job: ProcessingJob, stage_row: JobStage, started: float, exc: Exception
    ) -> None:
        """Record the stage failure and fail the job (transactionally)."""
        code, message, detail = self._describe_error(exc)
        with transaction.atomic():
            stage_row.status = StageStatus.FAILED
            stage_row.finished_at = timezone.now()
            stage_row.duration_ms = int((time.monotonic() - started) * 1000)
            stage_row.detail = {"code": code, "message": message}
            stage_row.save(
                update_fields=[
                    "status",
                    "finished_at",
                    "duration_ms",
                    "detail",
                    "updated_at",
                ]
            )
            self._apply_job_failure(job, code, message, detail)
        self._set_analysis_status(job, "failed")

    def mark_failed(self, job: ProcessingJob, exc: BaseException) -> ProcessingJob:
        """Record a terminal failure on ``job`` from ``exc`` (idempotent).

        Used by the Celery task for deterministic failures (and exhausted
        retries) so the failure code + user-safe envelope are always persisted,
        even if the exception bypassed a stage handler. Re-applying an already
        recorded failure is a harmless no-op-equivalent write.

        Args:
            job: The job to fail.
            exc: The terminal exception.

        Returns:
            The updated job.
        """
        code, message, detail = self._describe_error(exc)
        with transaction.atomic():
            self._apply_job_failure(job, code, message, detail)
        self._set_analysis_status(job, "failed")
        logger.info("Recorded terminal job failure", extra={"job_id": str(job.pk)})
        return job

    def register_retry(self, job: ProcessingJob, attempt: int) -> int:
        """Persist a transient-retry attempt and reset the job for a clean rerun.

        Increments and persists :attr:`ProcessingJob.retry_count`, clears the
        transient failure envelope, returns the job/stages to a pending state so
        the next attempt starts cleanly, and returns the exponential-backoff
        countdown (seconds) for :meth:`celery.app.task.Task.retry`.

        Args:
            job: The job being retried.
            attempt: The zero-based retry attempt number (``self.request.retries``).

        Returns:
            The backoff delay in seconds for the next attempt.
        """
        with transaction.atomic():
            job.retry_count = job.retry_count + 1
            job.status = JobStatus.QUEUED
            job.error = None
            job.failure_code = None
            job.finished_at = None
            job.save(
                update_fields=[
                    "retry_count",
                    "status",
                    "error",
                    "failure_code",
                    "finished_at",
                    "updated_at",
                ]
            )
            job.stages.all().update(
                status=StageStatus.PENDING,
                started_at=None,
                finished_at=None,
                duration_ms=None,
                detail={},
            )
        countdown = min(
            RETRY_BACKOFF_BASE_SECONDS * (2**attempt), RETRY_BACKOFF_MAX_SECONDS
        )
        logger.warning(
            "Transient failure; scheduling retry",
            extra={"job_id": str(job.pk)},
        )
        return countdown

    @staticmethod
    def _apply_job_failure(
        job: ProcessingJob, code: str, message: str, detail: dict[str, Any]
    ) -> None:
        """Write the user-safe failure envelope + flat ``failure_code`` on ``job``."""
        job.status = JobStatus.FAILED
        job.finished_at = timezone.now()
        job.error = {"code": code, "message": message, "detail": detail}
        job.failure_code = code
        job.save(
            update_fields=["status", "finished_at", "error", "failure_code", "updated_at"]
        )

    def _mark_cancelled(self, job: ProcessingJob) -> None:
        """Skip remaining stages and move the job/analysis to cancelled."""
        with transaction.atomic():
            job.stages.filter(status__in=[StageStatus.PENDING, StageStatus.RUNNING]).update(
                status=StageStatus.SKIPPED
            )
            job.status = JobStatus.CANCELLED
            job.finished_at = timezone.now()
            job.save(update_fields=["status", "finished_at", "updated_at"])
        self._set_analysis_status(job, "cancelled")
        logger.info("Job cancelled cooperatively", extra={"job_id": str(job.pk)})

    @staticmethod
    def _describe_error(exc: BaseException) -> tuple[str, str, dict[str, Any]]:
        """Return a user-safe ``(code, message, detail)`` for ``exc``.

        The ``message`` is always user-safe (mapped from a friendly table or a
        curated :class:`ValidationError` message) and never contains raw
        exception text. Internal diagnostics (developer message, wrapped cause,
        original type) are preserved separately in ``detail`` for operators.
        """
        if isinstance(exc, SoftTimeLimitExceeded):
            code = "time_limit_exceeded"
            return code, _FRIENDLY_MESSAGES[code], {"internal_type": type(exc).__name__}

        if isinstance(exc, DomainError):
            code = str(exc.details.get("code", exc.code))
            detail: dict[str, Any] = {k: v for k, v in exc.details.items() if k != "code"}
            detail["internal_message"] = exc.message
            cause = exc.__cause__
            if cause is not None:
                detail["internal_cause"] = f"{type(cause).__name__}: {cause}"
            message = _FRIENDLY_MESSAGES.get(code)
            if message is None:
                # ValidationError messages are curated + user-safe (§15); other
                # domain errors fall back to the generic message.
                if isinstance(exc, ValidationError):
                    message = exc.message
                else:
                    message = _GENERIC_FAILURE_MESSAGE
            return code, message, detail

        # Unknown/unexpected exception: never leak its text to the user.
        return "pipeline_error", _GENERIC_FAILURE_MESSAGE, {"internal_type": type(exc).__name__}

    @staticmethod
    def _set_analysis_status(job: ProcessingJob, status_value: str) -> None:
        """Best-effort mirror of terminal/running state onto the analysis."""
        analysis = job.analysis
        analysis.status = status_value
        fields = ["status", "updated_at"]
        if status_value in {"failed", "cancelled"}:
            analysis.completed_at = timezone.now()
            fields.append("completed_at")
        analysis.save(update_fields=fields)

    @staticmethod
    def _existing_job(analysis: Any) -> ProcessingJob | None:
        """Return the analysis's existing job, if any (reverse OneToOne)."""
        try:
            return cast("ProcessingJob", analysis.job)
        except ProcessingJob.DoesNotExist:
            return None

    @staticmethod
    def _enqueue(job: ProcessingJob) -> None:
        """Enqueue the pipeline task and record the broker task id."""
        from .tasks import run_analysis_pipeline

        result = run_analysis_pipeline.delay(str(job.pk))
        task_id = getattr(result, "id", None)
        if task_id:
            job.celery_task_id = str(task_id)
            job.save(update_fields=["celery_task_id", "updated_at"])


class PipelineRunner:
    """Composition root that runs the deterministic offline CPU sample path.

    Dependencies are injected for testability (no hard singletons); real
    services are constructed lazily on first use so importing this module never
    pulls in TensorFlow/rasterio. ``run`` executes the ten durable stages and
    writes real :class:`JobStage` progress via the orchestrator.
    """

    def __init__(
        self,
        *,
        orchestrator: JobOrchestrator | None = None,
        imagery_service: Any | None = None,
        imagery_provider: Any | None = None,
        model_registry: Any | None = None,
        vectorization_service: Any | None = None,
        persistence_service: Any | None = None,
        solar_service: Any | None = None,
        model_loader: Callable[[str], Any] | None = None,
        predictor_factory: Callable[[Any, Any], Any] | None = None,
    ) -> None:
        """Initialize the runner, deferring heavy imports to first use."""
        self._orchestrator = orchestrator or JobOrchestrator()
        self._imagery_service = imagery_service
        self._imagery_provider = imagery_provider
        self._model_registry = model_registry
        self._vectorization_service = vectorization_service
        self._persistence_service = persistence_service
        self._solar_service = solar_service
        self._model_loader = model_loader
        self._predictor_factory = predictor_factory

    def run(self, job: ProcessingJob) -> ProcessingJob:
        """Execute the pipeline for ``job``, stage by stage.

        Args:
            job: The running :class:`ProcessingJob` (already marked running).

        Returns:
            The job (terminal state persisted by the stage/orchestrator).
        """
        ctx: dict[str, Any] = {
            "job": job,
            "analysis": job.analysis,
            "temp_files": [],
            "provenance": self._initial_provenance(job.analysis),
        }
        # Idempotency-on-retry (system-arch §3): a run recomputes everything, so
        # clear any partial Building/SolarEstimate/RoofGeometry rows from a prior
        # attempt up front. SolarEstimate + RoofGeometry cascade from Building.
        self._reset_prior_results(job.analysis)
        handlers: list[tuple[str, Callable[[dict[str, Any], JobStage], None]]] = [
            (StageName.VALIDATE_REQUEST.value, self._validate_request),
            (StageName.LOAD_IMAGERY.value, self._load_imagery),
            (StageName.VALIDATE_RASTER.value, self._validate_raster),
            (StageName.TILE.value, self._tile),
            (StageName.SEGMENT.value, self._segment),
            (StageName.POSTPROCESS_MASK.value, self._postprocess_mask),
            (StageName.EXTRACT_POLYGONS.value, self._extract_polygons),
            (StageName.SOLAR_CALC.value, self._solar_calc),
            (StageName.PERSIST_RESULTS.value, self._persist_results),
            (StageName.PREPARE_REPORT.value, self._prepare_report),
        ]
        try:
            for name, handler in handlers:
                with self._orchestrator.stage(job, name) as stage_row:
                    handler(ctx, stage_row)
        except _JobCancelledError:
            logger.info("Pipeline cancelled", extra={"job_id": str(job.pk)})
        finally:
            self._cleanup(ctx)
        return job

    # -- stage handlers -----------------------------------------------------

    def _validate_request(self, ctx: dict[str, Any], stage_row: JobStage) -> None:
        """Stage 1: verify inputs, register bundled sample if needed."""
        from apps.analyses.services import AssumptionResolver

        analysis = ctx["analysis"]
        area = analysis.areas.first()
        if area is None:
            raise self._fail("no_analysis_area", "Analysis has no area of interest.")
        assumption = getattr(analysis, "assumption", None)
        if assumption is None:
            raise self._fail("no_assumptions", "Analysis has no assumptions.")

        asset = analysis.imagery_assets.first()
        if asset is None:
            asset = self.imagery_service.register_bundled_sample(analysis)

        ctx["area"] = area
        ctx["assumption"] = assumption
        ctx["imagery_asset"] = asset
        ctx["assumptions"] = AssumptionResolver().resolve(analysis)
        stage_row.detail = {
            "area_id": str(area.pk),
            "imagery_asset_id": str(asset.pk),
            "registered_sample": analysis.imagery_assets.count() == 1,
        }

    def _load_imagery(self, ctx: dict[str, Any], stage_row: JobStage) -> None:
        """Stage 2: read raster metadata (crs, transform, bounds, resolution)."""
        from affine import Affine

        asset = ctx["imagery_asset"]
        metadata = self.imagery_provider.read_metadata(asset.storage_key)
        ctx["metadata"] = metadata
        ctx["crs"] = metadata.crs
        ctx["transform"] = Affine(*metadata.transform)
        ctx["provenance"]["imagery_checksum"] = metadata.checksum
        stage_row.detail = {
            "crs": metadata.crs,
            "bands": metadata.bands,
            "width": metadata.width,
            "height": metadata.height,
            "resolution_m": metadata.resolution_m,
        }

    def _validate_raster(self, ctx: dict[str, Any], stage_row: JobStage) -> None:
        """Stage 3: fail fast unless CRS/bands/transform are usable."""
        import math

        metadata = ctx["metadata"]
        if not metadata.crs:
            raise self._fail("missing_crs", "Raster has no CRS; UTM area is impossible.")
        if metadata.bands < 3:
            raise self._fail(
                "insufficient_bands",
                "Raster has fewer than 3 bands; RGB inference is impossible.",
            )
        if not all(math.isfinite(coeff) for coeff in metadata.transform):
            raise self._fail("bad_transform", "Raster transform is not finite.")
        if metadata.transform[0] == 0 or metadata.transform[4] == 0:
            raise self._fail("bad_transform", "Raster transform has zero pixel size.")
        stage_row.detail = {"crs": metadata.crs, "bands": metadata.bands}

    def _tile(self, ctx: dict[str, Any], stage_row: JobStage) -> None:
        """Stage 4: windowed raster read + percentile normalize to RGB."""
        from ml.preprocessing.normalize import percentile_normalize

        metadata = ctx["metadata"]
        window = self._full_window(metadata.width, metadata.height)
        asset = ctx["imagery_asset"]
        try:
            raw = self.imagery_provider.open_window(asset.storage_key, window)
        except InfrastructureError:
            raise
        except Exception as exc:  # pragma: no cover - provider maps most errors
            raise InfrastructureError("Windowed raster read failed.") from exc
        rgb = percentile_normalize(raw, pmin=2.0, pmax=98.0)
        ctx["rgb"] = rgb
        tiler = self._build_tiler()
        ctx["tiler"] = tiler
        stage_row.detail = {
            "shape": [int(rgb.shape[0]), int(rgb.shape[1])],
            "tile": _TILE,
            "stride": _STRIDE,
            "tiles": len(tiler.tiles(max(rgb.shape[0], _TILE), max(rgb.shape[1], _TILE))),
        }

    def _segment(self, ctx: dict[str, Any], stage_row: JobStage) -> None:
        """Stage 5: load model (CI fallback) and run U-Net inference."""
        from ml.inference.predictor import ModelNotFoundError

        model_path, source, model_version = self._resolve_model()
        try:
            model = self.model_loader(model_path)
            predictor = self.predictor_factory(model, ctx["tiler"])
            prob = predictor.predict_prob(ctx["rgb"])
        except ModelNotFoundError as exc:
            raise InfrastructureError(
                "Segmentation model artifact is unavailable.",
                details={"code": "model_not_found"},
            ) from exc
        except Exception as exc:  # keras/tf failures
            raise InfrastructureError("Model inference failed.") from exc
        ctx["prob"] = prob
        checksum = self._sha256_file(model_path)
        ctx["provenance"]["model_name"] = model_version.name
        ctx["provenance"]["model_version"] = model_version.version
        ctx["provenance"]["model_checksum"] = checksum
        ctx["provenance"]["model_source"] = source
        stage_row.detail = {
            "model_name": model_version.name,
            "model_source": source,
            "prob_max": float(prob.max()) if prob.size else 0.0,
        }

    def _postprocess_mask(self, ctx: dict[str, Any], stage_row: JobStage) -> None:
        """Stage 6: threshold + morphological cleanup into a boolean mask."""
        from ml.inference.postprocess import cleanup_mask

        mask = cleanup_mask(ctx["prob"], threshold=0.2, min_object=8, min_hole=8)
        ctx["mask"] = mask
        stage_row.detail = {"foreground_px": int(mask.sum())}

    def _extract_polygons(self, ctx: dict[str, Any], stage_row: JobStage) -> None:
        """Stage 7: vectorize the mask into unsaved Building instances."""
        buildings = self.vectorization_service.mask_to_features(
            ctx["mask"], ctx["transform"], ctx["crs"], prob=ctx["prob"]
        )
        ctx["buildings"] = buildings
        stage_row.detail = {"buildings": len(buildings)}

    def _solar_calc(self, ctx: dict[str, Any], stage_row: JobStage) -> None:
        """Stage 8: resolve a fixed-orientation solar location per building.

        No DB writes here (buildings are not yet persisted); the per-building
        estimates are computed and saved in stage 9 right after persistence so
        the ``SolarEstimate.building`` FK is valid.
        """
        from apps.solar.services import SolarLocation

        buildings = ctx["buildings"]
        locations: list[SolarLocation] = []
        for building in buildings:
            centroid = building.centroid
            locations.append(
                SolarLocation(
                    timezone=_DEFAULT_TIMEZONE,
                    latitude=float(centroid.y),
                    longitude=float(centroid.x),
                )
            )
        ctx["locations"] = locations
        stage_row.detail = {"buildings": len(buildings), "timezone": _DEFAULT_TIMEZONE}

    def _persist_results(self, ctx: dict[str, Any], stage_row: JobStage) -> None:
        """Stage 9: persist buildings, then compute + save solar estimates."""
        analysis = ctx["analysis"]
        buildings = ctx["buildings"]
        assumption = ctx["assumption"]
        locations = ctx["locations"]
        total_annual_kwh = 0.0
        with transaction.atomic():
            saved = self.persistence_service.persist(analysis, buildings)
            for building, location in zip(saved, locations, strict=False):
                estimate = self.solar_service.estimate(building, assumption, location)
                total_annual_kwh += float(estimate.annual_kwh)
        ctx["building_count"] = len(saved)
        ctx["total_annual_kwh"] = total_annual_kwh
        stage_row.detail = {
            "buildings_persisted": len(saved),
            "total_annual_kwh": round(total_annual_kwh, 3),
        }

    def _prepare_report(self, ctx: dict[str, Any], stage_row: JobStage) -> None:
        """Stage 10 (STUB): finalize analysis + job; report deferred to exports."""
        from apps.analyses.models import AnalysisStatus

        job = ctx["job"]
        analysis = ctx["analysis"]
        self._finalize_snapshot(ctx)
        analysis.status = AnalysisStatus.COMPLETED
        analysis.completed_at = timezone.now()
        # TODO(analyses): expose AnalysisService.complete() to own this transition.
        analysis.save(update_fields=["status", "completed_at", "snapshot", "updated_at"])
        job.provenance = self._final_provenance(ctx)
        job.status = JobStatus.SUCCEEDED
        job.finished_at = timezone.now()
        job.save(update_fields=["provenance", "status", "finished_at", "updated_at"])
        # TODO(exports): optionally kick apps.exports.tasks.generate_export here.
        stage_row.detail = {
            "building_count": ctx.get("building_count", 0),
            "total_annual_kwh": round(ctx.get("total_annual_kwh", 0.0), 3),
            "report": "deferred_to_exports",
        }

    # -- lazily-constructed dependencies ------------------------------------

    @property
    def imagery_service(self) -> Any:
        """Return the injected or default :class:`ImageryService`."""
        if self._imagery_service is None:
            from apps.imagery.services import ImageryService

            self._imagery_service = ImageryService()
        return self._imagery_service

    @property
    def imagery_provider(self) -> Any:
        """Return the injected or default :class:`UploadedRasterProvider`."""
        if self._imagery_provider is None:
            from apps.imagery.providers import UploadedRasterProvider

            self._imagery_provider = UploadedRasterProvider()
        return self._imagery_provider

    @property
    def model_registry(self) -> Any:
        """Return the injected or default :class:`ModelRegistryService`."""
        if self._model_registry is None:
            from apps.ml_models.services import ModelRegistryService

            self._model_registry = ModelRegistryService()
        return self._model_registry

    @property
    def vectorization_service(self) -> Any:
        """Return the injected or default :class:`VectorizationService`."""
        if self._vectorization_service is None:
            from apps.geospatial.services import VectorizationService

            self._vectorization_service = VectorizationService()
        return self._vectorization_service

    @property
    def persistence_service(self) -> Any:
        """Return the injected or default :class:`BuildingPersistenceService`."""
        if self._persistence_service is None:
            from apps.geospatial.services import BuildingPersistenceService

            self._persistence_service = BuildingPersistenceService()
        return self._persistence_service

    @property
    def solar_service(self) -> Any:
        """Return the injected or default :class:`SolarEstimationService`."""
        if self._solar_service is None:
            from apps.solar.services import SolarEstimationService

            self._solar_service = SolarEstimationService()
        return self._solar_service

    @property
    def model_loader(self) -> Callable[[str], Any]:
        """Return the injected or default Keras model loader."""
        if self._model_loader is None:
            from ml.inference.predictor import load_keras_model

            self._model_loader = load_keras_model
        return self._model_loader

    @property
    def predictor_factory(self) -> Callable[[Any, Any], Any]:
        """Return the injected or default :class:`UNetPredictor` factory."""
        if self._predictor_factory is None:
            from ml.inference.predictor import UNetPredictor

            def _factory(model: Any, tiler: Any) -> Any:
                return UNetPredictor(model, tiler, batch_size=16)

            self._predictor_factory = _factory
        return self._predictor_factory

    # -- internal helpers ---------------------------------------------------

    @staticmethod
    def _build_tiler() -> Any:
        """Construct the canonical tiler (tile=256, stride=128)."""
        from ml.preprocessing.tiling import Tiler

        return Tiler(tile=_TILE, stride=_STRIDE)

    @staticmethod
    def _full_window(width: int, height: int) -> Any:
        """Return a window covering the whole (small sample) raster.

        The sample raster is small enough to read in a single window; the
        windowed-read API is used to keep the same bounded-memory path as
        production (MUST-ADD: never a naive full-raster load helper).
        """
        from rasterio.windows import Window

        return Window(0, 0, width, height)

    def _resolve_model(self) -> tuple[str, str, Any]:
        """Return ``(model_path, source, model_version)`` with CI fallback.

        Prefers ``settings.ML_MODEL_PATH`` (may be the real 90MB model). When it
        is absent, falls back to the tiny CI model so the pipeline is runnable
        offline (DEC-05). Which model was used is recorded in provenance.
        """
        model_version = self.model_registry.active()
        configured = getattr(settings, "ML_MODEL_PATH", "") or ""
        if configured and Path(configured).is_file():
            return configured, "configured", model_version
        ci_model = Path(settings.BASE_DIR).parent / "ml" / "tests" / "fixtures" / "ci_unet.keras"
        if ci_model.is_file():
            logger.warning("Configured model absent; falling back to CI model (DEC-05)")
            return str(ci_model), "ci_fallback", model_version
        # Neither present: let the loader raise ModelNotFoundError with guidance.
        return configured, "configured", model_version

    @staticmethod
    def _sha256_file(path: str) -> str:
        """Return the streaming SHA-256 of ``path`` (empty string on failure)."""
        if not path or not Path(path).is_file():
            return ""
        digest = hashlib.sha256()
        try:
            with Path(path).open("rb") as handle:
                for chunk in iter(lambda: handle.read(_HASH_CHUNK), b""):
                    digest.update(chunk)
        except OSError:  # pragma: no cover - provenance is best-effort
            return ""
        return digest.hexdigest()

    @staticmethod
    def _initial_provenance(analysis: Any) -> dict[str, Any]:
        """Seed provenance from the analysis snapshot + canonical configs."""
        from dataclasses import asdict

        from ml.configs import DEFAULT_INFERENCE, DEFAULT_PREPROCESS, DEFAULT_TILING

        snapshot = analysis.snapshot or {}
        return {
            "code_commit": snapshot.get("code_commit", "unknown"),
            "preprocess": asdict(DEFAULT_PREPROCESS),
            "tiling": asdict(DEFAULT_TILING),
            "inference": asdict(DEFAULT_INFERENCE),
        }

    @staticmethod
    def _final_provenance(ctx: dict[str, Any]) -> dict[str, Any]:
        """Attach per-stage timings to the accumulated provenance."""
        job = ctx["job"]
        provenance = dict(ctx["provenance"])
        provenance["stage_timings_ms"] = {
            row.name: row.duration_ms for row in job.stages.all() if row.duration_ms is not None
        }
        return provenance

    def _finalize_snapshot(self, ctx: dict[str, Any]) -> None:
        """Freeze imagery metadata into the analysis snapshot (DEC-09)."""
        analysis = ctx["analysis"]
        metadata = ctx.get("metadata")
        snapshot = dict(analysis.snapshot or {})
        if metadata is not None:
            snapshot["imagery"] = {
                "crs": metadata.crs,
                "bounds": metadata.bounds,
                "resolution_m": metadata.resolution_m,
                "bands": metadata.bands,
                "checksum": metadata.checksum,
            }
        analysis.snapshot = snapshot

    @staticmethod
    def _reset_prior_results(analysis: Any) -> None:
        """Delete partial results from a prior attempt (idempotent rerun).

        Removing :class:`~apps.geospatial.models.Building` rows cascades to their
        :class:`SolarEstimate` and :class:`RoofGeometry` children, so a retried
        run never duplicates buildings/estimates for the analysis.
        """
        from apps.geospatial.models import Building

        deleted, _ = Building.objects.filter(analysis=analysis).delete()
        if deleted:
            logger.info(
                "Cleared prior partial results before rerun",
                extra={"analysis_id": str(analysis.pk)},
            )

    @staticmethod
    def _cleanup(ctx: dict[str, Any]) -> None:
        """Remove temp files created during the run and record cleanup status.

        Runs in ``finally`` for every terminal transition (success, failure,
        cancellation), so the job's :attr:`ProcessingJob.cleanup_status` always
        reflects whether resource cleanup completed.
        """
        ok = True
        for temp in ctx.get("temp_files", []):
            try:
                Path(temp).unlink(missing_ok=True)
            except OSError:
                ok = False
                logger.warning("Failed to remove temp file during cleanup")
        job = ctx.get("job")
        if job is None:  # pragma: no cover - job is always present
            return
        job.cleanup_status = CleanupStatus.DONE if ok else CleanupStatus.FAILED
        job.save(update_fields=["cleanup_status", "updated_at"])

    @staticmethod
    def _fail(code: str, message: str) -> DomainError:
        """Return a deterministic validation failure (fail fast)."""
        from common.errors import ValidationError

        return ValidationError(message, code=code)
