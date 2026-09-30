"""URL routes for the exports app, mounted at ``/api/v1/`` (§4 #20, #21)."""

from __future__ import annotations

from django.urls import path

from .views import AnalysisExportsView, ExportDetailView, ExportDownloadView

urlpatterns = [
    path(
        "analyses/<uuid:analysis_id>/exports/",
        AnalysisExportsView.as_view(),
        name="analysis-exports",
    ),
    path("exports/<uuid:pk>/", ExportDetailView.as_view(), name="export-detail"),
    path(
        "exports/<uuid:pk>/download/",
        ExportDownloadView.as_view(),
        name="export-download",
    ),
]
