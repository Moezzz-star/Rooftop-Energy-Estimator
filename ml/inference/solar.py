"""Versioned solar-yield estimation via pvlib (pure calculation).

Ports the canonical pvlib chain from ``CONTEXT.md`` section 1 and DEC-01 with a
fixed tilt/azimuth (no orientation sweep). ``SolarEstimationService`` in the
backend wraps this pure model. No Django imports.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache
from zoneinfo import available_timezones

import pandas as pd  # type: ignore[import-untyped]
from pvlib import inverter, irradiance, pvsystem, temperature  # type: ignore[import-untyped]
from pvlib.location import Location  # type: ignore[import-untyped]
from pvlib.temperature import TEMPERATURE_MODEL_PARAMETERS  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)

# Representative non-leap simulation year for the hourly full-year run.
_SIM_YEAR = 2023
_SAPM_PARAMS = TEMPERATURE_MODEL_PARAMETERS["sapm"]["open_rack_glass_glass"]


@lru_cache(maxsize=1)
def _valid_timezones() -> frozenset[str]:
    """Return the set of valid IANA time-zone names (cached)."""
    return frozenset(available_timezones())


@dataclass(frozen=True)
class SolarInputs:
    """Inputs to a single fixed-orientation solar estimate.

    Attributes:
        roof_area_m2: Total roof area (m^2).
        latitude: Site latitude in degrees, ``[-90, 90]``.
        longitude: Site longitude in degrees, ``[-180, 180]``.
        timezone: IANA time-zone name (e.g. ``"Europe/Berlin"``).
        altitude: Site altitude above sea level (m).
        tilt_deg: Fixed module tilt, ``[0, 90]``.
        azimuth_deg: Fixed module azimuth, ``[0, 360]`` (180 = due south).
        usable_roof_fraction: Usable fraction of roof, ``(0, 1]``.
        power_density_w_m2: Installed DC power density per usable m^2 (> 0).
        system_losses: Aggregate AC-side loss fraction, ``[0, 1)``.
        shading: Fraction of direct POA retained, ``[0, 1]`` (1 = no shading).
    """

    roof_area_m2: float
    latitude: float
    longitude: float
    timezone: str
    altitude: float
    tilt_deg: float
    azimuth_deg: float
    usable_roof_fraction: float
    power_density_w_m2: float
    system_losses: float
    shading: float


@dataclass(frozen=True)
class SolarResult:
    """Result of a solar estimate.

    Attributes:
        monthly_kwh: Twelve monthly AC energy values (kWh), Jan..Dec.
        annual_kwh: Annual AC energy (kWh).
        capacity_kwp: Installed DC capacity (kWp).
        specific_yield: Annual energy per installed capacity (kWh/kWp).
        usable_area_m2: Roof area assumed usable for modules (m^2).
    """

    monthly_kwh: list[float]
    annual_kwh: float
    capacity_kwp: float
    specific_yield: float
    usable_area_m2: float


class SolarModel:
    """Fixed-orientation solar-yield model (pvlib clear-sky, PVWatts)."""

    def __init__(self, version: str = "solar-v1") -> None:
        """Initialize the model.

        Args:
            version: Methodology version identifier for provenance.
        """
        self.version = version

    def _validate(self, x: SolarInputs) -> None:
        """Validate inputs per CONTEXT.md section 15.

        Args:
            x: Candidate inputs.

        Raises:
            ValueError: If any input violates the documented bounds.
        """
        if x.roof_area_m2 < 0:
            raise ValueError(f"roof_area_m2 must be >= 0, got {x.roof_area_m2}")
        if not (0 < x.usable_roof_fraction <= 1):
            raise ValueError(
                f"usable_roof_fraction must be in (0, 1], got {x.usable_roof_fraction}"
            )
        usable_area = x.roof_area_m2 * x.usable_roof_fraction
        if usable_area > x.roof_area_m2 + 1e-9:
            raise ValueError("usable_area must not exceed roof_area")
        if x.power_density_w_m2 <= 0:
            raise ValueError(
                f"power_density_w_m2 must be > 0, got {x.power_density_w_m2}"
            )
        capacity_kwp = usable_area * x.power_density_w_m2 / 1000.0
        if capacity_kwp < 0:
            raise ValueError("capacity_kwp must be non-negative")
        if not (0 <= x.system_losses < 1):
            raise ValueError(f"system_losses must be in [0, 1), got {x.system_losses}")
        if not (-90 <= x.latitude <= 90):
            raise ValueError(f"latitude must be in [-90, 90], got {x.latitude}")
        if not (-180 <= x.longitude <= 180):
            raise ValueError(f"longitude must be in [-180, 180], got {x.longitude}")
        if not (0 <= x.tilt_deg <= 90):
            raise ValueError(f"tilt_deg must be in [0, 90], got {x.tilt_deg}")
        if not (0 <= x.azimuth_deg <= 360):
            raise ValueError(f"azimuth_deg must be in [0, 360], got {x.azimuth_deg}")
        if not (0 <= x.shading <= 1):
            raise ValueError(f"shading must be in [0, 1], got {x.shading}")
        if x.timezone not in _valid_timezones():
            raise ValueError(f"timezone is not a valid IANA name: {x.timezone!r}")

    def estimate(self, x: SolarInputs) -> SolarResult:
        """Estimate monthly and annual AC energy for the given inputs.

        Args:
            x: Validated solar inputs (validated internally).

        Returns:
            A :class:`SolarResult` with 12 monthly kWh values plus annual energy,
            installed capacity, specific yield, and usable area.

        Raises:
            ValueError: If inputs are invalid (see :meth:`_validate`).
        """
        self._validate(x)

        usable_area_m2 = x.roof_area_m2 * x.usable_roof_fraction
        pdc0_w = usable_area_m2 * x.power_density_w_m2
        capacity_kwp = pdc0_w / 1000.0

        times = pd.date_range(
            start=f"{_SIM_YEAR}-01-01 00:00",
            end=f"{_SIM_YEAR}-12-31 23:00",
            freq="1h",
            tz=x.timezone,
        )

        location = Location(
            latitude=x.latitude,
            longitude=x.longitude,
            tz=x.timezone,
            altitude=x.altitude,
        )

        clearsky = location.get_clearsky(times, model="ineichen")
        solar_position = location.get_solarposition(times)
        dni_extra = irradiance.get_extra_radiation(times)

        total_irrad = irradiance.get_total_irradiance(
            surface_tilt=x.tilt_deg,
            surface_azimuth=x.azimuth_deg,
            solar_zenith=solar_position["apparent_zenith"],
            solar_azimuth=solar_position["azimuth"],
            dni=clearsky["dni"],
            ghi=clearsky["ghi"],
            dhi=clearsky["dhi"],
            dni_extra=dni_extra,
            model="haydavies",
        )

        poa_global = total_irrad["poa_global"].fillna(0.0)
        poa_direct = total_irrad["poa_direct"].fillna(0.0)
        poa_diffuse = total_irrad["poa_diffuse"].fillna(0.0)
        poa_eff = poa_diffuse + poa_direct * x.shading

        temp_cell = temperature.sapm_cell(
            poa_global=poa_global,
            temp_air=20.0,
            wind_speed=1.0,
            **_SAPM_PARAMS,
        )

        # pvlib's pvwatts_dc signature is positional
        # (g_poa_effective, temp_cell, pdc0, gamma_pdc) and the first two
        # keyword names differ across pvlib releases; pass positionally.
        dc_power = pvsystem.pvwatts_dc(
            poa_eff,
            temp_cell,
            pdc0_w,
            gamma_pdc=-0.0035,
        )
        dc_power = dc_power.clip(lower=0.0).fillna(0.0)

        pac = inverter.pvwatts(pdc=dc_power, pdc0=pdc0_w, eta_inv_nom=0.96)
        pac = pac.clip(lower=0.0).fillna(0.0)
        pac_net = pac * (1.0 - x.system_losses)

        annual_kwh = float(pac_net.sum() / 1000.0)
        specific_yield = annual_kwh / capacity_kwp if capacity_kwp > 0 else 0.0

        monthly_kwh = self._monthly_kwh(pac_net)

        logger.info(
            "solar estimate complete",
            extra={
                "version": self.version,
                "capacity_kwp": capacity_kwp,
                "annual_kwh": annual_kwh,
                "specific_yield": specific_yield,
            },
        )

        return SolarResult(
            monthly_kwh=monthly_kwh,
            annual_kwh=annual_kwh,
            capacity_kwp=capacity_kwp,
            specific_yield=specific_yield,
            usable_area_m2=usable_area_m2,
        )

    @staticmethod
    def _monthly_kwh(pac_net: pd.Series) -> list[float]:
        """Resample net AC power (W, hourly) into 12 monthly kWh totals."""
        try:
            monthly = pac_net.resample("ME").sum() / 1000.0
        except ValueError:  # pragma: no cover - older pandas alias
            monthly = pac_net.resample("M").sum() / 1000.0
        values = [float(v) for v in monthly.to_numpy()]
        if len(values) != 12:
            # Pad/trim defensively so downstream always gets exactly 12.
            values = (values + [0.0] * 12)[:12]
        return values


__all__ = ["SolarInputs", "SolarResult", "SolarModel"]
