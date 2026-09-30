"""Domain services for versioned solar estimation.

:class:`SolarEstimationService` wraps the pure :class:`ml.inference.solar.SolarModel`
(pvlib port) — it never reimplements the physics. It builds the model's
:class:`~ml.inference.solar.SolarInputs` from a building, its resolved
assumptions (DEC-01) and a site location, invokes the pure model, maps its
validation failures to :class:`common.errors.ValidationError` at the boundary,
and persists a :class:`~apps.solar.models.SolarEstimate` carrying the DEC-02
disclaimer.

:class:`SolarMethodRegistry` resolves/creates the frozen methodology version
(:class:`~apps.solar.models.CalculationMethodVersion`) referenced by snapshots.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from typing import TYPE_CHECKING, Any, Protocol, cast, runtime_checkable

from common.errors import ValidationError
from common.logging import get_logger
from ml.configs import DEFAULT_SOLAR
from ml.inference.solar import SolarInputs, SolarModel

from .models import CalculationMethodVersion, SolarEstimate

if TYPE_CHECKING:  # pragma: no cover - typing only; avoids runtime app coupling
    from apps.geospatial.models import Building

logger = get_logger("solar.estimation")


@runtime_checkable
class BuildingLike(Protocol):
    """Minimal building contract needed to build solar inputs."""

    area_m2: float
    centroid: Any  # GEOS Point in EPSG:4326 exposing ``.x`` (lon) / ``.y`` (lat).


@runtime_checkable
class AssumptionLike(Protocol):
    """Minimal assumption contract (mirrors AnalysisAssumption / DEC-01)."""

    source: str
    usable_roof_fraction: float
    power_density_w_m2: float
    system_losses: float
    tilt_deg: float
    azimuth_deg: float
    shading: float


@dataclass(frozen=True)
class SolarLocation:
    """Resolved site location for an estimate.

    ``latitude``/``longitude`` may be omitted, in which case they are resolved
    from the building centroid (EPSG:4326).

    Attributes:
        timezone: IANA time-zone name (e.g. ``"Europe/Berlin"``).
        altitude: Site altitude above sea level (m).
        latitude: Optional explicit latitude override.
        longitude: Optional explicit longitude override.
    """

    timezone: str
    altitude: float = 0.0
    latitude: float | None = None
    longitude: float | None = None


class SolarMethodRegistry:
    """Resolve and register the frozen solar methodology version."""

    _NAME = "solar"

    def get_active(self) -> CalculationMethodVersion:
        """Return the most recent effective methodology version.

        Returns:
            The active :class:`CalculationMethodVersion`, creating the DEC-01
            default if none exists yet.
        """
        active = (
            CalculationMethodVersion.objects.filter(name=self._NAME)
            .order_by("-effective_date", "-created_at")
            .first()
        )
        if active is not None:
            return active
        return self.get_or_create_default()

    @classmethod
    def get_or_create_default(cls) -> CalculationMethodVersion:
        """Register (idempotently) the DEC-01 default methodology.

        Captures the DEC-01 default assumptions plus the pure model's version
        string so completed analyses can reproduce identical numbers (DEC-09).

        Returns:
            The default :class:`CalculationMethodVersion`.
        """
        version = SolarModel().version
        method, created = CalculationMethodVersion.objects.get_or_create(
            name=cls._NAME,
            version=version,
            defaults={
                "parameters": asdict(DEFAULT_SOLAR),
                "description": (
                    "pvlib clear-sky (Ineichen) fixed-orientation PVWatts model "
                    "with DEC-01 default assumptions."
                ),
                "effective_date": date(2024, 1, 1),
            },
        )
        if created:
            logger.info(
                "Registered default solar method version",
                extra={"version": version},
            )
        return method


class SolarEstimationService:
    """Produce and persist a solar estimate for a single building."""

    def __init__(
        self,
        model: SolarModel | None = None,
        method_version: CalculationMethodVersion | None = None,
    ) -> None:
        """Initialize the service with injected dependencies.

        Args:
            model: Pure pvlib model to wrap. Defaults to a fresh
                :class:`SolarModel`.
            method_version: Methodology snapshot to attach to results. Resolved
                from the registry on first use when omitted.
        """
        self._model = model if model is not None else SolarModel()
        self._method_version = method_version
        self._registry = SolarMethodRegistry()

    def estimate(
        self,
        building: BuildingLike,
        assumption: AssumptionLike,
        location: SolarLocation,
    ) -> SolarEstimate:
        """Estimate and persist solar yield for ``building``.

        Args:
            building: Building providing ``area_m2`` and a 4326 ``centroid``.
            assumption: Resolved assumptions (DEC-01 defaults or overrides).
            location: Site location (timezone/altitude; optional lat/lon).

        Returns:
            The persisted :class:`SolarEstimate`.

        Raises:
            ValidationError: If the pure model rejects the inputs (§15).
        """
        inputs = self._build_inputs(building, assumption, location)

        try:
            result = self._model.estimate(inputs)
        except ValueError as exc:
            logger.warning("Solar input validation failed", extra={"error": str(exc)})
            raise ValidationError(str(exc), code="solar_validation_error") from exc

        method = self._resolve_method_version()
        estimate = SolarEstimate.objects.create(
            building=cast("Building", building),
            calculation_version=method,
            capacity_kwp=result.capacity_kwp,
            annual_kwh=result.annual_kwh,
            monthly_kwh=result.monthly_kwh,
            specific_yield=result.specific_yield,
            usable_area_m2=result.usable_area_m2,
            inputs=self._classify_inputs(inputs, assumption.source),
        )
        logger.info(
            "Persisted solar estimate",
            extra={
                "annual_kwh": result.annual_kwh,
                "capacity_kwp": result.capacity_kwp,
            },
        )
        return estimate

    def _build_inputs(
        self,
        building: BuildingLike,
        assumption: AssumptionLike,
        location: SolarLocation,
    ) -> SolarInputs:
        """Assemble :class:`SolarInputs` from the building, assumptions, site."""
        latitude, longitude = self._resolve_coordinates(building, location)
        return SolarInputs(
            roof_area_m2=float(building.area_m2),
            latitude=latitude,
            longitude=longitude,
            timezone=location.timezone,
            altitude=location.altitude,
            tilt_deg=assumption.tilt_deg,
            azimuth_deg=assumption.azimuth_deg,
            usable_roof_fraction=assumption.usable_roof_fraction,
            power_density_w_m2=assumption.power_density_w_m2,
            system_losses=assumption.system_losses,
            shading=assumption.shading,
        )

    @staticmethod
    def _resolve_coordinates(
        building: BuildingLike, location: SolarLocation
    ) -> tuple[float, float]:
        """Resolve (lat, lon) preferring explicit location, else the centroid."""
        if location.latitude is not None and location.longitude is not None:
            return location.latitude, location.longitude
        centroid = building.centroid
        # GEOS Point in EPSG:4326: x = longitude, y = latitude.
        return float(centroid.y), float(centroid.x)

    def _resolve_method_version(self) -> CalculationMethodVersion:
        """Return the methodology version, resolving lazily on first use."""
        if self._method_version is None:
            self._method_version = self._registry.get_active()
        return self._method_version

    @staticmethod
    def _classify_inputs(inputs: SolarInputs, source: str) -> dict[str, Any]:
        """Return a JSON-serializable classified copy of the inputs."""
        classified = asdict(inputs)
        classified["source"] = source
        return classified
