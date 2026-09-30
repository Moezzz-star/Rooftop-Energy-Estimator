"""HTTP views for the exports app (§4 #20, #21).

Views are thin: they resolve owner-scoped analyses/artifacts, enforce object
ownership, create the artifact + enqueue the build task, and shape responses.
No building logic lives here (code-architecture §6).
"""

from __future__ import annotations

from typing import Any

from django.apps import apps as django_apps
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.errors import NotFoundError
from common.logging import get_logger
from common.permissions import IsOwner

from .models import ExportArtifact, ExportStatus
from .serializers import ExportArtifactSerializer, ExportRequestSerializer

logger = get_logger("exports.views")

# Content types served for a downloaded artifact, keyed by export kind.
_CONTENT_TYPES = {
    "geojson": "application/geo+json",
    "csv": "text/csv",
    "pdf": "application/pdf",
}


def _get_analysis(analysis_id: Any) -> Any:
    """Resolve an ``analyses.Analysis`` by id without importing the app."""
    model = django_apps.get_model("analyses", "Analysis")
    return get_object_or_404(model, pk=analysis_id)


class AnalysisExportsView(APIView):
    """GET/POST ``/analyses/{analysis_id}/exports/`` — list / request (#20)."""

    permission_classes = [IsOwner]
    serializer_class = ExportArtifactSerializer

    def get(self, request: Request, analysis_id: Any) -> Response:
        """List the analysis's export artifacts for the owner."""
        analysis = _get_analysis(analysis_id)
        self.check_object_permissions(request, analysis)
        artifacts = analysis.exports.all()
        serializer = ExportArtifactSerializer(
            artifacts, many=True, context={"request": request}
        )
        return Response(serializer.data)

    def post(self, request: Request, analysis_id: Any) -> Response:
        """Create a pending artifact and enqueue its async build (202)."""
        from .tasks import generate_export

        analysis = _get_analysis(analysis_id)
        self.check_object_permissions(request, analysis)

        payload = ExportRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        artifact = ExportArtifact.objects.create(
            analysis=analysis, kind=payload.validated_data["kind"]
        )
        generate_export.delay(str(artifact.pk))
        logger.info("Export requested", extra={"analysis_id": str(analysis.pk)})
        serializer = ExportArtifactSerializer(artifact, context={"request": request})
        return Response(serializer.data, status=status.HTTP_202_ACCEPTED)


class ExportDetailView(APIView):
    """GET ``/exports/{id}/`` — status + opaque download URL (#21)."""

    permission_classes = [IsOwner]
    serializer_class = ExportArtifactSerializer

    def get(self, request: Request, pk: Any) -> Response:
        """Return the artifact if the caller owns its analysis."""
        artifact = get_object_or_404(
            ExportArtifact.objects.select_related("analysis__project"), pk=pk
        )
        self.check_object_permissions(request, artifact)
        serializer = ExportArtifactSerializer(artifact, context={"request": request})
        return Response(serializer.data)


class ExportDownloadView(APIView):
    """GET ``/exports/{id}/download/`` — stream the artifact bytes (#21).

    The response streams the stored bytes with a ``Content-Disposition``
    attachment header. Ownership is enforced via the analysis chain, and the
    internal ``storage_key`` / filesystem path is never exposed: the download
    filename is derived only from the analysis id and export kind.
    """

    permission_classes = [IsOwner]

    def get(self, request: Request, pk: Any) -> FileResponse:
        """Stream the built artifact to an authorized owner."""
        artifact = get_object_or_404(
            ExportArtifact.objects.select_related("analysis__project"), pk=pk
        )
        self.check_object_permissions(request, artifact)
        if artifact.status != ExportStatus.READY or not artifact.storage_key:
            raise NotFound("Export is not ready for download.")

        from common.storage import get_storage

        try:
            stream = get_storage().open(artifact.storage_key)
        except NotFoundError as exc:
            logger.warning("Export bytes missing on download", extra={"export_id": str(pk)})
            raise NotFound("Export artifact bytes are unavailable.") from exc

        filename = f"analysis-{artifact.analysis_id}-{artifact.kind}.{artifact.kind}"
        content_type = _CONTENT_TYPES.get(artifact.kind, "application/octet-stream")
        return FileResponse(
            stream,
            as_attachment=True,
            filename=filename,
            content_type=content_type,
        )
