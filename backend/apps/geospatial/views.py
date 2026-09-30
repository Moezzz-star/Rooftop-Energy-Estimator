"""HTTP views for the geospatial app.

Views are thin: they parse/validate query input, resolve objects, enforce
ownership, delegate to services/selectors, and shape responses. No business
logic lives here (code-architecture §6).

Endpoints: #10 geometry validate, #16 results summary, #17 buildings list,
#18 building detail, #19 map-ready features.

NOTE (routing): this app's ``urls.py`` is currently included under the
``/api/v1/geometry/`` prefix (see ``config/urls.py``). Only ``validate/`` is
meant to live there; #16/#17/#18/#19 are specified at ``/api/v1/analyses/...``
and ``/api/v1/buildings/...``. This is an INTEGRATION ISSUE for the Technical
Lead (owner of ``config/urls.py``) — see the handback report.
"""

from __future__ import annotations

from typing import Any

from django.apps import apps as django_apps
from django.shortcuts import get_object_or_404
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.logging import get_logger
from common.permissions import IsOwner

from .filters import parse_bbox, parse_float, parse_int
from .models import Building
from .selectors import get_building, list_buildings, results_summary
from .serializers import (
    BuildingDetailSerializer,
    BuildingSerializer,
    GeometryValidateSerializer,
)
from .services import BuildingProjectionService, GeometryValidationService

logger = get_logger("geospatial.views")


def _get_analysis(analysis_id: Any) -> Any:
    """Resolve an ``analyses.Analysis`` by id without importing the app."""
    model = django_apps.get_model("analyses", "Analysis")
    return get_object_or_404(model, pk=analysis_id)


class GeometryValidateView(APIView):
    """POST ``geometry/validate/`` — validate GeoJSON polygon(s) (#10)."""

    permission_classes = [IsAuthenticated]
    serializer_class = GeometryValidateSerializer

    def post(self, request: Request) -> Response:
        """Validate and repair the supplied GeoJSON; return area + repairs."""
        serializer = GeometryValidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = GeometryValidationService().validate(serializer.validated_data["geojson"])
        return Response(result)


class BuildingListView(ListAPIView[Building]):
    """GET buildings list — paginated, filtered, geometry opt-in (#17)."""

    permission_classes = [IsAuthenticated]
    serializer_class = BuildingSerializer

    def get_queryset(self) -> Any:
        """Return the ownership-scoped, filtered, ordered building queryset."""
        params = self.request.query_params
        analysis_id = self.kwargs["analysis_id"]
        _get_analysis(analysis_id)  # 404 for unknown analysis
        return list_buildings(
            analysis_id,
            self.request.user,
            bbox=parse_bbox(params.get("bbox")),
            min_area=parse_float(params.get("min_area"), field="min_area"),
            min_confidence=parse_float(params.get("confidence"), field="confidence"),
            order=params.get("order", "-area"),
        )

    def get_serializer_context(self) -> dict[str, Any]:
        """Enable simplified geometry only when ``?geometry=simplified``."""
        context = super().get_serializer_context()
        include = self.request.query_params.get("geometry") == "simplified"
        context["include_geometry"] = include
        context["simplify_tol_deg"] = 1e-4 if include else 0.0
        return context


class BuildingDetailView(APIView):
    """GET ``buildings/{id}/`` — full building + roof + solar (#18)."""

    permission_classes = [IsOwner]
    serializer_class = BuildingDetailSerializer

    def get(self, request: Request, pk: Any) -> Response:
        """Return the owned building with roof and solar estimates."""
        building = get_building(pk, request.user)
        self.check_object_permissions(request, building)
        return Response(BuildingDetailSerializer(building).data)


class FeaturesView(APIView):
    """GET features — map-ready GeoJSON; bbox required, capped, simplified (#19)."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request, analysis_id: Any) -> Response:
        """Return a bounded, simplified GeoJSON ``FeatureCollection``."""
        _get_analysis(analysis_id)
        params = self.request.query_params
        bbox = parse_bbox(params.get("bbox"))
        if bbox is None:
            from common.errors import ValidationError

            raise ValidationError(
                "A 'bbox' query parameter is required for map features.",
                details={"bbox": "required"},
            )
        zoom = parse_int(params.get("zoom"), field="zoom", default=16)
        buildings = list(list_buildings(analysis_id, request.user, bbox=bbox))
        service = BuildingProjectionService()
        collection = service.to_feature_collection(
            buildings, simplify_tol_deg=service.simplify_tol_for_zoom(zoom)
        )
        return Response(collection)


class ResultsView(APIView):
    """GET results — counts + totals + disclaimer (#16)."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request, analysis_id: Any) -> Response:
        """Return the aggregated results summary for the analysis."""
        _get_analysis(analysis_id)
        return Response(results_summary(analysis_id, request.user))
