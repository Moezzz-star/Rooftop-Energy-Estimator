"""DRF serializers for the projects app (validation + shaping only)."""

from __future__ import annotations

from rest_framework import serializers

from .models import Project


class ProjectSerializer(serializers.ModelSerializer[Project]):
    """Read/write representation of a project.

    ``owner`` is never client-settable; it is injected from ``request.user`` by
    the view/service so a caller can only ever create projects they own.
    """

    class Meta:
        model = Project
        fields = [
            "id",
            "name",
            "description",
            "is_archived",
            "owner",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "owner", "created_at", "updated_at"]
