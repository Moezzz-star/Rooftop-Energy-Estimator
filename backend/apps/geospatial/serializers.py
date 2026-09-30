"""DRF serializers for the geospatial app.

Serializers validate and shape data only (code-architecture §6). Geometry is
excluded from the tabular building representation by default and only included
(simplified) on explicit opt-in, per the "bounding unbounded GeoJSON" rule (§4).
"""

from __future__ import annotations

import json
from typing import Any, cast

from django.contrib.gis.geos import GEOSGeometry
from rest_framework import serializers

from .models import Building, RoofGeometry


class GeometryValidateSerializer(serializers.Serializer[dict[str, Any]]):
    """Validate the request body for the geometry-validation endpoint (#10)."""

    geojson = serializers.JSONField()


class RoofGeometrySerializer(serializers.ModelSerializer[RoofGeometry]):
    """Nested representation of a building's roof geometry."""

    class Meta:
        model = RoofGeometry
        fields = ["id", "tilt_deg", "azimuth_deg", "usable_area_m2", "source"]
        read_only_fields = fields


class BuildingSerializer(serializers.ModelSerializer[Building]):
    """Tabular building row; geometry omitted by default (opt-in simplified).

    Pass ``context={"include_geometry": True}`` to embed a simplified geometry
    (tolerance from ``context["simplify_tol_deg"]``, default ``0`` = full).
    """

    centroid_lon = serializers.SerializerMethodField()
    centroid_lat = serializers.SerializerMethodField()
    geometry = serializers.SerializerMethodField()

    class Meta:
        model = Building
        fields = [
            "id",
            "index",
            "area_m2",
            "confidence",
            "centroid_lon",
            "centroid_lat",
            "geometry",
        ]
        read_only_fields = fields

    def get_centroid_lon(self, obj: Building) -> float | None:
        """Return the centroid longitude (EPSG:4326)."""
        return None if obj.centroid is None else float(obj.centroid.x)

    def get_centroid_lat(self, obj: Building) -> float | None:
        """Return the centroid latitude (EPSG:4326)."""
        return None if obj.centroid is None else float(obj.centroid.y)

    def get_geometry(self, obj: Building) -> dict[str, Any] | None:
        """Return a (possibly simplified) GeoJSON geometry, or ``None``.

        Geometry is only emitted when the view opts in via context, keeping the
        default tabular payload lightweight.
        """
        if not self.context.get("include_geometry"):
            return None
        geometry: GEOSGeometry = obj.geometry
        tol = float(self.context.get("simplify_tol_deg", 0.0))
        if tol > 0:
            geometry = geometry.simplify(tol, preserve_topology=True)
        return cast("dict[str, Any]", json.loads(geometry.geojson))


class BuildingDetailSerializer(BuildingSerializer):
    """Full building detail: roof, solar, and flattened §9 fields (#18).

    Exposes the §9 building fields that are available (usable area, orientation,
    shading, capacity, energy, yield), the nested roof and solar estimates, and
    a ``warnings`` list derived from data-quality factors for this building.

    Solar estimates belong to the ``solar`` app and are read via the
    ``solar_estimates`` reverse relation using ``getattr`` so this app never
    imports the solar app.
    """

    roof = RoofGeometrySerializer(read_only=True)
    solar_estimates = serializers.SerializerMethodField()
    usable_area_m2 = serializers.SerializerMethodField()
    tilt_deg = serializers.SerializerMethodField()
    azimuth_deg = serializers.SerializerMethodField()
    shading = serializers.SerializerMethodField()
    capacity_kwp = serializers.SerializerMethodField()
    annual_kwh = serializers.SerializerMethodField()
    monthly_kwh = serializers.SerializerMethodField()
    specific_yield = serializers.SerializerMethodField()
    warnings = serializers.SerializerMethodField()

    class Meta(BuildingSerializer.Meta):
        fields = [
            *BuildingSerializer.Meta.fields,
            "roof",
            "usable_area_m2",
            "tilt_deg",
            "azimuth_deg",
            "shading",
            "capacity_kwp",
            "annual_kwh",
            "monthly_kwh",
            "specific_yield",
            "solar_estimates",
            "warnings",
        ]

    def get_geometry(self, obj: Building) -> dict[str, Any] | None:
        """Always include full geometry in the detail representation."""
        return cast("dict[str, Any]", json.loads(obj.geometry.geojson))

    def get_usable_area_m2(self, obj: Building) -> Any:
        """Return the usable roof area (m^2) from the roof geometry."""
        roof = getattr(obj, "roof", None)
        return None if roof is None else roof.usable_area_m2

    def get_tilt_deg(self, obj: Building) -> Any:
        """Return the roof tilt (degrees) from the roof geometry."""
        roof = getattr(obj, "roof", None)
        return None if roof is None else roof.tilt_deg

    def get_azimuth_deg(self, obj: Building) -> Any:
        """Return the roof azimuth (degrees) from the roof geometry."""
        roof = getattr(obj, "roof", None)
        return None if roof is None else roof.azimuth_deg

    def get_shading(self, obj: Building) -> Any:
        """Return the shading factor from the solar estimate inputs, if any."""
        estimate = self._first_estimate(obj)
        inputs = getattr(estimate, "inputs", None)
        if isinstance(inputs, dict):
            return inputs.get("shading")
        return None

    def get_capacity_kwp(self, obj: Building) -> Any:
        """Return the installed capacity (kWp) from the solar estimate."""
        return getattr(self._first_estimate(obj), "capacity_kwp", None)

    def get_annual_kwh(self, obj: Building) -> Any:
        """Return the annual energy (kWh) from the solar estimate."""
        return getattr(self._first_estimate(obj), "annual_kwh", None)

    def get_monthly_kwh(self, obj: Building) -> Any:
        """Return the 12 monthly energy values from the solar estimate."""
        return getattr(self._first_estimate(obj), "monthly_kwh", None)

    def get_specific_yield(self, obj: Building) -> Any:
        """Return the specific yield (kWh/kWp) from the solar estimate."""
        return getattr(self._first_estimate(obj), "specific_yield", None)

    def get_warnings(self, obj: Building) -> list[str]:
        """Return data-quality warnings for this building (delegated to service)."""
        from .services import DataQualityService

        return DataQualityService().building_warnings(obj)

    def get_solar_estimates(self, obj: Building) -> list[dict[str, Any]]:
        """Return serialized solar estimates if the solar app is present."""
        manager = getattr(obj, "solar_estimates", None)
        if manager is None:
            return []
        return [self._solar_row(estimate) for estimate in manager.all()]

    @staticmethod
    def _first_estimate(obj: Building) -> Any:
        """Return the building's most relevant solar estimate, or ``None``."""
        manager = getattr(obj, "solar_estimates", None)
        return None if manager is None else manager.first()

    @staticmethod
    def _solar_row(estimate: Any) -> dict[str, Any]:
        """Shape a single solar estimate without importing its model."""
        fields = (
            "id",
            "capacity_kwp",
            "annual_kwh",
            "specific_yield",
            "usable_area_m2",
            "monthly_kwh",
            "disclaimer",
        )
        row: dict[str, Any] = {}
        for field in fields:
            value = getattr(estimate, field, None)
            row[field] = str(value) if field == "id" and value is not None else value
        return row
