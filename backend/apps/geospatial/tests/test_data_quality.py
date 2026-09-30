"""Tests for :class:`DataQualityService` (§16).

The data-quality indicator is a transparent heuristic (NOT a calibrated
confidence interval). These tests exercise the high/low ends of each factor and
the per-building warning derivation. They require the DB and GeoDjango.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

pytest.importorskip("django.contrib.gis.geos")

pytestmark = pytest.mark.django_db


def _add_roof(building: Any) -> Any:
    """Attach a roof geometry (with orientation) to ``building``."""
    from apps.geospatial.models import RoofGeometry

    return RoofGeometry.objects.create(
        building=building,
        tilt_deg=30.0,
        azimuth_deg=180.0,
        usable_area_m2=float(building.area_m2) * 0.7,
        source="footprint",
        geometry=building.geometry,
    )


def _add_imagery(analysis: Any, *, resolution_m: float | None, acquired_at: Any = None) -> Any:
    """Create an ImageryAsset for ``analysis`` without importing the app."""
    from django.apps import apps as django_apps

    model = django_apps.get_model("imagery", "ImageryAsset")
    return model.objects.create(
        analysis=analysis,
        provider="test",
        storage_key="k",
        checksum="c",
        crs="EPSG:4326",
        resolution_m=resolution_m,
        acquired_at=acquired_at,
    )


def test_summary_high_quality(
    analysis_factory: Callable[..., Any],
    building_factory: Callable[..., Any],
) -> None:
    """Sharp recent imagery + confident, valid, oriented buildings -> high."""
    from django.utils import timezone

    from apps.geospatial.services import DataQualityService

    analysis = analysis_factory()
    _add_imagery(analysis, resolution_m=0.2, acquired_at=timezone.now())
    for _ in range(3):
        building = building_factory(analysis, confidence=0.95, area_m2=200.0)
        _add_roof(building)

    summary = DataQualityService().summarize(analysis)

    assert summary["indicator"] == "high"
    assert summary["factors"]["imagery_resolution"]["class"] == "good"
    assert summary["factors"]["segmentation_confidence"]["class"] == "good"
    assert summary["factors"]["polygon_validity"]["valid_fraction"] == 1.0
    assert summary["factors"]["missing_orientation"]["fraction_missing"] == 0.0
    # Transparency note is always present and never claims calibration.
    assert any("not a calibrated" in note for note in summary["notes"])


def test_summary_low_quality(
    analysis_factory: Callable[..., Any],
    building_factory: Callable[..., Any],
) -> None:
    """Coarse imagery + low confidence + no orientation -> low."""
    from apps.geospatial.services import DataQualityService

    analysis = analysis_factory()
    _add_imagery(analysis, resolution_m=3.0, acquired_at=None)
    for _ in range(3):
        building_factory(analysis, confidence=0.2, area_m2=200.0)  # no roof

    summary = DataQualityService().summarize(analysis)

    assert summary["indicator"] == "low"
    assert summary["factors"]["imagery_resolution"]["class"] == "poor"
    assert summary["factors"]["imagery_age"]["class"] == "unknown"
    assert summary["factors"]["segmentation_confidence"]["class"] == "poor"
    assert summary["factors"]["missing_orientation"]["fraction_missing"] == 1.0


def test_summary_without_imagery_or_buildings(
    analysis_factory: Callable[..., Any],
) -> None:
    """An empty analysis yields unknown factors and a defensible indicator."""
    from apps.geospatial.services import DataQualityService

    analysis = analysis_factory()
    summary = DataQualityService().summarize(analysis)

    assert summary["indicator"] in ("high", "medium", "low")
    assert summary["factors"]["imagery_resolution"]["class"] == "unknown"
    assert summary["factors"]["segmentation_confidence"]["class"] == "unknown"
    assert summary["factors"]["polygon_validity"]["class"] == "unknown"


def test_building_warnings_flags_issues(
    analysis_factory: Callable[..., Any],
    building_factory: Callable[..., Any],
) -> None:
    """A weak building surfaces low confidence, missing orientation, small area."""
    from apps.geospatial.services import DataQualityService

    analysis = analysis_factory()
    building = building_factory(analysis, confidence=0.2, area_m2=5.0)  # no roof

    warnings = DataQualityService().building_warnings(building)

    assert "low_confidence" in warnings
    assert "missing_orientation" in warnings
    assert "below_min_area" in warnings


def test_building_warnings_clean_building(
    analysis_factory: Callable[..., Any],
    building_factory: Callable[..., Any],
) -> None:
    """A confident, oriented, adequately-sized building has no warnings."""
    from apps.geospatial.services import DataQualityService

    analysis = analysis_factory()
    building = building_factory(analysis, confidence=0.95, area_m2=200.0)
    _add_roof(building)

    assert DataQualityService().building_warnings(building) == []
