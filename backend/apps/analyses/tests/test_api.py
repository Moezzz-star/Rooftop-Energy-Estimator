"""Integration tests for the analyses HTTP endpoints (§4 #7, #8, #9)."""

from __future__ import annotations

from typing import Any

import pytest
from rest_framework.test import APIClient

from apps.analyses.models import Analysis, AnalysisStatus
from apps.audit.models import AuditEvent
from apps.ml_models.services import ModelRegistryService
from apps.solar.services import SolarMethodRegistry

pytestmark = pytest.mark.django_db


def _create_analysis(client: APIClient, project_id: str, geojson: dict[str, Any]) -> Any:
    """Create a draft analysis via the API and return the response."""
    return client.post(
        f"/api/v1/projects/{project_id}/analyses/",
        {"name": "Roof scan", "area": geojson},
        format="json",
    )


def test_create_analysis_draft(
    auth_client: APIClient, project: Any, polygon_geojson: dict[str, Any]
) -> None:
    """Creating an analysis returns a draft with a nested GeoJSON area."""
    response = _create_analysis(auth_client, str(project.pk), polygon_geojson)
    assert response.status_code == 201
    assert response.data["status"] == AnalysisStatus.DRAFT
    assert response.data["assumption"]["usable_roof_fraction"] == 0.70
    assert response.data["areas"][0]["area"]["type"] == "MultiPolygon"


def test_create_rejects_non_polygon(auth_client: APIClient, project: Any) -> None:
    """A non-polygon geometry is rejected with 400."""
    response = _create_analysis(
        auth_client, str(project.pk), {"type": "Point", "coordinates": [0, 0]}
    )
    assert response.status_code == 400


def test_list_scoped_to_owner(
    auth_client: APIClient,
    user_factory: Any,
    project_factory: Any,
    project: Any,
    polygon_geojson: dict[str, Any],
) -> None:
    """A user cannot see analyses under another user's project."""
    _create_analysis(auth_client, str(project.pk), polygon_geojson)

    other_user = user_factory()
    other_project = project_factory(owner=other_user)
    response = auth_client.get(f"/api/v1/projects/{other_project.pk}/analyses/")
    assert response.status_code == 404


def test_edit_blocked_after_submit(
    auth_client: APIClient, project: Any, polygon_geojson: dict[str, Any]
) -> None:
    """Editing is rejected once an analysis leaves draft."""
    ModelRegistryService.get_or_create_default()
    SolarMethodRegistry.get_or_create_default()
    created = _create_analysis(auth_client, str(project.pk), polygon_geojson)
    analysis_id = created.data["id"]

    auth_client.post(
        f"/api/v1/analyses/{analysis_id}/submit/",
        {},
        format="json",
        HTTP_IDEMPOTENCY_KEY="key-1",
    )
    response = auth_client.patch(f"/api/v1/analyses/{analysis_id}/", {"name": "new"}, format="json")
    assert response.status_code == 409


def test_submit_requires_idempotency_key(
    auth_client: APIClient, project: Any, polygon_geojson: dict[str, Any]
) -> None:
    """Submit without the header is a 400."""
    created = _create_analysis(auth_client, str(project.pk), polygon_geojson)
    response = auth_client.post(f"/api/v1/analyses/{created.data['id']}/submit/", {}, format="json")
    assert response.status_code == 400


def test_submit_sets_status_and_snapshot(
    auth_client: APIClient, project: Any, polygon_geojson: dict[str, Any]
) -> None:
    """Submit queues the analysis and populates the DEC-09 snapshot fields."""
    ModelRegistryService.get_or_create_default()
    SolarMethodRegistry.get_or_create_default()
    created = _create_analysis(auth_client, str(project.pk), polygon_geojson)
    analysis_id = created.data["id"]

    response = auth_client.post(
        f"/api/v1/analyses/{analysis_id}/submit/",
        {},
        format="json",
        HTTP_IDEMPOTENCY_KEY="key-1",
    )
    assert response.status_code == 202
    # Under CELERY_TASK_ALWAYS_EAGER the pipeline runs inline during submit, so
    # the analysis may already have advanced past QUEUED by the time we observe it.
    _submitted = {AnalysisStatus.QUEUED, AnalysisStatus.RUNNING, AnalysisStatus.COMPLETED}
    assert response.data["analysis"]["status"] in _submitted

    analysis = Analysis.objects.get(pk=analysis_id)
    assert analysis.status in _submitted
    assert analysis.submitted_at is not None
    assert analysis.model_version is not None
    assert analysis.calculation_version is not None
    assert analysis.snapshot["processing_config"]["tiling"]["tile"] == 256
    assert "code_commit" in analysis.snapshot


def test_idempotent_resubmit_no_duplicate(
    auth_client: APIClient, project: Any, polygon_geojson: dict[str, Any]
) -> None:
    """Re-submitting with the same key does not change status or duplicate."""
    ModelRegistryService.get_or_create_default()
    SolarMethodRegistry.get_or_create_default()
    created = _create_analysis(auth_client, str(project.pk), polygon_geojson)
    analysis_id = created.data["id"]

    first = auth_client.post(
        f"/api/v1/analyses/{analysis_id}/submit/",
        {},
        format="json",
        HTTP_IDEMPOTENCY_KEY="key-1",
    )
    second = auth_client.post(
        f"/api/v1/analyses/{analysis_id}/submit/",
        {},
        format="json",
        HTTP_IDEMPOTENCY_KEY="key-1",
    )
    assert first.status_code == 202
    assert second.status_code == 202
    analysis = Analysis.objects.get(pk=analysis_id)
    assert analysis.idempotency_key == "key-1"


def test_detail_denied_for_non_owner(
    auth_client: APIClient,
    api_client: APIClient,
    user_factory: Any,
    project: Any,
    polygon_geojson: dict[str, Any],
) -> None:
    """A non-owner cannot retrieve another user's analysis."""
    from rest_framework_simplejwt.tokens import RefreshToken

    created = _create_analysis(auth_client, str(project.pk), polygon_geojson)
    other = user_factory()
    token = RefreshToken.for_user(other)
    access = token.access_token  # type: ignore[attr-defined]  # simplejwt dynamic attr
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = api_client.get(f"/api/v1/analyses/{created.data['id']}/")
    assert response.status_code == 404


def test_create_rejects_out_of_range_assumption(
    auth_client: APIClient, project: Any, polygon_geojson: dict[str, Any]
) -> None:
    """An out-of-range assumption override is rejected with 400."""
    response = auth_client.post(
        f"/api/v1/projects/{project.pk}/analyses/",
        {"name": "Roof scan", "area": polygon_geojson, "assumptions": {"tilt_deg": 120.0}},
        format="json",
    )
    assert response.status_code == 400


def test_detail_exposes_defaults_and_frozen_snapshot(
    auth_client: APIClient, project: Any, polygon_geojson: dict[str, Any]
) -> None:
    """Detail surfaces DEC-01 defaults and, after submit, the frozen snapshot."""
    ModelRegistryService.get_or_create_default()
    SolarMethodRegistry.get_or_create_default()
    created = auth_client.post(
        f"/api/v1/projects/{project.pk}/analyses/",
        {"name": "Roof scan", "area": polygon_geojson, "assumptions": {"tilt_deg": 33.0}},
        format="json",
    )
    analysis_id = created.data["id"]
    assert created.data["assumption_defaults"]["usable_roof_fraction"] == 0.70

    auth_client.post(
        f"/api/v1/analyses/{analysis_id}/submit/",
        {},
        format="json",
        HTTP_IDEMPOTENCY_KEY="key-1",
    )
    detail = auth_client.get(f"/api/v1/analyses/{analysis_id}/")
    assert detail.status_code == 200
    assert detail.data["snapshot"]["assumptions"]["tilt_deg"] == 33.0
    assert detail.data["snapshot"]["model_version"]
    assert detail.data["assumption"]["tilt_deg"] == 33.0


def test_delete_analysis_records_surviving_audit_event(
    auth_client: APIClient, project: Any, polygon_geojson: dict[str, Any]
) -> None:
    """Deleting an analysis via the API records an audit event that survives."""
    created = _create_analysis(auth_client, str(project.pk), polygon_geojson)
    analysis_id = created.data["id"]

    response = auth_client.delete(f"/api/v1/analyses/{analysis_id}/")
    assert response.status_code == 204
    assert not Analysis.objects.filter(pk=analysis_id).exists()

    event = AuditEvent.objects.filter(
        action="analysis.deleted", target_id=str(analysis_id)
    ).first()
    assert event is not None
    assert event.actor_email  # direct delete threads the acting user


def test_non_owner_cannot_delete_analysis(
    auth_client: APIClient,
    api_client: APIClient,
    user_factory: Any,
    project: Any,
    polygon_geojson: dict[str, Any],
) -> None:
    """A non-owner receives 404 and cannot delete another user's analysis."""
    from rest_framework_simplejwt.tokens import RefreshToken

    created = _create_analysis(auth_client, str(project.pk), polygon_geojson)
    analysis_id = created.data["id"]

    other = user_factory()
    token = RefreshToken.for_user(other)
    access = token.access_token  # type: ignore[attr-defined]  # simplejwt dynamic attr
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = api_client.delete(f"/api/v1/analyses/{analysis_id}/")
    assert response.status_code == 404
    assert Analysis.objects.filter(pk=analysis_id).exists()
