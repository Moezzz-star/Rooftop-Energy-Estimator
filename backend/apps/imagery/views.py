"""HTTP views for the imagery app.

Views are thin: they resolve objects, enforce ownership, delegate to
:class:`apps.imagery.services.ImageryService` / the provider registry, and shape
responses. No business logic lives here (code-architecture §6).

Endpoints (§4): #11 upload, #12 metadata, #13 sources.
"""

from __future__ import annotations

from typing import Any

from django.apps import apps as django_apps
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.logging import get_logger
from common.permissions import IsOwner

from .models import ImageryAsset
from .providers import build_default_registry
from .serializers import (
    ImageryAssetSerializer,
    ImageryUploadSerializer,
    ProviderCapabilitiesSerializer,
)
from .services import ImageryService

logger = get_logger("imagery.views")


def _get_analysis(analysis_id: Any) -> Any:
    """Resolve an ``analyses.Analysis`` by id without importing the app."""
    model = django_apps.get_model("analyses", "Analysis")
    return get_object_or_404(model, pk=analysis_id)


class ImageryUploadView(APIView):
    """POST ``/analyses/{analysis_id}/imagery/`` — upload a raster (#11)."""

    permission_classes = [IsOwner]
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = ImageryUploadSerializer

    def post(self, request: Request, analysis_id: Any) -> Response:
        """Validate the upload, enforce ownership, and ingest the raster."""
        analysis = _get_analysis(analysis_id)
        self.check_object_permissions(request, analysis)

        serializer = ImageryUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = ImageryService()
        asset = service.register_upload(analysis, serializer.validated_data["file"])
        logger.info("Imagery uploaded", extra={"analysis_id": str(analysis.pk)})
        return Response(ImageryAssetSerializer(asset).data, status=status.HTTP_201_CREATED)


class ImageryDetailView(APIView):
    """GET ``/imagery/{id}/`` — return imagery metadata (#12)."""

    permission_classes = [IsOwner]
    serializer_class = ImageryAssetSerializer

    def get(self, request: Request, pk: Any) -> Response:
        """Return the asset if the caller owns its analysis."""
        asset = get_object_or_404(ImageryAsset.objects.select_related("analysis"), pk=pk)
        self.check_object_permissions(request, asset)
        return Response(ImageryAssetSerializer(asset).data)


class ImagerySourcesView(APIView):
    """GET ``/imagery/sources/`` — list available providers (#13)."""

    permission_classes = [IsAuthenticated]
    serializer_class = ProviderCapabilitiesSerializer

    def get(self, request: Request) -> Response:
        """Return capabilities for every registered imagery provider."""
        registry = build_default_registry()
        payload = [cap.as_dict() for cap in registry.available()]
        return Response({"sources": payload})
