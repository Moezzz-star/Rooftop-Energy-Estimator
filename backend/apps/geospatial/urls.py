"""URL routes for the geospatial app.

Mounted at the ``/api/v1/`` root by ``config/urls.py``. The geometry-validate
route carries its own ``geometry/`` prefix so it resolves at
``/api/v1/geometry/validate/`` (#10), while buildings/features/results resolve
at ``/api/v1/analyses/...`` and ``/api/v1/buildings/...`` per spec (#16-#19).
"""

from __future__ import annotations

from django.urls import path

from .views import (
    BuildingDetailView,
    BuildingListView,
    FeaturesView,
    GeometryValidateView,
    ResultsView,
)

urlpatterns = [
    # #10 — /api/v1/geometry/validate/ (module mounted at /api/v1/ root).
    path("geometry/validate/", GeometryValidateView.as_view(), name="geometry-validate"),
    # #16/#17/#18/#19 — /api/v1/... paths.
    path(
        "analyses/<uuid:analysis_id>/buildings/",
        BuildingListView.as_view(),
        name="analysis-buildings",
    ),
    path(
        "buildings/<uuid:pk>/",
        BuildingDetailView.as_view(),
        name="building-detail",
    ),
    path(
        "analyses/<uuid:analysis_id>/features/",
        FeaturesView.as_view(),
        name="analysis-features",
    ),
    path(
        "analyses/<uuid:analysis_id>/results/",
        ResultsView.as_view(),
        name="analysis-results",
    ),
]
