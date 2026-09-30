"""Integration tests for the exports HTTP endpoints (§4 #20, #21)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.exports.models import ExportArtifact, ExportStatus
from apps.exports.services import ExportService

pytestmark = pytest.mark.django_db


def test_request_geojson_export_creates_and_builds_artifact(
    auth_client: APIClient, analysis: Any, building_factory: Callable[..., Any]
) -> None:
    """POST export creates a pending artifact and (eager) builds it (#20)."""
    building_factory(analysis, index=0)

    response = auth_client.post(
        f"/api/v1/analyses/{analysis.pk}/exports/", {"kind": "geojson"}, format="json"
    )

    assert response.status_code == 202
    artifact = ExportArtifact.objects.get(pk=response.data["id"])
    # Eager Celery built it synchronously.
    assert artifact.status == ExportStatus.READY
    assert artifact.storage_key


def test_list_exports_scoped_to_owner(auth_client: APIClient, analysis: Any) -> None:
    """GET lists the analysis's exports for the owner (#20)."""
    ExportArtifact.objects.create(analysis=analysis, kind="csv")

    response = auth_client.get(f"/api/v1/analyses/{analysis.pk}/exports/")

    assert response.status_code == 200
    assert len(response.data) == 1


def test_export_detail_ownership_enforced(
    api_client: APIClient, user_factory: Any, analysis: Any
) -> None:
    """A non-owner cannot read another user's export artifact (#21)."""
    artifact = ExportArtifact.objects.create(analysis=analysis, kind="csv")

    other = user_factory()
    token = RefreshToken.for_user(other)
    access = token.access_token  # type: ignore[attr-defined]  # simplejwt dynamic attr
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = api_client.get(f"/api/v1/exports/{artifact.pk}/")
    assert response.status_code == 403


def test_export_detail_download_url_is_opaque(
    auth_client: APIClient, analysis: Any, building_factory: Callable[..., Any]
) -> None:
    """The detail response exposes an opaque download URL, never storage_key (#21)."""
    building_factory(analysis, index=0)
    auth_client.post(
        f"/api/v1/analyses/{analysis.pk}/exports/", {"kind": "geojson"}, format="json"
    )
    artifact = ExportArtifact.objects.get(analysis=analysis)

    response = auth_client.get(f"/api/v1/exports/{artifact.pk}/")

    assert response.status_code == 200
    assert "storage_key" not in response.data
    download_url = response.data["download_url"]
    assert download_url is not None
    assert download_url.endswith(f"/exports/{artifact.pk}/download/")
    # The opaque URL must not embed the internal storage key / filesystem path.
    assert artifact.storage_key not in download_url


def test_export_download_streams_bytes_for_owner(
    auth_client: APIClient, analysis: Any, building_factory: Callable[..., Any]
) -> None:
    """The owner can download the built artifact bytes with an attachment header."""
    building_factory(analysis, index=0)
    auth_client.post(
        f"/api/v1/analyses/{analysis.pk}/exports/", {"kind": "geojson"}, format="json"
    )
    artifact = ExportArtifact.objects.get(analysis=analysis)

    response = auth_client.get(f"/api/v1/exports/{artifact.pk}/download/")

    assert response.status_code == 200
    disposition = response["Content-Disposition"]
    assert "attachment" in disposition
    # Filename is derived from the analysis id + kind, not the storage key.
    assert artifact.storage_key not in disposition
    body = b"".join(response.streaming_content)
    assert body.startswith(b"{")


def test_export_download_denied_for_non_owner(
    api_client: APIClient, user_factory: Any, analysis: Any, building_factory: Callable[..., Any]
) -> None:
    """A non-owner cannot download another user's artifact (#21)."""
    building_factory(analysis, index=0)
    artifact = ExportArtifact.objects.create(analysis=analysis, kind="csv")
    ExportService().build(artifact)

    other = user_factory()
    token = RefreshToken.for_user(other)
    access = token.access_token  # type: ignore[attr-defined]  # simplejwt dynamic attr
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = api_client.get(f"/api/v1/exports/{artifact.pk}/download/")
    assert response.status_code == 403
