"""Django admin registration for the projects app."""

from __future__ import annotations

from django.contrib import admin

from .models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """Admin listing for projects."""

    list_display = ["name", "owner", "is_archived", "created_at"]
    list_filter = ["is_archived", "created_at"]
    search_fields = ["name", "owner__email"]
    readonly_fields = ["id", "created_at", "updated_at"]
    raw_id_fields = ["owner"]
