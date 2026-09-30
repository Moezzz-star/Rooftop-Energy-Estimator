"""API tests for the imagery endpoints (#11 upload, #12 detail, #13 sources).

Upload/detail tests require the DB and the geo/raster stack (GeoDjango +
rasterio); they are skipped when rasterio is unavailable. Ownership enforcement
is asserted for both the upload and the detail endpoints.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from .conftest import SAMPLE_TIF

rasterio = pytest.importorskip("rasterio")

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.skipif(not SAMPLE_TIF.is_file(), reason="bundled sample raster missing"),
]


def _auth(client: APIClient, user: Any) -> APIClient:
    token = RefreshToken.for_user(user)
    access = token.access_token  # type: ignore[attr-defined]  # simplejwt dynamic attr
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client


def test_sources_endpoint_lists_uploaded_raster(auth_client: APIClient) -> None:
    """GET /imagery/sources/ returns the uploaded-raster provider."""
    resp = auth_client.get(reverse("v1:imagery-sources"))
    assert resp.status_code == 200
    names = {s["name"] for s in resp.json()["sources"]}
    assert "uploaded_raster" in names


def test_upload_creates_asset(
    api_client: APIClient,
    analysis_factory: Callable[..., Any],
    user_factory: Callable[..., Any],
    tmp_path: Path,
    settings: Any,
) -> None:
    """POST upload persists an ImageryAsset with real sample metadata."""
    settings.MEDIA_ROOT = tmp_path
    owner = user_factory()
    analysis = analysis_factory(owner=owner)
    client = _auth(api_client, owner)

    with SAMPLE_TIF.open("rb") as handle:
        resp = client.post(
            reverse("v1:analysis-imagery-upload", args=[analysis.pk]),
            {"file": handle},
            format="multipart",
        )

    assert resp.status_code == 201, resp.content
    body = resp.json()
    assert body["crs"] == "EPSG:32632"
    assert body["bands"] == 3

    from apps.imagery.models import ImageryAsset

    assert ImageryAsset.objects.filter(analysis=analysis).count() == 1


def test_upload_rejects_non_owner(
    api_client: APIClient,
    analysis_factory: Callable[..., Any],
    user_factory: Callable[..., Any],
    tmp_path: Path,
    settings: Any,
) -> None:
    """A non-owner cannot upload imagery to another user's analysis."""
    settings.MEDIA_ROOT = tmp_path
    analysis = analysis_factory(owner=user_factory())
    intruder = user_factory()
    client = _auth(api_client, intruder)

    with SAMPLE_TIF.open("rb") as handle:
        resp = client.post(
            reverse("v1:analysis-imagery-upload", args=[analysis.pk]),
            {"file": handle},
            format="multipart",
        )

    assert resp.status_code in (403, 404)


def test_detail_rejects_non_owner(
    api_client: APIClient,
    analysis_factory: Callable[..., Any],
    user_factory: Callable[..., Any],
    tmp_path: Path,
    settings: Any,
) -> None:
    """A non-owner cannot read another user's imagery metadata."""
    settings.MEDIA_ROOT = tmp_path
    owner = user_factory()
    analysis = analysis_factory(owner=owner)

    from apps.imagery.services import ImageryService

    asset = ImageryService().register_bundled_sample(analysis)

    intruder = user_factory()
    client = _auth(api_client, intruder)
    resp = client.get(reverse("v1:imagery-detail", args=[asset.pk]))
    assert resp.status_code in (403, 404)
