"""URL routes for the ML model registry, mounted at ``/api/v1/models/``."""

from __future__ import annotations

from rest_framework.routers import SimpleRouter

from .views import MLModelVersionViewSet

router = SimpleRouter(trailing_slash=True)
router.register(r"", MLModelVersionViewSet, basename="model")

urlpatterns = router.urls
