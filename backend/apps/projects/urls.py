"""URL routes for the projects app (mounted under ``/api/v1/``).

Exposes ``/projects/`` (list/create) and ``/projects/{id}/`` (retrieve/update/
delete) via a DRF router (code-architecture §4 #5-6).
"""

from __future__ import annotations

from rest_framework.routers import DefaultRouter

from .views import ProjectViewSet

router = DefaultRouter()
router.register(r"projects", ProjectViewSet, basename="project")

urlpatterns = router.urls
