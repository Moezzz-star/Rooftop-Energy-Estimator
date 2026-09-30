"""Shared fixtures for jobs tests.

Fixtures build a user -> project -> analysis chain (with the bundled sample area
and assumptions) via services, so tests exercise real cross-app wiring. The
sample area geometry is loaded from ``sample-data/sample_area.geojson``.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from django.apps import apps as django_apps
from django.conf import settings
from django.contrib.gis.geos import GEOSGeometry


def _sample_area() -> GEOSGeometry:
    """Return the bundled sample area as an EPSG:4326 GEOS geometry."""
    path = Path(settings.BASE_DIR).parent / "sample-data" / "sample_area.geojson"
    payload = json.loads(path.read_text())
    geometry = payload["features"][0]["geometry"]
    geom = GEOSGeometry(json.dumps(geometry))
    geom.srid = 4326
    return geom


@pytest.fixture
def project(db: Any, user: Any) -> Any:
    """Return a project owned by the default ``user`` fixture."""
    project_model = django_apps.get_model("projects", "Project")
    return project_model.objects.create(owner=user, name="Jobs Test Project")


@pytest.fixture
def analysis_factory(db: Any) -> Callable[..., Any]:
    """Return a factory creating draft analyses over the sample area."""
    from apps.analyses.services import AnalysisService

    def _create(project: Any, name: str = "Sample analysis") -> Any:
        return AnalysisService().create(project=project, name=name, area=_sample_area())

    return _create


@pytest.fixture
def analysis(analysis_factory: Callable[..., Any], project: Any) -> Any:
    """Return a single draft analysis over the sample area."""
    return analysis_factory(project)
