"""Tests for :func:`ml.inference.vectorize.mask_to_features`."""

from __future__ import annotations

import numpy as np
import pytest
from rasterio.transform import from_origin  # type: ignore[import-untyped]

from ml.inference.vectorize import mask_to_features

# UTM zone 32N, 0.5 m/px grid so pixel area = 0.25 m^2.
_CRS = "EPSG:32632"
_RES = 0.5
_TRANSFORM = from_origin(500_000.0, 5_400_000.0, _RES, _RES)


def _make_mask() -> np.ndarray:
    """Build a mask with one large square (>= 20 m^2) and one tiny speck."""
    mask = np.zeros((100, 100), dtype=bool)
    mask[10:30, 10:30] = True  # 20x20 px = 400 px * 0.25 = 100 m^2
    mask[70:72, 70:72] = True  # 2x2 px = 4 px * 0.25 = 1 m^2 (< 20)
    return mask


def test_produces_polygons_and_area_filter() -> None:
    """Only the large square survives the 20 m^2 minimum-area filter."""
    gdf = mask_to_features(
        _make_mask(), _TRANSFORM, _CRS, simplify_tol_m=0.0, min_area_m2=20.0
    )
    assert len(gdf) == 1
    assert set(gdf.columns) == {
        "geometry",
        "area_m2",
        "centroid_lon",
        "centroid_lat",
        "confidence",
    }
    assert gdf["area_m2"].iloc[0] == pytest.approx(100.0, rel=0.05)


def test_centroid_in_wgs84() -> None:
    """Centroid lon/lat are plausible EPSG:4326 values near the raster."""
    gdf = mask_to_features(
        _make_mask(), _TRANSFORM, _CRS, simplify_tol_m=0.0, min_area_m2=20.0
    )
    lon = gdf["centroid_lon"].iloc[0]
    lat = gdf["centroid_lat"].iloc[0]
    assert -180 <= lon <= 180
    assert -90 <= lat <= 90
    # UTM 32N easting 500000 is on the central meridian (9E); ~48.7N.
    assert 8.0 <= lon <= 10.0
    assert 48.0 <= lat <= 49.5


def test_confidence_from_prob() -> None:
    """When a probability map is supplied, confidence is its in-polygon mean."""
    mask = _make_mask()
    prob = np.zeros_like(mask, dtype=np.float32)
    prob[10:30, 10:30] = 0.8
    gdf = mask_to_features(
        mask, _TRANSFORM, _CRS, simplify_tol_m=0.0, min_area_m2=20.0, prob=prob
    )
    assert gdf["confidence"].iloc[0] == pytest.approx(0.8, rel=0.1)


def test_empty_mask_returns_empty_frame() -> None:
    """An all-False mask returns an empty, correctly-typed GeoDataFrame."""
    empty = np.zeros((50, 50), dtype=bool)
    gdf = mask_to_features(empty, _TRANSFORM, _CRS, simplify_tol_m=0.0)
    assert len(gdf) == 0
    assert "geometry" in gdf.columns


def test_none_crs_raises() -> None:
    """A None CRS raises ValueError (UTM estimation needs a CRS)."""
    with pytest.raises(ValueError):
        mask_to_features(_make_mask(), _TRANSFORM, None, simplify_tol_m=0.0)


def test_output_geometry_is_valid() -> None:
    """Emitted geometry is valid (repaired)."""
    gdf = mask_to_features(
        _make_mask(), _TRANSFORM, _CRS, simplify_tol_m=0.0, min_area_m2=20.0
    )
    assert bool(gdf.geometry.is_valid.all())
