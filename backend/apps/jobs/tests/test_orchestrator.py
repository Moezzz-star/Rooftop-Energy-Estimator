"""Unit/integration tests for :class:`JobOrchestrator` and stage tracking."""

from __future__ import annotations

from typing import Any

import pytest

from apps.jobs.models import JobStatus, ProcessingJob, StageName, StageStatus
from apps.jobs.services import JobOrchestrator, PipelineRunner
from common.errors import ConflictError, ValidationError

pytestmark = pytest.mark.django_db


class _StubResult:
    """Stand-in for a Celery ``AsyncResult`` carrying a task id."""

    id = "test-task-id"


@pytest.fixture(autouse=True)
def _no_eager_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub the pipeline task's ``delay`` so submit does not run inference here.

    These tests target the orchestrator/stage bookkeeping in isolation; the full
    pipeline is exercised by ``test_pipeline_e2e``.
    """
    from apps.jobs import tasks

    monkeypatch.setattr(tasks.run_analysis_pipeline, "delay", lambda *_a, **_k: _StubResult())


def test_submit_creates_job_and_ten_pending_stages(analysis: Any) -> None:
    """Submit creates one job plus ten pending stages in canonical order."""
    job = JobOrchestrator().submit(analysis)

    assert job.status == JobStatus.QUEUED
    stages = list(job.stages.all())
    assert len(stages) == 10
    assert [s.name for s in stages] == [c.value for c in StageName]
    assert [s.sequence for s in stages] == list(range(1, 11))


def test_submit_is_idempotent(analysis: Any) -> None:
    """A second submit returns the same job without duplicating stages."""
    orchestrator = JobOrchestrator()
    first = orchestrator.submit(analysis)
    second = orchestrator.submit(analysis)

    assert first.pk == second.pk
    assert ProcessingJob.objects.filter(analysis=analysis).count() == 1
    assert first.stages.count() == 10


def test_cancel_sets_cancel_requested(analysis: Any) -> None:
    """Cancelling a non-terminal job flips the cooperative flag."""
    orchestrator = JobOrchestrator()
    job = orchestrator.submit(analysis)

    orchestrator.cancel(job)

    job.refresh_from_db()
    assert job.cancel_requested is True


def test_cancel_terminal_job_conflicts(analysis: Any) -> None:
    """Cancelling a terminal job raises a conflict."""
    orchestrator = JobOrchestrator()
    job = orchestrator.submit(analysis)
    job.status = JobStatus.SUCCEEDED
    job.save(update_fields=["status"])

    with pytest.raises(ConflictError):
        orchestrator.cancel(job)


def test_stage_failure_marks_stage_and_job_failed(analysis: Any) -> None:
    """A stage raising records the stage failed, the job failed, and error."""
    orchestrator = JobOrchestrator()
    job = orchestrator.submit(analysis)

    with (
        pytest.raises(ValidationError),
        orchestrator.stage(job, StageName.VALIDATE_REQUEST.value),
    ):
        raise ValidationError("boom", code="boom_code")

    job.refresh_from_db()
    stage_row = job.stages.get(name=StageName.VALIDATE_REQUEST.value)
    assert stage_row.status == StageStatus.FAILED
    assert stage_row.detail["code"] == "boom_code"
    assert job.status == JobStatus.FAILED
    assert job.error["code"] == "boom_code"
    assert job.finished_at is not None


def test_cooperative_cancellation_skips_remaining_stages(analysis: Any) -> None:
    """A cancel flag observed between stages cancels the job and skips the rest."""
    orchestrator = JobOrchestrator()
    job = orchestrator.submit(analysis)
    orchestrator.cancel(job)

    # Entering a stage after cancellation is requested aborts the run.
    runner = PipelineRunner(orchestrator=orchestrator)
    runner.run(job)

    job.refresh_from_db()
    assert job.status == JobStatus.CANCELLED
    assert set(job.stages.values_list("status", flat=True)) == {StageStatus.SKIPPED}
