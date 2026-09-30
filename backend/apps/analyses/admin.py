"""Admin registration for the analyses app."""

from __future__ import annotations

from django.contrib import admin

from .models import Analysis, AnalysisArea, AnalysisAssumption


@admin.register(Analysis)
class AnalysisAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """Admin view for analyses."""

    list_display = ("name", "status", "project", "submitted_at", "completed_at")
    list_filter = ("status",)
    search_fields = ("name", "idempotency_key")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(AnalysisArea)
class AnalysisAreaAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """Admin view for analysis areas."""

    list_display = ("label", "analysis")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(AnalysisAssumption)
class AnalysisAssumptionAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """Admin view for analysis assumptions."""

    list_display = ("analysis", "source", "usable_roof_fraction", "power_density_w_m2")
    list_filter = ("source",)
    readonly_fields = ("id", "created_at", "updated_at")
