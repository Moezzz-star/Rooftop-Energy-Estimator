"""django-filter FilterSet for the projects list endpoint.

Supports case-insensitive name search and archived filtering; ordering by
``created_at`` is handled by DRF's ``OrderingFilter`` in the view.
"""

from __future__ import annotations

from django_filters import rest_framework as filters

from .models import Project


class ProjectFilter(filters.FilterSet):  # type: ignore[misc]  # django_filters is untyped
    """Filter projects by name (icontains) and archived state."""

    name = filters.CharFilter(field_name="name", lookup_expr="icontains")
    is_archived = filters.BooleanFilter(field_name="is_archived")

    class Meta:
        model = Project
        fields = ["name", "is_archived"]
