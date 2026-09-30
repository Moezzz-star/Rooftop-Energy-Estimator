"""Root URL configuration for the config project.

All API routes are mounted under ``/api/v1/``. Each domain app owns its own
``urls.py`` with a module-level ``urlpatterns`` (provided by the app engineers);
they are statically included here. Schema/docs and public health endpoints are
defined at this level.
"""

from __future__ import annotations

from django.contrib import admin
from django.urls import URLPattern, URLResolver, include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

from common.health import LivenessView, ReadinessView

# ---------------------------------------------------------------------------
# API v1 routes (each app supplies its own urlpatterns).
# ---------------------------------------------------------------------------
api_v1_patterns: list[URLPattern | URLResolver] = [
    # Authentication + current user.
    path("", include("apps.accounts.urls")),
    # Core domain resources.
    path("", include("apps.projects.urls")),
    path("", include("apps.analyses.urls")),
    # Geospatial routes mount at the API root; the geometry-validate route
    # carries its own ``geometry/`` prefix inside the app's urls module so that
    # buildings/features/results resolve at /api/v1/... per spec (#16-#19).
    path("", include("apps.geospatial.urls")),
    path("", include("apps.imagery.urls")),
    path("", include("apps.solar.urls")),
    # Model registry lives under /models/.
    path("models/", include("apps.ml_models.urls")),
    path("", include("apps.jobs.urls")),
    path("", include("apps.exports.urls")),
    # Health probes (public).
    path("health/", LivenessView.as_view(), name="health-liveness"),
    path("health/ready/", ReadinessView.as_view(), name="health-readiness"),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include((api_v1_patterns, "api"), namespace="v1")),
    # OpenAPI schema + Swagger UI.
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]
