"""Read-only HTTP views for the ML model registry (§4 #22-23).

Views are thin: they expose registry metadata and delegate any logic to
:class:`~apps.ml_models.services.ModelRegistryService`. Both endpoints require
authentication (project default) but not object ownership: model metadata is
shared, non-tenant data.
"""

from __future__ import annotations

from django.db.models import QuerySet
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from .models import MLModelVersion, ModelStatus
from .serializers import MLModelVersionSerializer


class MLModelVersionViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet[MLModelVersion],
):
    """List production/registered model metadata and retrieve a model card.

    * ``GET /api/v1/models/`` -> paginated list of active (production or
      registered) versions.
    * ``GET /api/v1/models/{id}/`` -> a single model card (any status).
    """

    serializer_class = MLModelVersionSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self) -> QuerySet[MLModelVersion]:
        """Return the visible model versions.

        The list action is restricted to production/registered versions;
        retrieval by id may return any version (e.g. rolled-back cards).
        """
        base = MLModelVersion.objects.all()
        if self.action == "list":
            return base.filter(status__in=[ModelStatus.PRODUCTION, ModelStatus.REGISTERED])
        return base
