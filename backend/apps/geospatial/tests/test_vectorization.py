"""Tests for :class:`VectorizationService` wrapping ``ml.inference.vectorize``.

Runs the real ML vectorizer on a small synthetic mask and asserts the returned
unsaved :class:`Building` instances carry sensible area/centroid/index. Requires
the geo stack (rasterio, geopandas, GDAL); skipped otherwise.
"""

from __future__ import annotations

import pytest

pytest.importorskip("rasterio")
pytest.importorskip("geopandas")

np = pytest.importorskip("numpy")


def _synthetic_mask_transform() -> tuple[object, object, str]:
    """Return a mask with one ~20x20 m block, its transform, and CRS."""
    from rasterio.transform import from_origin

    mask = np.zeros((100, 100), dtype=bool)
    mask[20:60, 20:60] = True  # 40 px * 0.5 m = 20 m per side -> 400 m^2
    transform = from_origin(500000.0, 5400000.0, 0.5, 0.5)
    return mask, transform, "EPSG:32632"


def test_mask_to_features_returns_buildings() -> None:
    """The service returns Building instances with area/centroid/index set."""
    from apps.geospatial.services import VectorizationService

    mask, transform, crs = _synthetic_mask_transform()
    buildings = VectorizationService(simplify_tol_m=0.0).mask_to_features(mask, transform, crs)

    assert len(buildings) == 1
    building = buildings[0]
    assert building.index == 0
    assert building.area_m2 == pytest.approx(400.0, rel=0.15)
    assert building.geometry.srid == 4326
    assert building.centroid.srid == 4326
    # Centroid longitude for UTM 32N easting 500000 is ~9 deg E.
    assert 8.9 < building.centroid.x < 9.1


def test_empty_mask_returns_no_buildings() -> None:
    """An all-false mask yields an empty building list."""
    from rasterio.transform import from_origin

    from apps.geospatial.services import VectorizationService

    mask = np.zeros((50, 50), dtype=bool)
    transform = from_origin(500000.0, 5400000.0, 0.5, 0.5)
    buildings = VectorizationService().mask_to_features(mask, transform, "EPSG:32632")
    assert buildings == []
