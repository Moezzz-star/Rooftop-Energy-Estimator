"""Robustness tests for the jobs pipeline (Phase 5 §13/§17).

Covers the retry classification + bounded transient retries, Celery soft
time-limit handling, cancellation cleanup bookkeeping, user-safe failure
messages, and idempotent re-runs. The full happy path lives in
``test_pipeline_e2e``; here the pipeline / stage handlers are monkeypatched to
raise the specific exceptions under test (CELERY_TASK_ALWAYS_EAGER is set by
``config.settings.test``).
"""

from __future__ import annotations

from typing import Any

import pytest
from celery.exceptions import SoftTimeLimitExceeded
from django.contrib.gis.geos import Point, Polygon

from apps.jobs.models import (
    CleanupStatus,
    JobStatus,
    ProcessingJob,
    StageName,
    StageStatus,
)
from apps.jobs.services import (
    MAX_PIPELINE_RETRIES,
    RETRY_BACKOFF_BASE_SECONDS,
    JobOrchestrator,
    PipelineRunner,
    is_transient_error,
)
from apps.jobs.tasks import run_analysis_pipeline
from common.errors import (
    ConflictError,
    InfrastructureError,
    NotFoundError,
    ValidationError,
)

pytestmark = pytest.mark.django_db


class _StubResult:
    """Stand-in for a Celery ``AsyncResult`` carrying a task id."""

    id = "test-task-id"


class _RetrySignal(Exception):
    """Sentinel raised by a fake ``self.retry`` to avoid real eager recursion."""


@pytest.fixture(autouse=True)
def _no_eager_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub the pipeline task's ``delay`` so ``submit`` never runs inference."""
    monkeypatch.setattr(
        run_analysis_pipeline, "delay", lambda *_a, **_k: _StubResult()
    )


def _submitted_job(analysis: Any) -> ProcessingJob:
    """Create a queued job with its ten pending stages for ``analysis``."""
    return JobOrchestrator().submit(analysis)


# -- C1: retry classification ------------------------------------------------


def test_is_transient_error_classification() -> None:
    """Transient vs terminal classification follows system-arch §3."""
    assert is_transient_error(InfrastructureError("io")) is True
    assert is_transient_error(OSError("disk")) is True
    assert is_transient_error(ValidationError("bad")) is False
    assert is_transient_error(ConflictError("dup")) is False
    assert is_transient_error(NotFoundError("gone")) is False
    assert is_transient_error(SoftTimeLimitExceeded()) is False
    # A missing model artifact is deterministic even though it is "infrastructure".
    terminal_infra = InfrastructureError("no model", details={"code": "model_not_found"})
    assert is_transient_error(terminal_infra) is False
    # An infra error can opt out of retry via an explicit flag.
    flagged = InfrastructureError("perm", details={"transient": False})
    assert is_transient_error(flagged) is False


# -- C1: retries in the task -------------------------------------------------


def test_transient_failure_triggers_retry_and_increments_retry_count(
    analysis: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A transient pipeline failure retries with backoff and bumps retry_count."""
    job = _submitted_job(analysis)

    def _boom(_self: Any, _job: Any) -> None:
        raise InfrastructureError("windowed read failed")

    captured: dict[str, Any] = {}

    def _fake_retry(*, exc: BaseException, countdown: int) -> None:
        captured["exc"] = exc
        captured["countdown"] = countdown
        raise _RetrySignal

    monkeypatch.setattr(PipelineRunner, "run", _boom)
    monkeypatch.setattr(run_analysis_pipeline, "retry", _fake_retry)

    with pytest.raises(_RetrySignal):
        run_analysis_pipeline.apply(args=[str(job.pk)])

    job.refresh_from_db()
    assert job.retry_count == 1
    assert job.status == JobStatus.QUEUED  # reset for the next attempt
    assert job.error is None
    assert captured["countdown"] == RETRY_BACKOFF_BASE_SECONDS  # base * 2**0
    assert isinstance(captured["exc"], InfrastructureError)
    # Stages were reset to pending so the retry starts cleanly.
    assert set(job.stages.values_list("status", flat=True)) == {StageStatus.PENDING}


def test_deterministic_validation_error_does_not_retry(
    analysis: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A deterministic ValidationError fails fast with a recorded failure_code."""
    job = _submitted_job(analysis)

    def _boom(_self: Any, _job: Any) -> None:
        raise ValidationError("Analysis has no area of interest.", code="no_analysis_area")

    def _fail_retry(**_kwargs: Any) -> None:
        raise AssertionError("retry must not be called for deterministic failures")

    monkeypatch.setattr(PipelineRunner, "run", _boom)
    monkeypatch.setattr(run_analysis_pipeline, "retry", _fail_retry)

    with pytest.raises(ValidationError):
        run_analysis_pipeline.apply(args=[str(job.pk)])

    job.refresh_from_db()
    assert job.retry_count == 0
    assert job.status == JobStatus.FAILED
    assert job.failure_code == "no_analysis_area"
    assert job.error["code"] == "no_analysis_area"


# -- C2: soft time limit -----------------------------------------------------


def test_soft_time_limit_marks_stage_and_job_failed(
    analysis: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SoftTimeLimitExceeded is handled: stage/job failed + cleanup recorded."""
    orchestrator = JobOrchestrator()
    job = orchestrator.submit(analysis)
    runner = PipelineRunner(orchestrator=orchestrator)

    def _timeout(_ctx: Any, _stage_row: Any) -> None:
        raise SoftTimeLimitExceeded

    monkeypatch.setattr(runner, "_validate_request", _timeout)

    with pytest.raises(SoftTimeLimitExceeded):
        runner.run(job)

    job.refresh_from_db()
    stage = job.stages.get(name=StageName.VALIDATE_REQUEST.value)
    assert stage.status == StageStatus.FAILED
    assert stage.detail["code"] == "time_limit_exceeded"
    assert job.status == JobStatus.FAILED
    assert job.failure_code == "time_limit_exceeded"
    assert job.cleanup_status == CleanupStatus.DONE
    # The user-facing message must not leak the raw exception type.
    assert "SoftTimeLimitExceeded" not in job.error["message"]


# -- C3: cancellation completeness -------------------------------------------


def test_cancel_sets_cleanup_status_and_skips_remaining_stages(analysis: Any) -> None:
    """Cancel flags cleanup pending; the run skips stages and finishes cleanup."""
    orchestrator = JobOrchestrator()
    job = orchestrator.submit(analysis)

    orchestrator.cancel(job)
    job.refresh_from_db()
    assert job.cancel_requested is True
    assert job.cleanup_status == CleanupStatus.PENDING

    PipelineRunner(orchestrator=orchestrator).run(job)

    job.refresh_from_db()
    assert job.status == JobStatus.CANCELLED
    assert set(job.stages.values_list("status", flat=True)) == {StageStatus.SKIPPED}
    assert job.cleanup_status == CleanupStatus.DONE


def test_cancel_terminal_job_conflicts(analysis: Any) -> None:
    """Cancelling an already-terminal job raises a conflict (no revoke)."""
    orchestrator = JobOrchestrator()
    job = orchestrator.submit(analysis)
    job.status = JobStatus.SUCCEEDED
    job.save(update_fields=["status"])

    with pytest.raises(ConflictError):
        orchestrator.cancel(job)


# -- C4: user-safe failure messages ------------------------------------------


def test_failure_message_is_user_safe_but_keeps_internal_detail(analysis: Any) -> None:
    """The user message is friendly; internal diagnostics live in ``detail``."""
    orchestrator = JobOrchestrator()
    job = orchestrator.submit(analysis)

    try:
        raise ValueError("psycopg: connection refused at 10.0.0.5:5432")
    except ValueError as exc:
        wrapped = InfrastructureError("Windowed raster read failed.")
        wrapped.__cause__ = exc
        orchestrator.mark_failed(job, wrapped)

    job.refresh_from_db()
    message = job.error["message"]
    detail = job.error["detail"]
    # No raw internals in the user-facing message.
    assert "psycopg" not in message
    assert "10.0.0.5" not in message
    assert "Windowed raster read failed." not in message
    # Internals are preserved for operators.
    assert detail["internal_message"] == "Windowed raster read failed."
    assert "psycopg" in detail["internal_cause"]
    assert job.failure_code == "infrastructure_error"


# -- C1 idempotency: re-run does not duplicate buildings ---------------------


def test_reset_prior_results_clears_buildings(analysis: Any) -> None:
    """A rerun clears prior Building rows so retries do not duplicate results."""
    from apps.geospatial.models import Building

    poly = Polygon(((0, 0), (0, 1), (1, 1), (1, 0), (0, 0)), srid=4326)
    Building.objects.create(
        analysis=analysis,
        confidence=0.9,
        area_m2=100.0,
        index=0,
        geometry=poly,
        centroid=Point(0.5, 0.5, srid=4326),
    )
    assert Building.objects.filter(analysis=analysis).count() == 1

    PipelineRunner()._reset_prior_results(analysis)

    assert Building.objects.filter(analysis=analysis).count() == 0
