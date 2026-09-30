"""HTTP views for the jobs app (§4 #14, #15).

Views are thin: they resolve the owner-scoped job, enforce object-level
ownership, delegate to :class:`apps.jobs.services.JobOrchestrator`, and shape
responses. No orchestration logic lives here (code-architecture §6).

Endpoint #16 (results summary) is owned by the geospatial app and is not
implemented here.
"""

from __future__ import annotations

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.logging import get_logger
from common.permissions import IsOwner

from .selectors import get_job_for_analysis
from .serializers import JobSerializer
from .services import JobOrchestrator

logger = get_logger("jobs.views")


class AnalysisJobView(APIView):
    """GET ``/analyses/{analysis_id}/job/`` — job status + stages (#14)."""

    permission_classes = [IsOwner]
    serializer_class = JobSerializer

    def get(self, request: Request, analysis_id: str) -> Response:
        """Return the polled job progress for an owned analysis."""
        job = get_job_for_analysis(analysis_id, request.user)
        self.check_object_permissions(request, job)
        return Response(JobSerializer(job).data)


class AnalysisJobCancelView(APIView):
    """POST ``/analyses/{analysis_id}/job/cancel/`` — request cancel (#15)."""

    permission_classes = [IsOwner]
    serializer_class = JobSerializer

    def post(self, request: Request, analysis_id: str) -> Response:
        """Request cooperative cancellation of the analysis's job."""
        job = get_job_for_analysis(analysis_id, request.user)
        self.check_object_permissions(request, job)
        JobOrchestrator().cancel(job)
        logger.info("Cancellation accepted", extra={"job_id": str(job.pk)})
        return Response(JobSerializer(job).data, status=status.HTTP_202_ACCEPTED)
