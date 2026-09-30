"""Admin registration for solar methodology + estimates."""

from __future__ import annotations

from django.contrib import admin

from .models import CalculationMethodVersion, SolarEstimate


@admin.register(CalculationMethodVersion)
class CalculationMethodVersionAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """Admin view for solar methodology versions."""

    list_display = ("name", "version", "effective_date", "created_at")
    list_filter = ("name",)
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(SolarEstimate)
class SolarEstimateAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """Admin view for per-building solar estimates."""

    list_display = ("building_id", "capacity_kwp", "annual_kwh", "specific_yield")
    readonly_fields = ("id", "created_at", "updated_at")
