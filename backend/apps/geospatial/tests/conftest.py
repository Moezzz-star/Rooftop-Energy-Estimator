"""Shared fixtures for geospatial tests (ownership chain + building factory)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest


@pytest.fixture
def analysis_factory(db: Any, user_factory: Callable[..., Any]) -> Callable[..., Any]:
    """Return a factory creating an ``analyses.Analysis`` owned by a user."""
    from django.apps import apps as django_apps

    project_model = django_apps.get_model("projects", "Project")
    analysis_model = django_apps.get_model("analyses", "Analysis")

    def _create(owner: Any | None = None, **overrides: Any) -> Any:
        owner = owner or user_factory()
        project = project_model.objects.create(owner=owner, name="P")
        return analysis_model.objects.create(
            project=project, name=overrides.pop("name", "A"), **overrides
        )

    return _create


@pytest.fixture
def building_factory(db: Any) -> Callable[..., Any]:
    """Return a factory creating persisted buildings with 4326 geometry."""
    from django.contrib.gis.geos import Point, Polygon

    from apps.geospatial.models import Building

    counter = {"n": 0}

    def _create(analysis: Any, **overrides: Any) -> Building:
        counter["n"] += 1
        idx = overrides.pop("index", counter["n"])
        lon = overrides.pop("lon", 9.0 + idx * 0.001)
        lat = overrides.pop("lat", 48.75)
        ring = Polygon.from_bbox((lon, lat, lon + 0.0005, lat + 0.0005))
        ring.srid = 4326
        centroid = Point(lon + 0.00025, lat + 0.00025, srid=4326)
        return Building.objects.create(
            analysis=analysis,
            geometry=ring,
            centroid=centroid,
            area_m2=overrides.pop("area_m2", 100.0 * idx),
            confidence=overrides.pop("confidence", 0.9),
            index=idx,
        )

    return _create
