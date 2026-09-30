"""Persistence models for versioned solar estimation.

* :class:`CalculationMethodVersion` freezes a solar methodology (DEC-01
  parameters + pvlib port version) so completed analyses remain reproducible
  (DEC-09). Referenced with ``PROTECT``; never hard-deleted.
* :class:`SolarEstimate` is a per-building result row carrying the mandatory
  indicative-only disclaimer (DEC-02).
"""

from __future__ import annotations

from django.db import models

from common.models import BaseModel

# DEC-02 — exact disclaimer applied to every solar output (UI/PDF/CSV/GeoJSON).
DISCLAIMER = (
    "These are engineering estimates for indicative purposes only and are not "
    "a bankable photovoltaic yield study."
)


class CalculationMethodVersion(BaseModel):
    """A frozen, versioned solar-estimation methodology.

    Attributes:
        name: Method family (``"solar"``).
        version: Version identifier (mirrors ``SolarModel.version``).
        parameters: DEC-01 default assumptions captured at registration.
        description: Human-readable methodology summary.
        effective_date: Date from which this version is authoritative.
    """

    name = models.CharField(max_length=64, default="solar")
    version = models.CharField(max_length=64)
    parameters = models.JSONField(default=dict)
    description = models.TextField(blank=True)
    effective_date = models.DateField()

    class Meta:
        verbose_name = "calculation method version"
        verbose_name_plural = "calculation method versions"
        constraints = [
            models.UniqueConstraint(
                fields=["name", "version"],
                name="uq_calcmethod_name_version",
            ),
        ]
        ordering = ["-effective_date", "-created_at"]

    def __str__(self) -> str:
        """Return a human-readable identifier."""
        return f"{self.name}@{self.version}"


class SolarEstimate(BaseModel):
    """A per-building solar-yield estimate produced by the pipeline.

    Attributes:
        building: Owning building (geospatial app; string FK).
        calculation_version: Methodology snapshot used (PROTECT).
        capacity_kwp: Installed DC capacity (kWp).
        annual_kwh: Annual AC energy (kWh).
        monthly_kwh: Twelve monthly AC energy values (kWh), Jan..Dec.
        specific_yield: Annual energy per installed capacity (kWh/kWp).
        usable_area_m2: Roof area assumed usable for modules (m^2).
        inputs: Classified inputs used for the estimate (with ``source``).
        disclaimer: Mandatory indicative-only disclaimer (DEC-02).
    """

    building = models.ForeignKey(
        "geospatial.Building",
        on_delete=models.CASCADE,
        related_name="solar_estimates",
    )
    calculation_version = models.ForeignKey(
        CalculationMethodVersion,
        on_delete=models.PROTECT,
        related_name="estimates",
    )
    capacity_kwp = models.FloatField()
    annual_kwh = models.FloatField()
    monthly_kwh = models.JSONField(default=list)
    specific_yield = models.FloatField()
    usable_area_m2 = models.FloatField()
    inputs = models.JSONField(default=dict)
    disclaimer = models.TextField(default=DISCLAIMER)

    class Meta:
        verbose_name = "solar estimate"
        verbose_name_plural = "solar estimates"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        """Return a human-readable identifier."""
        return f"SolarEstimate<{self.building_id}> {self.annual_kwh:.0f} kWh/yr"
