"""Shared fixtures for imagery tests.

Provides ownership-chain objects (project + analysis) built via the analyses/
projects apps, and a marker to skip when the geo/raster stack is unavailable.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

# Repo-root sample raster (see sample-data/README.md): EPSG:32632, 0.5 m/px.
SAMPLE_TIF = Path(__file__).resolve().parents[4] / "sample-data" / "sample_imagery.tif"


def write_geotiff(
    path: Path,
    *,
    bands: int = 3,
    width: int = 8,
    height: int = 8,
    dtype: str = "uint8",
    crs: str | None = "EPSG:32632",
    nodata: float | None = None,
) -> Path:
    """Write a tiny valid GeoTIFF for tests and return its path.

    Uses a metric CRS + 0.5 m pixels by default so bounds are finite and
    non-degenerate. ``crs=None`` produces a raster with no CRS (for the
    missing-CRS rejection test).
    """
    import numpy as np
    import rasterio
    from rasterio.transform import from_origin

    transform = from_origin(500000.0, 5000000.0, 0.5, 0.5)
    profile: dict[str, Any] = {
        "driver": "GTiff",
        "width": width,
        "height": height,
        "count": bands,
        "dtype": dtype,
        "transform": transform,
    }
    if crs is not None:
        profile["crs"] = crs
    if nodata is not None:
        profile["nodata"] = nodata
    data = np.ones((bands, height, width), dtype=dtype)
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(data)
    return path


@pytest.fixture
def analysis_factory(db: Any, user_factory: Callable[..., Any]) -> Callable[..., Any]:
    """Return a factory creating an ``analyses.Analysis`` owned by a user.

    Uses the ORM via string model refs so the imagery app does not import the
    projects/analyses apps directly.
    """
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
