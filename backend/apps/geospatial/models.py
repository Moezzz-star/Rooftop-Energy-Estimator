"""Persistence models for the geospatial app.

Defines :class:`Building` (a detected rooftop footprint with metric area and
centroid) and :class:`RoofGeometry` (per-building usable-roof geometry and
orientation). Both store geometry in EPSG:4326; metric operations happen in
services via on-the-fly UTM reprojection (code-architecture §3).

Models hold persistence and simple invariants only; domain logic lives in
:mod:`apps.geospatial.services` (code-architecture §6). The ``analyses.Analysis``
reference is a string label so this app never imports the analyses app.
"""

from __future__ import annotations

from django.contrib.gis.db import models as gis_models
from django.db import models

from common.models import BaseModel


class Building(BaseModel):
    """A detected building footprint bound to an analysis.

    Attributes:
        analysis: Owning analysis (ownership chain root for permissions).
        confidence: Mean model probability for the footprint (nullable).
        area_m2: Metric footprint area (computed in UTM at vectorization).
        index: Stable ordering index assigned during vectorization.
        geometry: Footprint polygon in EPSG:4326.
        centroid: Footprint centroid point in EPSG:4326.
    """

    analysis = models.ForeignKey(
        "analyses.Analysis",
        on_delete=models.CASCADE,
        related_name="buildings",
    )
    confidence = models.FloatField(null=True, blank=True)
    area_m2 = models.FloatField()
    index = models.IntegerField()
    geometry = gis_models.PolygonField(srid=4326)
    centroid = gis_models.PointField(srid=4326)

    class Meta:
        ordering = ["index"]
        verbose_name = "building"
        verbose_name_plural = "buildings"
        indexes = [
            models.Index(fields=["analysis", "index"]),
            models.Index(fields=["analysis", "area_m2"]),
        ]

    def __str__(self) -> str:
        """Return a short identifier."""
        return f"Building(index={self.index}, area_m2={self.area_m2:.1f})"


class RoofGeometry(BaseModel):
    """Usable-roof geometry and orientation for a single building.

    Attributes:
        building: The owning building (one-to-one).
        tilt_deg: Roof tilt in degrees.
        azimuth_deg: Roof azimuth in degrees (0 = north).
        usable_area_m2: Usable roof area in square metres.
        source: Origin of the geometry (e.g. ``"footprint"``, ``"user"``).
        geometry: Usable-roof polygon in EPSG:4326.
    """

    building = models.OneToOneField(
        Building,
        on_delete=models.CASCADE,
        related_name="roof",
    )
    tilt_deg = models.FloatField()
    azimuth_deg = models.FloatField()
    usable_area_m2 = models.FloatField()
    source = models.CharField(max_length=64)
    geometry = gis_models.PolygonField(srid=4326)

    class Meta:
        verbose_name = "roof geometry"
        verbose_name_plural = "roof geometries"

    def __str__(self) -> str:
        """Return a short identifier."""
        return (
            f"RoofGeometry(building={self.building_id}, usable_area_m2={self.usable_area_m2:.1f})"
        )
