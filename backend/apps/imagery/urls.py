"""URL routes for the imagery app (mounted under ``/api/v1/``).

Endpoints (§4): #11 upload, #12 metadata, #13 sources. The ``sources`` route is
declared before the ``<uuid:pk>`` detail route for clarity (the typed converter
already prevents collision).
"""

from __future__ import annotations

from django.urls import path

from .views import ImageryDetailView, ImagerySourcesView, ImageryUploadView

urlpatterns = [
    path(
        "analyses/<uuid:analysis_id>/imagery/",
        ImageryUploadView.as_view(),
        name="analysis-imagery-upload",
    ),
    path("imagery/sources/", ImagerySourcesView.as_view(), name="imagery-sources"),
    path("imagery/<uuid:pk>/", ImageryDetailView.as_view(), name="imagery-detail"),
]
