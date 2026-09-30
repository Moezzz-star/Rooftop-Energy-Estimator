"""Persistence model for downloadable export artifacts.

An :class:`ExportArtifact` records a requested export (GeoJSON/CSV/PDF) of an
analysis's results. The heavy bytes live in object storage
(:mod:`common.storage`); this row stores only the reference, integrity metadata,
and build status. Models hold persistence only; building logic lives in
:mod:`apps.exports.services` (code-architecture §6).
"""

from __future__ import annotations

from django.db import models

from common.models import BaseModel


class ExportKind(models.TextChoices):
    """Supported export formats."""

    GEOJSON = "geojson", "GeoJSON"
    CSV = "csv", "CSV"
    PDF = "pdf", "PDF"


class ExportStatus(models.TextChoices):
    """Build lifecycle of an export artifact."""

    PENDING = "pending", "Pending"
    READY = "ready", "Ready"
    FAILED = "failed", "Failed"


class ExportArtifact(BaseModel):
    """A requested, asynchronously-built export of an analysis's results.

    Attributes:
        analysis: The owning analysis (ownership chain root for permissions).
        kind: Export format (geojson/csv/pdf).
        storage_key: Opaque object-storage key (null until built).
        checksum: Hex SHA-256 of the built bytes (null until built).
        bytes: Size of the built artifact in bytes (null until built).
        status: Build status (pending/ready/failed).
    """

    analysis = models.ForeignKey(
        "analyses.Analysis",
        on_delete=models.CASCADE,
        related_name="exports",
    )
    kind = models.CharField(max_length=16, choices=ExportKind.choices)
    storage_key = models.CharField(max_length=512, null=True, blank=True)
    checksum = models.CharField(max_length=64, null=True, blank=True)
    bytes = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=16,
        choices=ExportStatus.choices,
        default=ExportStatus.PENDING,
    )

    objects: models.Manager[ExportArtifact] = models.Manager()

    class Meta:
        verbose_name = "export artifact"
        verbose_name_plural = "export artifacts"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        """Return a short identifier."""
        return f"ExportArtifact({self.kind}, {self.status})"
