"""Django admin registration for the geospatial app."""

from __future__ import annotations

from django.contrib.gis import admin

from .models import Building, RoofGeometry


@admin.register(Building)
class BuildingAdmin(admin.GISModelAdmin):
    """Admin for detected building footprints."""

    list_display = ("id", "index", "area_m2", "confidence", "analysis")
    list_filter = ("analysis",)
    search_fields = ("id",)


@admin.register(RoofGeometry)
class RoofGeometryAdmin(admin.GISModelAdmin):
    """Admin for per-building roof geometries."""

    list_display = ("id", "building", "tilt_deg", "azimuth_deg", "usable_area_m2", "source")
    list_filter = ("source",)
