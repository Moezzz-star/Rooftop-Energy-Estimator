"""Admin registration for the ML model registry (read-focused)."""

from __future__ import annotations

from django.contrib import admin

from .models import MLModelVersion


@admin.register(MLModelVersion)
class MLModelVersionAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """Admin view for browsing registered model versions."""

    list_display = ("name", "version", "status", "input_resolution", "created_at")
    list_filter = ("status", "name")
    search_fields = ("name", "version", "checksum")
    readonly_fields = ("id", "created_at", "updated_at")
