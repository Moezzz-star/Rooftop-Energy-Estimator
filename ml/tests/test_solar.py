"""Tests for :mod:`ml.inference.solar` (real pvlib run)."""

from __future__ import annotations

import dataclasses

import pytest

from ml.configs import SolarConfig
from ml.inference.solar import SolarInputs, SolarModel


def _valid_inputs() -> SolarInputs:
    """Return a valid, representative set of solar inputs (Berlin-ish)."""
    cfg = SolarConfig()
    return SolarInputs(
        roof_area_m2=100.0,
        latitude=52.52,
        longitude=13.405,
        timezone="Europe/Berlin",
        altitude=34.0,
        tilt_deg=cfg.tilt_deg,
        azimuth_deg=cfg.azimuth_deg,
        usable_roof_fraction=cfg.usable_roof_fraction,
        power_density_w_m2=cfg.power_density_w_m2,
        system_losses=cfg.system_losses,
        shading=cfg.shading,
    )


def test_estimate_produces_plausible_results() -> None:
    """A real pvlib run yields positive energy and a plausible specific yield."""
    model = SolarModel()
    result = model.estimate(_valid_inputs())

    assert result.annual_kwh > 0
    assert result.capacity_kwp == pytest.approx(100.0 * 0.70 * 200.0 / 1000.0)
    # Clear-sky specific yield is optimistic but must be physically plausible.
    assert 500.0 <= result.specific_yield <= 2500.0
    assert result.usable_area_m2 == pytest.approx(70.0)


def test_monthly_length_and_sum() -> None:
    """Monthly values number 12 and sum to the reported annual energy."""
    result = SolarModel().estimate(_valid_inputs())
    assert len(result.monthly_kwh) == 12
    assert all(v >= 0 for v in result.monthly_kwh)
    assert sum(result.monthly_kwh) == pytest.approx(result.annual_kwh, rel=1e-6)


def test_version_default() -> None:
    """The default methodology version is stable."""
    assert SolarModel().version == "solar-v1"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("roof_area_m2", -1.0),
        ("usable_roof_fraction", 0.0),
        ("usable_roof_fraction", 1.5),
        ("system_losses", 1.0),
        ("system_losses", -0.1),
        ("latitude", 91.0),
        ("longitude", 181.0),
        ("tilt_deg", 91.0),
        ("azimuth_deg", 361.0),
        ("power_density_w_m2", 0.0),
        ("shading", 1.5),
        ("timezone", "Not/AZone"),
    ],
)
def test_validate_rejects_bad_inputs(field: str, value: object) -> None:
    """Each out-of-bounds field triggers a ValueError from _validate."""
    bad = dataclasses.replace(_valid_inputs(), **{field: value})  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        SolarModel().estimate(bad)
