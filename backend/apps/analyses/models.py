"""Persistence models for the analysis lifecycle.

* :class:`Analysis` is the unit of work; on submit it freezes an immutable
  snapshot (DEC-09) of the model version, calculation-method version, its
  assumptions, and reproducibility metadata (code commit, imagery, processing
  config). Snapshot FKs use ``PROTECT`` so referenced versions cannot be
  deleted out from under a completed analysis.
* :class:`AnalysisArea` stores the area(s) of interest as EPSG:4326 geometry.
* :class:`AnalysisAssumption` holds the classified DEC-01 assumptions; it is a
  1:1 with the analysis and becomes immutable after submit.
"""

from __future__ import annotations

from django.contrib.gis.db import models as gis_models
from django.db import models

from common.models import BaseModel

# DEC-01 default solar assumptions (mirrors ml.configs.SolarConfig).
_DEFAULT_USABLE_ROOF_FRACTION = 0.70
_DEFAULT_POWER_DENSITY_W_M2 = 200.0
_DEFAULT_SYSTEM_LOSSES = 0.14
_DEFAULT_MODULE_EFF = 0.20
_DEFAULT_TILT_DEG = 20.0
_DEFAULT_AZIMUTH_DEG = 180.0
_DEFAULT_SHADING = 1.0
_DEFAULT_TEMP_AIR = 20.0
_DEFAULT_WIND = 1.0

# Public, documented DEC-01 defaults for the assumptions form. Exposed by the
# API (see :class:`apps.analyses.serializers.AnalysisSerializer`) so the frontend
# can render the assumptions editor pre-filled with the canonical defaults. This
# mirrors ``ml.configs.SolarConfig`` (the pipeline's source of truth) but is
# owned here so the API contract stays stable and Django-import-free for the ml/
# package. Keep these values in sync with ``SolarConfig``.
ASSUMPTION_DEFAULTS: dict[str, float] = {
    "usable_roof_fraction": _DEFAULT_USABLE_ROOF_FRACTION,
    "power_density_w_m2": _DEFAULT_POWER_DENSITY_W_M2,
    "system_losses": _DEFAULT_SYSTEM_LOSSES,
    "module_eff": _DEFAULT_MODULE_EFF,
    "tilt_deg": _DEFAULT_TILT_DEG,
    "azimuth_deg": _DEFAULT_AZIMUTH_DEG,
    "shading": _DEFAULT_SHADING,
    "temp_air": _DEFAULT_TEMP_AIR,
    "wind": _DEFAULT_WIND,
}


class AnalysisStatus(models.TextChoices):
    """Lifecycle states of an analysis."""

    DRAFT = "draft", "Draft"
    QUEUED = "queued", "Queued"
    RUNNING = "running", "Running"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"
    CANCELLED = "cancelled", "Cancelled"


class AssumptionSource(models.TextChoices):
    """Provenance classification of assumption values."""

    MEASURED = "measured", "Measured"
    INFERRED = "inferred", "Inferred"
    USER = "user", "User"
    DEFAULT = "default", "Default"
    CALCULATED = "calculated", "Calculated"


class Analysis(BaseModel):
    """A single rooftop analysis with an immutable post-submit snapshot.

    Attributes:
        name: Human-readable analysis name.
        status: Lifecycle state (default ``draft``).
        idempotency_key: Client-supplied submit key; unique per project when
            set (see ``Meta.constraints``).
        submitted_at: Timestamp the analysis was submitted.
        completed_at: Timestamp the pipeline finished.
        project: Owning project (ownership root; CASCADE).
        model_version: Frozen ML model version snapshot (PROTECT, DEC-09).
        calculation_version: Frozen solar methodology snapshot (PROTECT).
        snapshot: Frozen reproducibility metadata (code commit, imagery,
            processing config).
    """

    name = models.CharField(max_length=200)
    status = models.CharField(
        max_length=16,
        choices=AnalysisStatus.choices,
        default=AnalysisStatus.DRAFT,
    )
    idempotency_key = models.CharField(max_length=200, null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="analyses",
    )

    # Immutable snapshot references (DEC-09) — PROTECT so versions survive.
    model_version = models.ForeignKey(
        "ml_models.MLModelVersion",
        on_delete=models.PROTECT,
        related_name="analyses",
        null=True,
        blank=True,
    )
    calculation_version = models.ForeignKey(
        "solar.CalculationMethodVersion",
        on_delete=models.PROTECT,
        related_name="analyses",
        null=True,
        blank=True,
    )
    snapshot = models.JSONField(default=dict)

    class Meta:
        verbose_name = "analysis"
        verbose_name_plural = "analyses"
        ordering = ["-created_at"]
        constraints = [
            # Idempotency: a given key is unique within a project, enforced
            # only when a key is present (drafts have no key).
            models.UniqueConstraint(
                fields=["project", "idempotency_key"],
                condition=models.Q(idempotency_key__isnull=False),
                name="uq_analysis_project_idempotency_key",
            ),
        ]

    def __str__(self) -> str:
        """Return a human-readable identifier."""
        return f"{self.name} ({self.status})"

    @property
    def is_draft(self) -> bool:
        """Return whether the analysis is still editable."""
        return self.status == AnalysisStatus.DRAFT


class AnalysisArea(BaseModel):
    """A labelled area of interest for an analysis (EPSG:4326).

    ``MultiPolygonField`` is used so callers may submit either a single polygon
    (normalized on write) or a multi-polygon.
    """

    analysis = models.ForeignKey(
        Analysis,
        on_delete=models.CASCADE,
        related_name="areas",
    )
    label = models.CharField(max_length=200, blank=True)
    area = gis_models.MultiPolygonField(srid=4326)

    class Meta:
        verbose_name = "analysis area"
        verbose_name_plural = "analysis areas"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        """Return a human-readable identifier."""
        return self.label or f"area<{self.pk}>"


class AnalysisAssumption(BaseModel):
    """Classified DEC-01 assumptions for an analysis (1:1, frozen post-submit).

    Attributes:
        source: Provenance classification of the values.
        usable_roof_fraction: Usable fraction of roof, ``(0, 1]``.
        power_density_w_m2: Installed DC power density per usable m^2.
        system_losses: Aggregate AC-side loss fraction, ``[0, 1)``.
        module_eff: Nominal module efficiency (informational).
        tilt_deg: Fixed module tilt (degrees).
        azimuth_deg: Fixed module azimuth (degrees, 180 = due south).
        shading: Fraction of direct POA retained (1 = no shading).
        temp_air: Ambient air temperature assumption (degC).
        wind: Wind speed assumption (m/s).
    """

    analysis = models.OneToOneField(
        Analysis,
        on_delete=models.CASCADE,
        related_name="assumption",
    )
    source = models.CharField(
        max_length=16,
        choices=AssumptionSource.choices,
        default=AssumptionSource.DEFAULT,
    )
    usable_roof_fraction = models.FloatField(default=_DEFAULT_USABLE_ROOF_FRACTION)
    power_density_w_m2 = models.FloatField(default=_DEFAULT_POWER_DENSITY_W_M2)
    system_losses = models.FloatField(default=_DEFAULT_SYSTEM_LOSSES)
    module_eff = models.FloatField(default=_DEFAULT_MODULE_EFF)
    tilt_deg = models.FloatField(default=_DEFAULT_TILT_DEG)
    azimuth_deg = models.FloatField(default=_DEFAULT_AZIMUTH_DEG)
    shading = models.FloatField(default=_DEFAULT_SHADING)
    temp_air = models.FloatField(default=_DEFAULT_TEMP_AIR)
    wind = models.FloatField(default=_DEFAULT_WIND)

    class Meta:
        verbose_name = "analysis assumption"
        verbose_name_plural = "analysis assumptions"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        """Return a human-readable identifier."""
        return f"assumption<{self.analysis_id}> ({self.source})"
