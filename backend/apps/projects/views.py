"""HTTP views for the projects app.

A thin :class:`ProjectViewSet` scopes every query to ``request.user`` (DEC-08)
and delegates writes to :class:`apps.projects.services.ProjectService`. No
business logic lives in the view (code-architecture §6).
"""

from __future__ import annotations

from typing import Any

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, viewsets
from rest_framework.filters import OrderingFilter
from rest_framework.request import Request
from rest_framework.response import Response

from common.permissions import IsOwner

from .filters import ProjectFilter
from .models import Project
from .selectors import list_for_owner
from .serializers import ProjectSerializer
from .services import ProjectService


class ProjectViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet[Project],
):
    """CRUD for the authenticated user's projects.

    List/retrieve are scoped to the owner; create injects the owner and
    delegates to the service. DELETE cascades to child rows via model FKs.
    """

    serializer_class = ProjectSerializer
    permission_classes = [IsOwner]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = ProjectFilter
    ordering_fields = ["created_at", "name"]
    ordering = ["-created_at"]

    def get_queryset(self) -> Any:
        """Return only the requesting user's projects (ownership scoping)."""
        # Guard for schema generation where there is no authenticated user.
        if getattr(self, "swagger_fake_view", False):
            return Project.objects.none()
        return list_for_owner(self.request.user)

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Validate input, delegate creation to the service, return 201."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        service = ProjectService()
        project = service.create(
            owner=request.user,
            name=data["name"],
            description=data.get("description", ""),
        )
        out = self.get_serializer(project)
        return Response(out.data, status=201)
