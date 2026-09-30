"""Tests for :class:`GeometryValidationService` (pure shapely/pyproj, no DB)."""

from __future__ import annotations

import pytest

from apps.geospatial.services import GeometryValidationService
from common.errors import ValidationError

pytest.importorskip("shapely")
pytest.importorskip("pyproj")


def _polygon(coords: list[list[float]]) -> dict[str, object]:
    return {"type": "Polygon", "coordinates": [coords]}


def test_valid_polygon_reports_sensible_utm_area() -> None:
    """A ~255 x 256 m rectangle near Stuttgart yields ~65,000 m^2."""
    square = _polygon(
        [
            [9.0, 48.75070997424761],
            [9.0034828274372, 48.75070997424761],
            [9.0034828274372, 48.75301300432218],
            [9.0, 48.75301300432218],
            [9.0, 48.75070997424761],
        ]
    )
    result = GeometryValidationService().validate(square)

    assert result["valid"] is True
    assert result["count"] == 1
    feature = result["features"][0]
    assert feature["repairs"] == []
    assert 50_000 < feature["area_m2"] < 80_000


def test_self_intersecting_polygon_is_repaired() -> None:
    """A self-intersecting bowtie is repaired (valid) with repairs recorded."""
    bowtie = _polygon(
        [
            [9.0, 48.0],
            [9.001, 48.001],
            [9.0, 48.001],
            [9.001, 48.0],
            [9.0, 48.0],
        ]
    )
    result = GeometryValidationService().validate(bowtie)

    feature = result["features"][0]
    assert feature["valid"] is True
    assert feature["repairs"]  # at least one repair op applied
    assert feature["area_m2"] > 0


def test_feature_collection_aggregates_multiple() -> None:
    """A FeatureCollection validates each polygon and sums areas."""
    poly = _polygon(
        [
            [9.0, 48.75],
            [9.001, 48.75],
            [9.001, 48.751],
            [9.0, 48.751],
            [9.0, 48.75],
        ]
    )
    fc = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "geometry": poly, "properties": {}},
            {"type": "Feature", "geometry": poly, "properties": {}},
        ],
    }
    result = GeometryValidationService().validate(fc)

    assert result["count"] == 2
    assert result["total_area_m2"] == pytest.approx(2 * result["features"][0]["area_m2"])


def test_empty_payload_raises() -> None:
    """A payload with no polygon raises a domain ValidationError."""
    with pytest.raises(ValidationError):
        GeometryValidationService().validate({"type": "FeatureCollection", "features": []})


def test_oversized_polygon_is_flagged_not_raised() -> None:
    """A polygon larger than the max-area guard is invalid, not a crash (#10)."""
    big = _polygon(
        [
            [9.0, 48.0],
            [9.2, 48.0],
            [9.2, 48.2],
            [9.0, 48.2],
            [9.0, 48.0],
        ]
    )
    # A ~5 km^2 guard makes the ~300 km^2 polygon exceed the bound.
    result = GeometryValidationService(max_area_km2=5.0).validate(big)

    feature = result["features"][0]
    assert feature["valid"] is False
    assert result["valid"] is False
    assert "exceeds_max_area" in feature["warnings"]
    assert feature["area_m2"] > 0


def test_multipolygon_is_supported() -> None:
    """A MultiPolygon validates and its area sums both parts."""
    multi = {
        "type": "MultiPolygon",
        "coordinates": [
            [[[9.0, 48.75], [9.001, 48.75], [9.001, 48.751], [9.0, 48.751], [9.0, 48.75]]],
            [[[9.01, 48.75], [9.011, 48.75], [9.011, 48.751], [9.01, 48.751], [9.01, 48.75]]],
        ],
    }
    result = GeometryValidationService().validate(multi)

    assert result["count"] == 1
    feature = result["features"][0]
    assert feature["valid"] is True
    assert feature["area_m2"] > 0


def test_non_polygon_geometry_rejected() -> None:
    """A LineString geometry is rejected with a ValidationError."""
    fc = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": [[9.0, 48.0], [9.1, 48.1]]},
                "properties": {},
            }
        ],
    }
    with pytest.raises(ValidationError):
        GeometryValidationService().validate(fc)


def test_below_min_area_warning_present() -> None:
    """A tiny valid polygon carries a below_min_area warning but stays valid."""
    tiny = _polygon(
        [
            [9.0, 48.75],
            [9.00001, 48.75],
            [9.00001, 48.75001],
            [9.0, 48.75001],
            [9.0, 48.75],
        ]
    )
    result = GeometryValidationService().validate(tiny)

    feature = result["features"][0]
    assert feature["valid"] is True
    assert "below_min_area" in feature["warnings"]
