"""Tests for :class:`SolarEstimationService`.

These tests exercise the service against the real pure ``SolarModel`` (pvlib)
and the ORM. They use a lightweight duck-typed building (a namespace with
``area_m2`` + a centroid exposing ``.x``/``.y``) rather than the geospatial
``Building`` model, which is built in parallel. DB-touching tests are marked
``django_db``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point, Polygon

from apps.solar.models import DISCLAIMER, SolarEstimate
from apps.solar.services import (
    SolarEstimationService,
    SolarLocation,
    SolarMethodRegistry,
)
from common.errors import ValidationError


@dataclass
class _Assumption:
    """Minimal DEC-01 assumption stand-in."""

    source: str = "default"
    usable_roof_fraction: float = 0.70
    power_density_w_m2: float = 200.0
    system_losses: float = 0.14
    tilt_deg: float = 20.0
    azimuth_deg: float = 180.0
    shading: float = 1.0


def _real_building(area_m2: float, lat: float, lon: float) -> Any:
    """Create and persist a real geospatial ``Building`` (with its ownership
    chain) so ``SolarEstimate.building`` FK assignment is valid."""
    from apps.analyses.models import Analysis
    from apps.geospatial.models import Building
    from apps.projects.models import Project

    user = get_user_model().objects.create_user(email="solar@example.com", password="pw-123456")
    project = Project.objects.create(owner=user, name="Solar test project")
    analysis = Analysis.objects.create(project=project, name="Solar test analysis")
    d = 0.001
    geometry = Polygon(
        (
            (lon - d, lat - d),
            (lon + d, lat - d),
            (lon + d, lat + d),
            (lon - d, lat + d),
            (lon - d, lat - d),
        ),
        srid=4326,
    )
    return Building.objects.create(
        analysis=analysis,
        area_m2=area_m2,
        index=0,
        geometry=geometry,
        centroid=Point(lon, lat, srid=4326),
    )


@pytest.mark.django_db
def test_estimate_persists_full_result() -> None:
    """A valid building yields a persisted, 12-month, positive estimate."""
    building = _real_building(area_m2=120.0, lat=48.137, lon=11.575)
    location = SolarLocation(timezone="Europe/Berlin", altitude=520.0)
    service = SolarEstimationService()

    estimate = service.estimate(building, _Assumption(), location)

    assert isinstance(estimate, SolarEstimate)
    assert len(estimate.monthly_kwh) == 12
    assert estimate.annual_kwh > 0
    assert estimate.capacity_kwp > 0
    assert estimate.usable_area_m2 == pytest.approx(120.0 * 0.70)
    assert estimate.disclaimer == DISCLAIMER
    assert estimate.calculation_version is not None
    assert estimate.inputs["source"] == "default"
    assert estimate.inputs["timezone"] == "Europe/Berlin"


@pytest.mark.django_db
def test_estimate_uses_explicit_location_coordinates() -> None:
    """Explicit lat/lon override the building centroid."""
    building = _real_building(area_m2=80.0, lat=0.0, lon=0.0)
    location = SolarLocation(
        timezone="Europe/Berlin", altitude=100.0, latitude=48.0, longitude=11.0
    )
    service = SolarEstimationService()

    estimate = service.estimate(building, _Assumption(), location)
    assert estimate.inputs["latitude"] == 48.0
    assert estimate.inputs["longitude"] == 11.0


@pytest.mark.django_db
def test_estimate_invalid_timezone_raises_validation_error() -> None:
    """An invalid IANA timezone maps to a domain ValidationError (§15)."""
    building = _real_building(area_m2=120.0, lat=48.0, lon=11.0)
    location = SolarLocation(timezone="Not/AZone", altitude=0.0)
    service = SolarEstimationService()

    with pytest.raises(ValidationError):
        service.estimate(building, _Assumption(), location)
    assert SolarEstimate.objects.count() == 0


@pytest.mark.django_db
def test_estimate_invalid_fraction_raises_validation_error() -> None:
    """An out-of-range usable_roof_fraction maps to ValidationError (§15)."""
    building = _real_building(area_m2=120.0, lat=48.0, lon=11.0)
    location = SolarLocation(timezone="Europe/Berlin")
    bad = _Assumption(usable_roof_fraction=1.5)
    service = SolarEstimationService()

    with pytest.raises(ValidationError):
        service.estimate(building, bad, location)


@pytest.mark.django_db
def test_method_registry_default_is_idempotent() -> None:
    """The default methodology is created once and reused."""
    first = SolarMethodRegistry.get_or_create_default()
    second = SolarMethodRegistry.get_or_create_default()
    assert first.pk == second.pk
    assert first.name == "solar"
    assert SolarMethodRegistry().get_active().pk == first.pk
    assert "usable_roof_fraction" in first.parameters
