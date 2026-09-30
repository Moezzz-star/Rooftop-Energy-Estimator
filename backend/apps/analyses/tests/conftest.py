"""Shared fixtures for analyses tests.

A ``project`` fixture is built via ``apps.get_model`` so these tests do not
import the projects app directly. All fixtures require the database.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from django.apps import apps


@pytest.fixture
def project_factory(db: Any) -> Callable[..., Any]:
    """Return a factory creating projects owned by a given user."""
    project_model = apps.get_model("projects", "Project")

    def _create(owner: Any, **overrides: Any) -> Any:
        defaults: dict[str, Any] = {"name": overrides.pop("name", "Test Project")}
        defaults.update(overrides)
        return project_model.objects.create(owner=owner, **defaults)

    return _create


@pytest.fixture
def project(project_factory: Callable[..., Any], user: Any) -> Any:
    """Return a single project owned by the default ``user`` fixture."""
    return project_factory(owner=user)


@pytest.fixture
def polygon_geojson() -> dict[str, Any]:
    """Return a small valid GeoJSON polygon near Munich (EPSG:4326)."""
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [11.574, 48.137],
                [11.575, 48.137],
                [11.575, 48.138],
                [11.574, 48.138],
                [11.574, 48.137],
            ]
        ],
    }
