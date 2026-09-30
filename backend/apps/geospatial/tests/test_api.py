"""API tests for the geospatial endpoints (#16 results, #17 list, #18 detail, #19 features).

These require the DB and GeoDjango (GDAL/PostGIS) for geometry fields; they are
skipped when GEOS/GDAL are unavailable. Routes are resolved by name so they pass
regardless of the (currently ``/api/v1/geometry/``) include prefix.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

pytest.importorskip("django.contrib.gis.geos")

pytestmark = pytest.mark.django_db


def _auth(client: APIClient, user: Any) -> APIClient:
    token = RefreshToken.for_user(user)
    access = token.access_token  # type: ignore[attr-defined]  # simplejwt dynamic attr
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client


def test_geometry_validate_endpoint(auth_client: APIClient) -> None:
    """POST geometry/validate/ returns validity and area."""
    payload = {
        "geojson": {
            "type": "Polygon",
            "coordinates": [
                [
                    [9.0, 48.75],
                    [9.001, 48.75],
                    [9.001, 48.751],
                    [9.0, 48.751],
                    [9.0, 48.75],
                ]
            ],
        }
    }
    resp = auth_client.post(reverse("v1:geometry-validate"), payload, format="json")
    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is True
    assert body["features"][0]["area_m2"] > 0


def test_buildings_list_paginated_geometry_omitted(
    api_client: APIClient,
    analysis_factory: Callable[..., Any],
    building_factory: Callable[..., Any],
    user_factory: Callable[..., Any],
) -> None:
    """Building list is paginated and omits geometry by default."""
    owner = user_factory()
    analysis = analysis_factory(owner=owner)
    for _ in range(3):
        building_factory(analysis)
    client = _auth(api_client, owner)

    resp = client.get(reverse("v1:analysis-buildings", args=[analysis.pk]))
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 3
    assert all(row["geometry"] is None for row in body["results"])


def test_buildings_list_geometry_opt_in(
    api_client: APIClient,
    analysis_factory: Callable[..., Any],
    building_factory: Callable[..., Any],
    user_factory: Callable[..., Any],
) -> None:
    """?geometry=simplified embeds geometry in the tabular rows."""
    owner = user_factory()
    analysis = analysis_factory(owner=owner)
    building_factory(analysis)
    client = _auth(api_client, owner)

    resp = client.get(
        reverse("v1:analysis-buildings", args=[analysis.pk]),
        {"geometry": "simplified"},
    )
    assert resp.status_code == 200
    assert resp.json()["results"][0]["geometry"] is not None


def test_features_requires_bbox(
    api_client: APIClient,
    analysis_factory: Callable[..., Any],
    user_factory: Callable[..., Any],
) -> None:
    """The features endpoint returns 400 when bbox is missing."""
    owner = user_factory()
    analysis = analysis_factory(owner=owner)
    client = _auth(api_client, owner)

    resp = client.get(reverse("v1:analysis-features", args=[analysis.pk]))
    assert resp.status_code == 400


def test_features_with_bbox_returns_feature_collection(
    api_client: APIClient,
    analysis_factory: Callable[..., Any],
    building_factory: Callable[..., Any],
    user_factory: Callable[..., Any],
) -> None:
    """With a bbox, features returns a GeoJSON FeatureCollection."""
    owner = user_factory()
    analysis = analysis_factory(owner=owner)
    building_factory(analysis, lon=9.0, lat=48.75)
    client = _auth(api_client, owner)

    resp = client.get(
        reverse("v1:analysis-features", args=[analysis.pk]),
        {"bbox": "8.9,48.7,9.1,48.8", "zoom": "16"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["type"] == "FeatureCollection"
    assert len(body["features"]) == 1


def test_results_summary_aggregates(
    api_client: APIClient,
    analysis_factory: Callable[..., Any],
    building_factory: Callable[..., Any],
    user_factory: Callable[..., Any],
) -> None:
    """Results summary reports counts, area totals, and the disclaimer."""
    owner = user_factory()
    analysis = analysis_factory(owner=owner)
    building_factory(analysis, area_m2=100.0)
    building_factory(analysis, area_m2=250.0)
    client = _auth(api_client, owner)

    resp = client.get(reverse("v1:analysis-results", args=[analysis.pk]))
    assert resp.status_code == 200
    body = resp.json()
    assert body["building_count"] == 2
    assert body["total_area_m2"] == pytest.approx(350.0)
    assert "engineering estimates" in body["disclaimer"]


def test_building_detail_rejects_non_owner(
    api_client: APIClient,
    analysis_factory: Callable[..., Any],
    building_factory: Callable[..., Any],
    user_factory: Callable[..., Any],
) -> None:
    """A non-owner cannot read another user's building detail."""
    owner = user_factory()
    analysis = analysis_factory(owner=owner)
    building = building_factory(analysis)
    intruder = user_factory()
    client = _auth(api_client, intruder)

    resp = client.get(reverse("v1:building-detail", args=[building.pk]))
    assert resp.status_code in (403, 404)


def test_results_summary_enriched_fields(
    api_client: APIClient,
    analysis_factory: Callable[..., Any],
    building_factory: Callable[..., Any],
    user_factory: Callable[..., Any],
) -> None:
    """Results summary exposes the §9 zone-summary fields and data quality."""
    owner = user_factory()
    analysis = analysis_factory(owner=owner)
    building_factory(analysis, area_m2=100.0)
    client = _auth(api_client, owner)

    resp = client.get(reverse("v1:analysis-results", args=[analysis.pk]))
    assert resp.status_code == 200
    body = resp.json()
    for key in (
        "total_usable_area_m2",
        "total_capacity_kwp",
        "total_annual_kwh",
        "average_specific_yield",
        "system_losses",
        "model_version",
        "calculation_version",
        "data_quality",
    ):
        assert key in body
    assert body["data_quality"]["indicator"] in ("high", "medium", "low")
    assert "factors" in body["data_quality"]


def test_building_detail_exposes_fields_and_warnings(
    api_client: APIClient,
    analysis_factory: Callable[..., Any],
    building_factory: Callable[..., Any],
    user_factory: Callable[..., Any],
) -> None:
    """Building detail exposes §9 fields and derived warnings (#18)."""
    owner = user_factory()
    analysis = analysis_factory(owner=owner)
    building = building_factory(analysis, confidence=0.2, area_m2=5.0)  # weak, no roof
    client = _auth(api_client, owner)

    resp = client.get(reverse("v1:building-detail", args=[building.pk]))
    assert resp.status_code == 200
    body = resp.json()
    # §9 fields present (null where no roof/solar exists yet).
    for key in (
        "usable_area_m2",
        "tilt_deg",
        "azimuth_deg",
        "shading",
        "capacity_kwp",
        "annual_kwh",
        "monthly_kwh",
        "specific_yield",
        "warnings",
    ):
        assert key in body
    assert "low_confidence" in body["warnings"]
    assert "missing_orientation" in body["warnings"]
    assert "below_min_area" in body["warnings"]


def test_buildings_ordering(
    api_client: APIClient,
    analysis_factory: Callable[..., Any],
    building_factory: Callable[..., Any],
    user_factory: Callable[..., Any],
) -> None:
    """The list endpoint supports ascending/descending ordering by area."""
    owner = user_factory()
    analysis = analysis_factory(owner=owner)
    building_factory(analysis, area_m2=100.0)
    building_factory(analysis, area_m2=300.0)
    building_factory(analysis, area_m2=200.0)
    client = _auth(api_client, owner)

    asc = client.get(reverse("v1:analysis-buildings", args=[analysis.pk]), {"order": "area"})
    assert asc.status_code == 200
    asc_areas = [row["area_m2"] for row in asc.json()["results"]]
    assert asc_areas == sorted(asc_areas)

    desc = client.get(reverse("v1:analysis-buildings", args=[analysis.pk]), {"order": "-area"})
    desc_areas = [row["area_m2"] for row in desc.json()["results"]]
    assert desc_areas == sorted(desc_areas, reverse=True)
