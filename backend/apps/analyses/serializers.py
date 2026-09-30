"""DRF serializers for the analyses app.

Serializers validate and shape data only; all lifecycle logic lives in
:mod:`apps.analyses.services`. GeoJSON is parsed/emitted manually with
``django.contrib.gis.geos.GEOSGeometry`` (no ``rest_framework_gis`` dependency).
"""

from __future__ import annotations

import json
from typing import Any, cast

from django.contrib.gis.geos import GEOSGeometry
from django.contrib.gis.geos.error import GEOSException
from rest_framework import serializers

from .models import ASSUMPTION_DEFAULTS, Analysis, AnalysisArea, AnalysisAssumption

_POLYGON_TYPES = frozenset({"Polygon", "MultiPolygon"})


def _parse_geojson_geometry(value: Any) -> GEOSGeometry:
    """Parse a GeoJSON geometry mapping into a 4326 GEOS geometry.

    Args:
        value: A GeoJSON geometry object (dict) of type Polygon/MultiPolygon.

    Returns:
        The parsed :class:`GEOSGeometry` with SRID 4326.

    Raises:
        serializers.ValidationError: If the input is not a valid GeoJSON
            polygon/multipolygon geometry.
    """
    if not isinstance(value, dict):
        raise serializers.ValidationError("Area must be a GeoJSON geometry object.")
    geom_type = value.get("type")
    if geom_type not in _POLYGON_TYPES:
        raise serializers.ValidationError("Area geometry type must be Polygon or MultiPolygon.")
    try:
        geom = GEOSGeometry(json.dumps(value))
    except (GEOSException, ValueError, TypeError) as exc:
        raise serializers.ValidationError("Area is not valid GeoJSON.") from exc
    if geom.srid is None:
        geom.srid = 4326
    return geom


class AnalysisAssumptionSerializer(serializers.ModelSerializer[AnalysisAssumption]):
    """Serialize an analysis's classified assumptions (read-only)."""

    class Meta:
        model = AnalysisAssumption
        fields = (
            "source",
            "usable_roof_fraction",
            "power_density_w_m2",
            "system_losses",
            "module_eff",
            "tilt_deg",
            "azimuth_deg",
            "shading",
            "temp_air",
            "wind",
        )
        read_only_fields = fields


class AnalysisAreaSerializer(serializers.ModelSerializer[AnalysisArea]):
    """Serialize an analysis area with GeoJSON geometry output."""

    area = serializers.SerializerMethodField()

    class Meta:
        model = AnalysisArea
        fields = ("id", "label", "area")
        read_only_fields = fields

    def get_area(self, obj: AnalysisArea) -> dict[str, Any]:
        """Return the area geometry as a GeoJSON mapping."""
        return cast(dict[str, Any], json.loads(obj.area.geojson))


class AnalysisSerializer(serializers.ModelSerializer[Analysis]):
    """Full read representation of an analysis.

    Surfaces the frozen DEC-09 ``snapshot`` (pinned model/calculation versions,
    frozen assumptions, code commit, imagery metadata) so the results workspace
    can display the exact methodology used, plus the immutable ``assumption``
    row and the canonical DEC-01 ``assumption_defaults`` for the editor form.
    """

    areas = AnalysisAreaSerializer(many=True, read_only=True)
    assumption = AnalysisAssumptionSerializer(read_only=True)
    assumption_defaults = serializers.SerializerMethodField()

    class Meta:
        model = Analysis
        fields = (
            "id",
            "name",
            "status",
            "project",
            "idempotency_key",
            "submitted_at",
            "completed_at",
            "model_version",
            "calculation_version",
            "snapshot",
            "areas",
            "assumption",
            "assumption_defaults",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_assumption_defaults(self, obj: Analysis) -> dict[str, float]:
        """Return the DEC-01 default assumptions for rendering the form."""
        return dict(ASSUMPTION_DEFAULTS)


class AnalysisCreateSerializer(serializers.Serializer[Any]):
    """Validate the payload for creating a draft analysis."""

    name = serializers.CharField(max_length=200)
    area = serializers.JSONField()
    assumptions = serializers.DictField(required=False)

    def validate_area(self, value: Any) -> GEOSGeometry:
        """Parse and validate the GeoJSON area geometry."""
        return _parse_geojson_geometry(value)


class AnalysisUpdateSerializer(serializers.Serializer[Any]):
    """Validate a draft-only partial update of an analysis."""

    name = serializers.CharField(max_length=200, required=False)
    area = serializers.JSONField(required=False)
    assumptions = serializers.DictField(required=False)

    def validate_area(self, value: Any) -> GEOSGeometry:
        """Parse and validate the GeoJSON area geometry."""
        return _parse_geojson_geometry(value)
