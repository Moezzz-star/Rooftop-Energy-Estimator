"""Shared fixtures for exports tests.

Builds a minimal user -> project -> analysis -> building(+solar estimate) chain
directly via the ORM so export rendering has data to serialize.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from django.apps import apps as django_apps
from django.contrib.gis.geos import Point, Polygon


@pytest.fixture
def project(db: Any, user: Any) -> Any:
    """Return a project owned by the default ``user`` fixture."""
    project_model = django_apps.get_model("projects", "Project")
    return project_model.objects.create(owner=user, name="Exports Test Project")


@pytest.fixture
def analysis(db: Any, project: Any) -> Any:
    """Return a draft analysis under ``project``."""
    analysis_model = django_apps.get_model("analyses", "Analysis")
    return analysis_model.objects.create(project=project, name="Export analysis")


@pytest.fixture
def building_factory(db: Any) -> Callable[..., Any]:
    """Return a factory creating persisted buildings for an analysis."""
    building_model = django_apps.get_model("geospatial", "Building")

    def _create(analysis: Any, index: int = 0) -> Any:
        polygon = Polygon(
            ((9.0, 48.75), (9.001, 48.75), (9.001, 48.751), (9.0, 48.751), (9.0, 48.75)),
            srid=4326,
        )
        centroid = Point(9.0005, 48.7505, srid=4326)
        return building_model.objects.create(
            analysis=analysis,
            area_m2=120.0,
            index=index,
            confidence=0.9,
            geometry=polygon,
            centroid=centroid,
        )

    return _create


@pytest.fixture
def solar_estimate_factory(db: Any) -> Callable[..., Any]:
    """Return a factory creating solar estimates for a building."""
    from apps.solar.services import SolarMethodRegistry

    estimate_model = django_apps.get_model("solar", "SolarEstimate")

    def _create(building: Any) -> Any:
        method = SolarMethodRegistry.get_or_create_default()
        return estimate_model.objects.create(
            building=building,
            calculation_version=method,
            capacity_kwp=16.8,
            annual_kwh=18000.0,
            monthly_kwh=[1500.0] * 12,
            specific_yield=1071.4,
            usable_area_m2=84.0,
            inputs={"source": "default"},
        )

    return _create
