"""Convert a boolean building mask into a validated GeoDataFrame of polygons.

Ports and hardens the canonical vectorization from ``CONTEXT.md`` sections 1
and 3: ``rasterio.features.shapes`` -> shapely geometries -> validity filtering
with ``make_valid`` (fallback ``buffer(0)``) -> bounded simplify -> metric area
via UTM reprojection -> drop ``area_m2 < min_area_m2`` -> UTM centroid reprojected
to EPSG:4326.
"""

from __future__ import annotations

import logging
from typing import Any

import geopandas as gpd  # type: ignore[import-untyped]
import numpy as np
from rasterio.features import shapes as raster_shapes  # type: ignore[import-untyped]
from shapely.geometry import shape as shapely_shape  # type: ignore[import-untyped]
from shapely.geometry.base import BaseGeometry  # type: ignore[import-untyped]

try:  # shapely >= 2.0
    from shapely import make_valid as _make_valid  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover - very old shapely
    _make_valid = None

logger = logging.getLogger(__name__)

_WGS84 = "EPSG:4326"


def _repair(geom: BaseGeometry) -> BaseGeometry:
    """Repair an invalid geometry using make_valid, falling back to buffer(0)."""
    if geom.is_valid:
        return geom
    if _make_valid is not None:
        try:
            repaired = _make_valid(geom)
            if not repaired.is_empty:
                return repaired
        except (ValueError, TypeError) as exc:  # pragma: no cover - defensive
            logger.debug(
                "make_valid failed; falling back to buffer(0)",
                extra={"error": str(exc)},
            )
    return geom.buffer(0)


def mask_to_features(
    mask: np.ndarray,
    transform: Any,
    crs: Any,
    simplify_tol_m: float,
    min_area_m2: float = 20.0,
    prob: np.ndarray | None = None,
) -> gpd.GeoDataFrame:
    """Vectorize a boolean mask into building polygons with metric attributes.

    Args:
        mask: 2-D boolean (or 0/1) array; ``True`` marks building pixels.
        transform: Affine transform mapping pixel to source-CRS coordinates.
        crs: Source coordinate reference system (must not be ``None``).
        simplify_tol_m: Simplification tolerance in metres (applied in UTM);
            ``<= 0`` disables simplification.
        min_area_m2: Drop polygons whose area is below this (m^2).
        prob: Optional probability map aligned with ``mask`` used to compute a
            per-polygon mean ``confidence``. When ``None``, confidence is ``None``.

    Returns:
        A GeoDataFrame in the source ``crs`` (4326-friendly) with columns
        ``geometry``, ``area_m2``, ``centroid_lon``, ``centroid_lat``,
        ``confidence``. Empty input yields an empty, correctly-typed frame.

    Raises:
        ValueError: If ``crs`` is ``None`` (needed for UTM estimation) or ``mask``
            is not 2-dimensional.
    """
    if crs is None:
        raise ValueError("crs must not be None; UTM area estimation requires a CRS")
    if mask.ndim != 2:
        raise ValueError(f"expected a 2-D mask, got shape {mask.shape!r}")

    columns = ["geometry", "area_m2", "centroid_lon", "centroid_lat", "confidence"]
    bool_mask = mask.astype(bool)

    if not bool_mask.any():
        logger.debug("empty mask -> no features")
        return gpd.GeoDataFrame({c: [] for c in columns}, geometry="geometry", crs=crs)

    geoms: list[BaseGeometry] = []
    uint8_mask = bool_mask.astype(np.uint8)
    for geom_json, value in raster_shapes(
        uint8_mask, mask=bool_mask, transform=transform
    ):
        if value != 1:
            continue
        geom = shapely_shape(geom_json)
        if geom is None or geom.is_empty:
            continue
        geom = _repair(geom)
        if geom.is_empty:
            continue
        geoms.append(geom)

    if not geoms:
        return gpd.GeoDataFrame({c: [] for c in columns}, geometry="geometry", crs=crs)

    gdf = gpd.GeoDataFrame(geometry=geoms, crs=crs)

    utm_crs = gdf.estimate_utm_crs()
    gdf_utm = gdf.to_crs(utm_crs)

    if simplify_tol_m > 0:
        gdf_utm["geometry"] = gdf_utm.geometry.simplify(
            simplify_tol_m, preserve_topology=True
        )
        gdf_utm = gdf_utm[~gdf_utm.geometry.is_empty & gdf_utm.geometry.notnull()]

    gdf_utm["area_m2"] = gdf_utm.geometry.area
    gdf_utm = gdf_utm[gdf_utm["area_m2"] >= min_area_m2]

    if gdf_utm.empty:
        return gpd.GeoDataFrame({c: [] for c in columns}, geometry="geometry", crs=crs)

    centroids_utm = gdf_utm.geometry.centroid
    centroids_wgs = centroids_utm.to_crs(_WGS84)
    gdf_utm["centroid_lon"] = centroids_wgs.x.to_numpy()
    gdf_utm["centroid_lat"] = centroids_wgs.y.to_numpy()

    # Reproject repaired/simplified geometry back to the source CRS for output.
    result = gdf_utm.to_crs(crs)
    result["area_m2"] = gdf_utm["area_m2"].to_numpy()
    result["centroid_lon"] = gdf_utm["centroid_lon"].to_numpy()
    result["centroid_lat"] = gdf_utm["centroid_lat"].to_numpy()

    if prob is not None:
        result["confidence"] = _polygon_confidences(result, prob, transform)
    else:
        result["confidence"] = [None] * len(result)

    result = result.reset_index(drop=True)
    return result[columns]


def _polygon_confidences(
    gdf: gpd.GeoDataFrame,
    prob: np.ndarray,
    transform: Any,
) -> list[float | None]:
    """Compute mean probability inside each polygon by rasterizing it.

    Args:
        gdf: GeoDataFrame whose geometries are in the raster's source CRS.
        prob: Probability map aligned with the raster grid.
        transform: Affine transform for the raster grid.

    Returns:
        A list of per-polygon mean probabilities (``None`` where no pixels hit).
    """
    from rasterio.features import geometry_mask

    out: list[float | None] = []
    for geom in gdf.geometry:
        poly_mask = ~geometry_mask(
            [geom], out_shape=prob.shape, transform=transform, invert=False
        )
        if poly_mask.any():
            out.append(float(prob[poly_mask].mean()))
        else:
            out.append(None)
    return out


__all__ = ["mask_to_features"]
