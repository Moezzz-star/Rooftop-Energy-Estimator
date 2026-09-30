"""HTTP views for the analysis lifecycle (§4 #7, #8, #9).

Views are thin: they authenticate/authorize, validate via serializers, and
delegate all lifecycle logic to :class:`apps.analyses.services.AnalysisService`.
Ownership is enforced by scoping every queryset to
``project__owner == request.user`` and via :class:`common.permissions.IsOwner`.
"""

from __future__ import annotations

from typing import Any

from django.apps import apps
from django.db.models import QuerySet
from rest_framework import generics, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.errors import NotFoundError, ValidationError
from common.permissions import IsOwner

from .models import Analysis
from .serializers import (
    AnalysisCreateSerializer,
    AnalysisSerializer,
    AnalysisUpdateSerializer,
)
from .services import AnalysisService

_IDEMPOTENCY_HEADER = "Idempotency-Key"


def _owned_analyses(user: Any) -> QuerySet[Analysis]:
    """Return analyses owned by ``user`` (via project ownership)."""
    return Analysis.objects.filter(project__owner=user).select_related(
        "project", "assumption", "model_version", "calculation_version"
    )


def _get_owned_project(user: Any, project_id: str) -> Any:
    """Resolve a project owned by ``user`` or raise ``NotFoundError``.

    Uses ``apps.get_model`` so this module does not import the projects app at
    import time (keeps cross-app coupling lazy).
    """
    project_model = apps.get_model("projects", "Project")
    project = project_model.objects.filter(pk=project_id, owner=user).first()
    if project is None:
        raise NotFoundError("Project not found.")
    return project


class ProjectAnalysisListCreateView(generics.ListCreateAPIView):  # type: ignore[type-arg]
    """List/create analyses under a project (§4 #7)."""

    serializer_class = AnalysisSerializer
    permission_classes = (IsOwner,)

    def get_queryset(self) -> QuerySet[Analysis]:
        """Return the owner's analyses for the URL's project."""
        project_id = self.kwargs["project_id"]
        _get_owned_project(self.request.user, project_id)
        return _owned_analyses(self.request.user).filter(project_id=project_id)

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Create a draft analysis from a validated GeoJSON payload."""
        project = _get_owned_project(request.user, self.kwargs["project_id"])
        payload = AnalysisCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        analysis = AnalysisService().create(
            project=project,
            name=data["name"],
            area=data["area"],
            assumptions=data.get("assumptions"),
        )
        output = AnalysisSerializer(analysis, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_201_CREATED)


class AnalysisDetailView(generics.RetrieveUpdateDestroyAPIView):  # type: ignore[type-arg]
    """Retrieve, edit (draft only), or delete an analysis (§4 #8)."""

    serializer_class = AnalysisSerializer
    permission_classes = (IsOwner,)
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self) -> QuerySet[Analysis]:
        """Return the owner's analyses."""
        return _owned_analyses(self.request.user)

    def patch(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Apply a draft-only partial update."""
        analysis = self.get_object()
        payload = AnalysisUpdateSerializer(data=request.data, partial=True)
        payload.is_valid(raise_exception=True)

        AnalysisService().update_draft(analysis, dict(payload.validated_data))
        analysis.refresh_from_db()
        output = AnalysisSerializer(analysis, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_200_OK)

    def perform_destroy(self, instance: Analysis) -> None:
        """Delete an owned analysis, threading the actor for the audit trail.

        Cascade deletes reach imagery/export rows (their signals clean storage),
        and the ``Analysis`` post_delete handler records the audit event. The
        acting user is attached so the direct-delete audit event names the actor.
        """
        instance._audit_actor = self.request.user  # type: ignore[attr-defined]  # signal hand-off
        instance.delete()


class AnalysisSubmitView(APIView):
    """Submit an analysis for processing (§4 #9)."""

    permission_classes = (IsOwner,)

    def post(self, request: Request, pk: str) -> Response:
        """Submit the analysis; requires an ``Idempotency-Key`` header."""
        idempotency_key = request.headers.get(_IDEMPOTENCY_HEADER, "").strip()
        if not idempotency_key:
            raise ValidationError("Idempotency-Key header is required.")

        analysis = self._get_owned_analysis(request, pk)
        analysis, job = AnalysisService().submit(analysis, idempotency_key)

        return Response(self._body(analysis, job), status=status.HTTP_202_ACCEPTED)

    def _get_owned_analysis(self, request: Request, pk: str) -> Analysis:
        """Fetch an owned analysis and run the object-level permission check."""
        analysis = _owned_analyses(request.user).filter(pk=pk).first()
        if analysis is None:
            raise NotFoundError("Analysis not found.")
        self.check_object_permissions(request, analysis)
        return analysis

    @staticmethod
    def _body(analysis: Analysis, job: Any) -> dict[str, Any]:
        """Build the submit response body (job summary is best-effort)."""
        job_summary: dict[str, Any] | None = None
        if job is not None:
            job_summary = {
                "id": str(getattr(job, "pk", "")),
                "status": getattr(job, "status", None),
            }
        return {
            "analysis": {"id": str(analysis.pk), "status": analysis.status},
            "job": job_summary,
        }
