"""DRF serializers for the imagery app.

Serializers validate and shape data only; ingestion logic lives in
:class:`apps.imagery.services.ImageryService` (code-architecture §6).
"""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from .models import ImageryAsset


class ImageryAssetSerializer(serializers.ModelSerializer[ImageryAsset]):
    """Read representation of an :class:`ImageryAsset` (metadata only)."""

    class Meta:
        model = ImageryAsset
        fields = [
            "id",
            "analysis",
            "provider",
            "original_filename",
            "storage_key",
            "checksum",
            "crs",
            "resolution_m",
            "bounds",
            "transform",
            "width",
            "height",
            "bands",
            "nodata",
            "dtype",
            "acquired_at",
            "license",
            "attribution",
            "lineage",
            "created_at",
        ]
        read_only_fields = fields


class ImageryUploadSerializer(serializers.Serializer[dict[str, Any]]):
    """Validate the multipart upload body (a single raster file)."""

    file = serializers.FileField()


class ProviderCapabilitiesSerializer(serializers.Serializer[dict[str, Any]]):
    """Shape a provider's capabilities for the sources endpoint."""

    name = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField()
    supports_upload = serializers.BooleanField()
    supports_windowed_read = serializers.BooleanField()
    requires_network = serializers.BooleanField()
    available = serializers.BooleanField()
