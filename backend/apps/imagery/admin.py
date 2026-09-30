"""Django admin registration for the imagery app."""

from __future__ import annotations

from django.contrib import admin

from .models import ImageryAsset


@admin.register(ImageryAsset)
class ImageryAssetAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """Read-mostly admin for ingested imagery assets."""

    list_display = ("id", "provider", "crs", "resolution_m", "bands", "created_at")
    list_filter = ("provider", "crs")
    search_fields = ("id", "storage_key", "checksum")
    readonly_fields = ("checksum", "storage_key")
