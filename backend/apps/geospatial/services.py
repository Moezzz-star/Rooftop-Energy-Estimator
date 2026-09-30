"""Domain services for the geospatial app.

Service classes (code-architecture §6, each with injected dependencies):

* :class:`GeometryValidationService` — validate/repair GeoJSON polygons and
  compute metric area via UTM reprojection (#10).
* :class:`VectorizationService` — wrap the pure ``ml.inference.vectorize`` and
  convert its GeoDataFrame rows into unsaved :class:`Building` instances.
* :class:`BuildingPersistenceService` — bulk-persist buildings (+ roofs).
* :class:`DataQualityService` — transparent, non-calibrated data-quality
  summary for an analysis (#16).
* :class:`BuildingProjectionService` — bbox filtering + zoom-dependent simplify
  for map-ready GeoJSON, with a hard feature cap (#19).

Geometry is stored in EPSG:4326; metric work happens here via on-the-fly UTM
reprojection (matching ``estimate_utm_crs`` semantics). Third-party errors are
mapped to :class:`common.errors` at the boundary.
"""

from __future__ import annotations

from typing import Any, cast

from django.db.models import QuerySet

from common.errors import InfrastructureError, ValidationError
from common.logging import get_logger

from .models import Building, RoofGeometry

logger = get_logger("geospatial.service")

_WGS84 = "EPSG:4326"


def _utm_epsg(lon: float, lat: float) -> str:
    """Return the EPSG code of the UTM zone containing ``(lon, lat)``."""
    zone = int((lon + 180.0) / 6.0) + 1
    zone = min(max(zone, 1), 60)
    prefix = 32600 if lat >= 0 else 32700
    return f"EPSG:{prefix + zone}"


class GeometryValidationService:
    """Validate and repair GeoJSON polygons and compute their metric area.

    Args:
        min_area_m2: Minimum sensible polygon area (m^2); polygons below this
            are still reported (with a warning flag) but not rejected.
        max_area_km2: Bounded upper guard (km^2). Polygons whose UTM area
            exceeds this are reported ``valid=false`` with an
            ``exceeds_max_area`` warning rather than raising (no 500).
    """

    def __init__(self, min_area_m2: float = 20.0, max_area_km2: float = 100.0) -> None:
        self._min_area_m2 = min_area_m2
        self._max_area_m2 = max_area_km2 * 1_000_000.0

    def validate(self, geojson: dict[str, Any]) -> dict[str, Any]:
        """Validate one or more GeoJSON polygons.

        Args:
            geojson: A GeoJSON ``Geometry``, ``Feature``, or
                ``FeatureCollection`` (coordinates assumed EPSG:4326).

        Returns:
            A summary dict ``{valid, count, total_area_m2, features:[...]}``
            where each feature entry carries ``valid``, ``area_m2``,
            ``repairs`` (list of applied repair operations), ``below_min_area``,
            and ``warnings`` (list of transparency flags such as
            ``below_min_area``, ``exceeds_max_area``,
            ``self_intersection_repaired``).

        Raises:
            ValidationError: If the payload contains no usable polygon, or a
                non-polygon geometry (Point/LineString) is supplied.
        """
        geometries = self._extract_geometries(geojson)
        if not geometries:
            raise ValidationError(
                "No polygon geometry found in the payload.",
                details={"geojson": "expected Polygon/MultiPolygon"},
            )

        features = [self._validate_one(geom) for geom in geometries]
        total_area = sum(f["area_m2"] for f in features)
        result = {
            "valid": all(f["valid"] for f in features),
            "count": len(features),
            "total_area_m2": total_area,
            "features": features,
        }
        logger.info("Geometry validation completed", extra={"stage": "VALIDATE_REQUEST"})
        return result

    def _validate_one(self, geom_mapping: dict[str, Any]) -> dict[str, Any]:
        """Validate/repair a single geometry mapping and compute its area."""
        from shapely.geometry import shape as shapely_shape

        try:
            geom = shapely_shape(geom_mapping)
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValidationError(
                "Geometry could not be parsed.", details={"error": str(exc)}
            ) from exc

        if geom.geom_type not in ("Polygon", "MultiPolygon"):
            raise ValidationError(
                "Only Polygon/MultiPolygon geometries are supported.",
                details={"geom_type": geom.geom_type},
            )

        if geom.is_empty:
            raise ValidationError("Geometry is empty.")

        geom, repairs = self._repair(geom)
        area_m2 = self._utm_area(geom)
        warnings = self._warnings(area_m2, repairs)
        within_bounds = area_m2 <= self._max_area_m2
        return {
            "valid": geom.is_valid and not geom.is_empty and within_bounds,
            "area_m2": area_m2,
            "repairs": repairs,
            "below_min_area": area_m2 < self._min_area_m2,
            "warnings": warnings,
        }

    def _warnings(self, area_m2: float, repairs: list[str]) -> list[str]:
        """Return transparency warning flags for a validated feature."""
        warnings: list[str] = []
        if area_m2 < self._min_area_m2:
            warnings.append("below_min_area")
        if area_m2 > self._max_area_m2:
            warnings.append("exceeds_max_area")
        if repairs:
            warnings.append("self_intersection_repaired")
        return warnings

    def _repair(self, geom: Any) -> tuple[Any, list[str]]:
        """Return ``(repaired_geom, repairs_applied)`` for ``geom``."""
        if geom.is_valid:
            return geom, []
        repairs: list[str] = []
        try:
            from shapely import make_valid

            repaired = make_valid(geom)
            if not repaired.is_empty:
                return repaired, ["make_valid"]
            repairs.append("make_valid_empty")
        except (ImportError, ValueError, TypeError):
            repairs.append("make_valid_unavailable")
        buffered = geom.buffer(0)
        repairs.append("buffer0")
        return buffered, repairs

    def _utm_area(self, geom: Any) -> float:
        """Compute ``geom``'s area in m^2 via UTM reprojection."""
        from shapely.ops import transform as shapely_transform

        rep = geom.representative_point()
        utm = _utm_epsg(rep.x, rep.y)
        try:
            from pyproj import Transformer

            transformer = Transformer.from_crs(_WGS84, utm, always_xy=True)
            projected = shapely_transform(transformer.transform, geom)
        except Exception as exc:  # pyproj/proj database errors
            logger.error("UTM reprojection failed during validation")
            raise InfrastructureError("Failed to reproject geometry for area computation.") from exc
        return float(projected.area)

    @staticmethod
    def _extract_geometries(geojson: dict[str, Any]) -> list[dict[str, Any]]:
        """Normalize a GeoJSON payload into a list of geometry mappings."""
        if not isinstance(geojson, dict):
            raise ValidationError("A GeoJSON object is required.")
        gtype = geojson.get("type")
        if gtype == "FeatureCollection":
            return [
                f["geometry"]
                for f in geojson.get("features", [])
                if isinstance(f, dict) and f.get("geometry")
            ]
        if gtype == "Feature":
            geometry = geojson.get("geometry")
            return [geometry] if geometry else []
        if gtype in ("Polygon", "MultiPolygon"):
            return [geojson]
        return []


class VectorizationService:
    """Wrap the pure ``ml.inference.vectorize.mask_to_features``.

    Converts the resulting GeoDataFrame rows into *unsaved* :class:`Building`
    instances (geometry reprojected to EPSG:4326). Persistence is the caller's
    responsibility (the jobs pipeline calls :class:`BuildingPersistenceService`).

    Args:
        simplify_tol_m: Default simplification tolerance (m) passed to the ML
            vectorizer; ``<= 0`` disables simplification.
        min_area_m2: Default minimum polygon area (m^2); MUST-ADD 20 m^2 filter.
    """

    def __init__(self, simplify_tol_m: float = 0.5, min_area_m2: float = 20.0) -> None:
        self._simplify_tol_m = simplify_tol_m
        self._min_area_m2 = min_area_m2

    def mask_to_features(
        self,
        mask: Any,
        transform: Any,
        crs: Any,
        *,
        prob: Any | None = None,
        simplify_tol_m: float | None = None,
        min_area_m2: float | None = None,
    ) -> list[Building]:
        """Vectorize a boolean mask into unsaved :class:`Building` instances.

        Args:
            mask: 2-D boolean/0-1 array (``True`` = building pixel).
            transform: Affine transform mapping pixel to source-CRS coords.
            crs: Source CRS (must not be ``None``).
            prob: Optional probability map for per-polygon confidence.
            simplify_tol_m: Override for the simplify tolerance (m).
            min_area_m2: Override for the minimum area (m^2).

        Returns:
            A list of unsaved :class:`Building` instances ordered by ``index``.

        Raises:
            ValidationError: If the mask/CRS is unusable.
            InfrastructureError: If the ML vectorizer fails unexpectedly.
        """
        from ml.inference.vectorize import mask_to_features as ml_mask_to_features

        tol = self._simplify_tol_m if simplify_tol_m is None else simplify_tol_m
        min_area = self._min_area_m2 if min_area_m2 is None else min_area_m2

        try:
            gdf = ml_mask_to_features(
                mask, transform, crs, simplify_tol_m=tol, min_area_m2=min_area, prob=prob
            )
        except ValueError as exc:
            raise ValidationError(
                "Mask/CRS is unusable for vectorization.", details={"error": str(exc)}
            ) from exc
        except Exception as exc:  # rasterio/geopandas failures
            logger.error("Vectorization failed", extra={"stage": "VECTORIZE"})
            raise InfrastructureError("Vectorization failed.") from exc

        return self._to_buildings(gdf)

    def _to_buildings(self, gdf: Any) -> list[Building]:
        """Convert a 4326-reprojected GeoDataFrame into unsaved buildings."""
        from django.contrib.gis.geos import GEOSGeometry, Point, Polygon

        if gdf.empty:
            logger.info("Vectorization produced no features", extra={"stage": "VECTORIZE"})
            return []

        gdf_4326 = gdf.to_crs(_WGS84)
        buildings: list[Building] = []
        for index, (_, row) in enumerate(gdf_4326.iterrows()):
            geometry = GEOSGeometry(row.geometry.wkb_hex, srid=4326)
            centroid = Point(float(row["centroid_lon"]), float(row["centroid_lat"]), srid=4326)
            confidence = row["confidence"]
            buildings.append(
                Building(
                    geometry=cast(Polygon, geometry),
                    centroid=centroid,
                    area_m2=float(row["area_m2"]),
                    confidence=None if confidence is None else float(confidence),
                    index=index,
                )
            )
        logger.info("Vectorized %d building(s)", len(buildings), extra={"stage": "VECTORIZE"})
        return buildings


class BuildingPersistenceService:
    """Bulk-persist buildings (and optional roof geometries)."""

    def persist(
        self,
        analysis: Any,
        buildings: list[Building],
        roofs: list[RoofGeometry] | None = None,
    ) -> list[Building]:
        """Persist ``buildings`` under ``analysis`` and any aligned ``roofs``.

        Args:
            analysis: The owning ``analyses.Analysis`` instance.
            buildings: Unsaved :class:`Building` instances.
            roofs: Optional :class:`RoofGeometry` instances aligned 1:1 with
                ``buildings`` by position (their ``building`` is set here).

        Returns:
            The persisted buildings.
        """
        if not buildings:
            return []
        for building in buildings:
            building.analysis = analysis
        created = Building.objects.bulk_create(buildings)
        logger.info(
            "Persisted %d building(s)",
            len(created),
            extra={"analysis_id": str(analysis.pk), "stage": "PERSIST_ARTIFACTS"},
        )
        if roofs:
            for roof, building in zip(roofs, created, strict=False):
                roof.building = building
            RoofGeometry.objects.bulk_create(roofs)
        return created


class DataQualityService:
    """Compute a transparent, NON-calibrated data-quality summary (§16).

    The returned ``indicator`` (``high``/``medium``/``low``) is a heuristic
    aggregate of observable factors — it is deliberately NOT a calibrated
    confidence interval and must never be presented as one (see ``notes``).

    Fields on the imagery model are read defensively (``getattr`` + fallbacks)
    because the imagery schema is being extended in parallel.

    Args:
        min_area_m2: Threshold below which a building's footprint is flagged.
        low_confidence: Segmentation confidence below which a building is
            flagged / the confidence factor is scored poorly.
        good_resolution_m: GSD at or below which imagery is ``good``.
        medium_resolution_m: GSD at or below which imagery is ``medium``.
    """

    _NOTE_TRANSPARENCY = (
        "Data quality is a transparent heuristic derived from observable "
        "inputs; it is not a calibrated confidence interval or a guarantee of "
        "accuracy."
    )

    def __init__(
        self,
        min_area_m2: float = 20.0,
        low_confidence: float = 0.5,
        good_resolution_m: float = 0.3,
        medium_resolution_m: float = 1.0,
    ) -> None:
        self._min_area_m2 = min_area_m2
        self._low_confidence = low_confidence
        self._good_resolution_m = good_resolution_m
        self._medium_resolution_m = medium_resolution_m

    def summarize(self, analysis: Any) -> dict[str, Any]:
        """Return a data-quality summary for ``analysis``.

        Args:
            analysis: The owning ``analyses.Analysis`` instance.

        Returns:
            ``{"indicator": ..., "factors": {...}, "notes": [...]}``.
        """
        buildings = Building.objects.filter(analysis=analysis)
        factors: dict[str, Any] = {
            "imagery_resolution": self._resolution_factor(analysis),
            "imagery_age": self._age_factor(analysis),
            "segmentation_confidence": self._confidence_factor(buildings),
            "polygon_validity": self._validity_factor(buildings),
            "missing_orientation": self._orientation_factor(buildings),
        }
        notes = [self._NOTE_TRANSPARENCY]
        indicator = self._indicator(factors, notes)
        logger.info(
            "Computed data-quality summary",
            extra={"analysis_id": str(getattr(analysis, "pk", "?")), "stage": "PUBLISH_RESULTS"},
        )
        return {"indicator": indicator, "factors": factors, "notes": notes}

    def building_warnings(self, building: Building) -> list[str]:
        """Return per-building transparency warnings (#18).

        Flags low/missing segmentation confidence, missing roof orientation,
        below-minimum footprint area, and invalid stored geometry.
        """
        warnings: list[str] = []
        confidence = building.confidence
        if confidence is None:
            warnings.append("missing_confidence")
        elif confidence < self._low_confidence:
            warnings.append("low_confidence")
        if not self._has_orientation(building):
            warnings.append("missing_orientation")
        if building.area_m2 is not None and building.area_m2 < self._min_area_m2:
            warnings.append("below_min_area")
        geometry = building.geometry
        if geometry is not None and not geometry.valid:
            warnings.append("invalid_geometry")
        return warnings

    def _resolution_factor(self, analysis: Any) -> dict[str, Any]:
        """Classify imagery ground sample distance for ``analysis``."""
        resolution = self._imagery_attr(analysis, "resolution_m")
        if resolution is None:
            return {"value_m": None, "class": "unknown"}
        if resolution <= self._good_resolution_m:
            grade = "good"
        elif resolution <= self._medium_resolution_m:
            grade = "medium"
        else:
            grade = "poor"
        return {"value_m": float(resolution), "class": grade}

    def _age_factor(self, analysis: Any) -> dict[str, Any]:
        """Classify imagery acquisition age for ``analysis``."""
        from django.utils import timezone

        acquired_at = self._imagery_attr(analysis, "acquired_at")
        if acquired_at is None:
            return {"acquired_at": None, "class": "unknown"}
        try:
            age_days = (timezone.now() - acquired_at).days
        except (TypeError, ValueError):
            return {"acquired_at": str(acquired_at), "class": "unknown"}
        if age_days <= 730:
            grade = "good"
        elif age_days <= 1825:
            grade = "medium"
        else:
            grade = "poor"
        return {"acquired_at": acquired_at.isoformat(), "age_days": age_days, "class": grade}

    def _confidence_factor(self, buildings: QuerySet[Building]) -> dict[str, Any]:
        """Aggregate segmentation confidence across ``buildings``."""
        from django.db.models import Avg, Count, Min

        agg = buildings.aggregate(
            mean=Avg("confidence"),
            min=Min("confidence"),
            count_with_confidence=Count("confidence"),
        )
        mean = agg["mean"]
        count = agg["count_with_confidence"] or 0
        if count == 0 or mean is None:
            grade = "unknown"
        elif mean >= 0.8:
            grade = "good"
        elif mean >= self._low_confidence:
            grade = "medium"
        else:
            grade = "poor"
        return {
            "mean": None if mean is None else float(mean),
            "min": None if agg["min"] is None else float(agg["min"]),
            "count_with_confidence": count,
            "class": grade,
        }

    def _validity_factor(self, buildings: QuerySet[Building]) -> dict[str, Any]:
        """Compute the fraction of buildings with valid stored geometry."""
        total = 0
        valid = 0
        for building in buildings.only("id", "geometry").iterator():
            total += 1
            geometry = building.geometry
            if geometry is not None and geometry.valid:
                valid += 1
        if total == 0:
            return {"valid_fraction": None, "count": 0, "class": "unknown"}
        fraction = valid / total
        if fraction >= 0.95:
            grade = "good"
        elif fraction >= 0.8:
            grade = "medium"
        else:
            grade = "poor"
        return {"valid_fraction": fraction, "count": total, "class": grade}

    def _orientation_factor(self, buildings: QuerySet[Building]) -> dict[str, Any]:
        """Compute the fraction of buildings lacking roof orientation."""
        total = buildings.count()
        if total == 0:
            return {"fraction_missing": None, "count": 0, "class": "unknown"}
        with_orientation = RoofGeometry.objects.filter(
            building__in=buildings,
            tilt_deg__isnull=False,
            azimuth_deg__isnull=False,
        ).count()
        fraction_missing = (total - with_orientation) / total
        if fraction_missing <= 0.1:
            grade = "good"
        elif fraction_missing <= 0.5:
            grade = "medium"
        else:
            grade = "poor"
        return {"fraction_missing": fraction_missing, "count": total, "class": grade}

    def _indicator(self, factors: dict[str, Any], notes: list[str]) -> str:
        """Aggregate factor grades into an overall high/medium/low indicator."""
        scores = {"good": 2, "medium": 1, "poor": 0}
        graded = [scores[f["class"]] for f in factors.values() if f["class"] in scores]
        if not graded:
            notes.append("Insufficient data to assess quality; defaulting to 'low'.")
            return "low"
        average = sum(graded) / len(graded)
        if average >= 1.5:
            return "high"
        if average >= 0.75:
            return "medium"
        return "low"

    @staticmethod
    def _imagery_attr(analysis: Any, attr: str) -> Any:
        """Return ``attr`` from the analysis's first imagery asset, or ``None``."""
        manager = getattr(analysis, "imagery_assets", None)
        if manager is None:
            return None
        try:
            asset = manager.first()
        except Exception:  # defensive: relation may be mid-migration
            return None
        return None if asset is None else getattr(asset, attr, None)

    @staticmethod
    def _has_orientation(building: Building) -> bool:
        """Return whether ``building`` has a roof with tilt and azimuth."""
        roof = getattr(building, "roof", None)
        if roof is None:
            return False
        return getattr(roof, "tilt_deg", None) is not None and (
            getattr(roof, "azimuth_deg", None) is not None
        )


class BuildingProjectionService:
    """Build map-ready GeoJSON with bbox filtering and zoom-dependent simplify.

    Args:
        max_features: Hard cap on features per response (#19); exceeding it is
            a client error (the caller should tighten the bbox/zoom).
    """

    def __init__(self, max_features: int = 2000) -> None:
        self._max_features = max_features

    def simplify_tol_for_zoom(self, zoom: int) -> float:
        """Return a degree-space simplify tolerance for a web-map ``zoom``.

        Lower zoom (further out) -> coarser tolerance. Bounded to keep polygons
        recognisable at all zoom levels.
        """
        zoom = max(0, min(zoom, 22))
        # ~1.5e-2 deg at z0 down to ~0 near z18; monotone decreasing.
        return float(max(0.0, 1.5e-2 / (2 ** max(zoom - 4, 0))))

    def to_feature_collection(
        self,
        buildings: list[Building],
        *,
        simplify_tol_deg: float = 0.0,
    ) -> dict[str, Any]:
        """Serialize ``buildings`` into a GeoJSON ``FeatureCollection``.

        Args:
            buildings: Buildings to include (already bbox-filtered upstream).
            simplify_tol_deg: Simplification tolerance in degrees; ``<= 0``
                keeps full geometry.

        Returns:
            A GeoJSON ``FeatureCollection`` mapping.

        Raises:
            ValidationError: If the feature count exceeds ``max_features``.
        """
        count = len(buildings)
        if count > self._max_features:
            raise ValidationError(
                "Too many features for a single response; tighten the bbox or zoom.",
                details={"count": count, "max_features": self._max_features},
            )
        features = [self._feature(b, simplify_tol_deg) for b in buildings]
        return {"type": "FeatureCollection", "features": features}

    def _feature(self, building: Building, simplify_tol_deg: float) -> dict[str, Any]:
        """Build a single GeoJSON feature for ``building``."""
        import json

        from django.contrib.gis.geos import GEOSGeometry

        geometry: GEOSGeometry = building.geometry
        if simplify_tol_deg > 0:
            geometry = geometry.simplify(simplify_tol_deg, preserve_topology=True)
        return {
            "type": "Feature",
            "id": str(building.pk),
            "geometry": json.loads(geometry.geojson),
            "properties": {
                "index": building.index,
                "area_m2": building.area_m2,
                "confidence": building.confidence,
            },
        }


__all__ = [
    "BuildingPersistenceService",
    "BuildingProjectionService",
    "DataQualityService",
    "GeometryValidationService",
    "VectorizationService",
]
