"""Persistence models for the imagery app.

Defines :class:`ImageryAsset`, an immutable record of an ingested raster scene
bound to an :class:`analyses.Analysis`. The heavy raster bytes live in object
storage (:mod:`common.storage`); this row stores only references and extracted
metadata (CRS, bounds, resolution, band count, checksum) plus a 4326 footprint.

Models hold persistence and simple invariants only; all domain logic lives in
:mod:`apps.imagery.services` (code-architecture §6). Cross-app references use a
string label (``"analyses.Analysis"``) so this app never imports the analyses
app directly.
"""

from __future__ import annotations

from django.contrib.gis.db import models as gis_models
from django.db import models

from common.models import BaseModel

# DEC-04: OSM training labels are ODbL 1.0; ship attribution with derived
# outputs. These defaults are overridable per asset (e.g. uploads with their
# own licensing terms).
DEFAULT_LICENSE = "ODbL 1.0"
DEFAULT_ATTRIBUTION = "© OpenStreetMap contributors, ODbL"


class ImageryAsset(BaseModel):
    """A single ingested raster scene and its extracted metadata.

    Attributes:
        analysis: Owning analysis (ownership chain root for permissions).
        provider: Registry name of the :class:`ImageryProvider` that produced
            the asset (e.g. ``"uploaded_raster"``).
        original_filename: Basename of the uploaded/source raster (provenance).
        storage_key: Opaque object-storage key for the raster bytes.
        checksum: Hex SHA-256 of the stored raster (provenance/idempotency).
        crs: Coordinate reference system identifier (e.g. ``"EPSG:32632"``).
        resolution_m: Ground sample distance in metres per pixel (nullable).
        bounds: Native-CRS bounds as ``{"left","bottom","right","top"}``.
        transform: Affine transform coefficients ``[a, b, c, d, e, f]``.
        width: Raster width in pixels.
        height: Raster height in pixels.
        bands: Number of raster bands.
        nodata: Declared nodata sentinel value, if any (nullable).
        dtype: Pixel data type of band 1 (e.g. ``"uint8"``).
        acquired_at: Optional acquisition timestamp.
        license: Data license identifier (defaults to DEC-04 ODbL).
        attribution: Attribution string shown with derived outputs (DEC-04).
        lineage: Processing lineage (how/where derived), e.g.
            ``{"origin": "upload", "filename": ..., "ingested_at": ...}``.
        footprint: Scene footprint polygon reprojected to EPSG:4326 (nullable).
    """

    analysis = models.ForeignKey(
        "analyses.Analysis",
        on_delete=models.CASCADE,
        related_name="imagery_assets",
    )
    provider = models.CharField(max_length=64)
    original_filename = models.CharField(max_length=255, blank=True, default="")
    storage_key = models.CharField(max_length=512)
    checksum = models.CharField(max_length=64)
    crs = models.CharField(max_length=64)
    resolution_m = models.FloatField(null=True, blank=True)
    bounds = models.JSONField(default=dict, blank=True)
    transform = models.JSONField(default=list, blank=True)
    width = models.PositiveIntegerField(default=0)
    height = models.PositiveIntegerField(default=0)
    bands = models.PositiveIntegerField(default=0)
    nodata = models.FloatField(null=True, blank=True)
    dtype = models.CharField(max_length=32, blank=True, default="")
    acquired_at = models.DateTimeField(null=True, blank=True)
    license = models.CharField(max_length=64, default=DEFAULT_LICENSE)
    attribution = models.CharField(max_length=255, default=DEFAULT_ATTRIBUTION)
    lineage = models.JSONField(default=dict, blank=True)
    footprint = gis_models.PolygonField(srid=4326, null=True, blank=True)

    objects: models.Manager[ImageryAsset] = models.Manager()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "imagery asset"
        verbose_name_plural = "imagery assets"

    def __str__(self) -> str:
        """Return a short, non-sensitive identifier."""
        return f"ImageryAsset({self.provider}, {self.crs})"
