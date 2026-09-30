"""Integration tests for the jobs HTTP endpoints (§4 #14, #15)."""

from __future__ import annotations

from typing import Any

import pytest
from rest_framework.test import APIClient

from apps.jobs.services import JobOrchestrator

pytestmark = pytest.mark.django_db


class _StubResult:
    """Stand-in for a Celery ``AsyncResult`` carrying a task id."""

    id = "test-task-id"


@pytest.fixture(autouse=True)
def _no_eager_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub the pipeline task's ``delay`` so submit does not run inference here."""
    from apps.jobs import tasks

    monkeypatch.setattr(tasks.run_analysis_pipeline, "delay", lambda *_a, **_k: _StubResult())


def test_job_detail_returns_status_and_stages(auth_client: APIClient, analysis: Any) -> None:
    """GET job returns the job with its ten ordered stages (#14)."""
    JobOrchestrator().submit(analysis)

    response = auth_client.get(f"/api/v1/analyses/{analysis.pk}/job/")

    assert response.status_code == 200
    assert response.data["status"] == "queued"
    assert len(response.data["stages"]) == 10
    assert response.data["stages"][0]["name"] == "validate_request"


def test_job_detail_owner_scoped(api_client: APIClient, user_factory: Any, analysis: Any) -> None:
    """A non-owner cannot read another user's job (#14)."""
    JobOrchestrator().submit(analysis)
    from rest_framework_simplejwt.tokens import RefreshToken

    other = user_factory()
    token = RefreshToken.for_user(other)
    access = token.access_token  # type: ignore[attr-defined]  # simplejwt dynamic attr
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = api_client.get(f"/api/v1/analyses/{analysis.pk}/job/")
    assert response.status_code == 404


def test_job_cancel_sets_flag(auth_client: APIClient, analysis: Any) -> None:
    """POST cancel flips the cooperative cancellation flag (#15)."""
    JobOrchestrator().submit(analysis)

    response = auth_client.post(f"/api/v1/analyses/{analysis.pk}/job/cancel/")

    assert response.status_code == 202
    assert response.data["cancel_requested"] is True
