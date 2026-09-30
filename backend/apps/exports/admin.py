"""Django admin registration for the exports app."""

from __future__ import annotations

from django.contrib import admin

from .models import ExportArtifact


@admin.register(ExportArtifact)
class ExportArtifactAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """Read-mostly admin for export artifacts."""

    list_display = ("id", "analysis_id", "kind", "status", "bytes", "created_at")
    list_filter = ("kind", "status")
    search_fields = ("id", "analysis__id", "storage_key", "checksum")
    readonly_fields = ("storage_key", "checksum", "bytes")
