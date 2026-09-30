"""URL routes for the analyses app, mounted at ``/api/v1/``.

Routes (code-architecture §4):
    * ``GET/POST  /projects/{project_id}/analyses/``  (#7)
    * ``GET/PATCH/DELETE  /analyses/{id}/``           (#8)
    * ``POST     /analyses/{id}/submit/``             (#9)
"""

from __future__ import annotations

from django.urls import path

from .views import (
    AnalysisDetailView,
    AnalysisSubmitView,
    ProjectAnalysisListCreateView,
)

urlpatterns = [
    path(
        "projects/<uuid:project_id>/analyses/",
        ProjectAnalysisListCreateView.as_view(),
        name="project-analyses",
    ),
    path(
        "analyses/<uuid:pk>/",
        AnalysisDetailView.as_view(),
        name="analysis-detail",
    ),
    path(
        "analyses/<uuid:pk>/submit/",
        AnalysisSubmitView.as_view(),
        name="analysis-submit",
    ),
]
