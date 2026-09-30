"""URL routes for the jobs app, mounted at ``/api/v1/`` (§4 #14, #15)."""

from __future__ import annotations

from django.urls import path

from .views import AnalysisJobCancelView, AnalysisJobView

urlpatterns = [
    path(
        "analyses/<uuid:analysis_id>/job/",
        AnalysisJobView.as_view(),
        name="analysis-job",
    ),
    path(
        "analyses/<uuid:analysis_id>/job/cancel/",
        AnalysisJobCancelView.as_view(),
        name="analysis-job-cancel",
    ),
]
