"""DRF serializers for the exports app.

Serializers validate and shape data only; building logic lives in
:class:`apps.exports.services.ExportService` (code-architecture §6).
"""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from .models import ExportArtifact, ExportKind, ExportStatus


class ExportArtifactSerializer(serializers.ModelSerializer[ExportArtifact]):
    """Read representation of an :class:`ExportArtifact` with a download URL."""

    download_url = serializers.SerializerMethodField()

    class Meta:
        model = ExportArtifact
        fields = [
            "id",
            "analysis",
            "kind",
            "status",
            "checksum",
            "bytes",
            "created_at",
            "download_url",
        ]
        read_only_fields = fields

    def get_download_url(self, obj: ExportArtifact) -> str | None:
        """Return an opaque, authenticated download URL when ready, else ``None``.

        The URL points at the app's download endpoint (which streams the bytes
        after an ownership check); it never exposes the internal ``storage_key``
        or any filesystem path.
        """
        if obj.status != ExportStatus.READY or not obj.storage_key:
            return None
        from django.urls import reverse

        path = reverse("v1:export-download", kwargs={"pk": obj.pk})
        request = self.context.get("request")
        if request is not None:
            return str(request.build_absolute_uri(path))
        return path


class ExportRequestSerializer(serializers.Serializer[dict[str, Any]]):
    """Validate an export request body (the desired ``kind``)."""

    kind = serializers.ChoiceField(choices=ExportKind.choices)
