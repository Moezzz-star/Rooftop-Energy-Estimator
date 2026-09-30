"""Bounded validation of DEC-01 solar assumption overrides (§15-style rules).

This is the single source of truth for assumption-input bounds. It is invoked
from :class:`apps.analyses.services.AnalysisService` (so both the HTTP path and
direct service callers are validated) and raises :class:`common.errors.
ValidationError` with structured, field-keyed ``details`` so the API surfaces a
consistent error envelope.

The bounds mirror ``ml.inference.solar.SolarModel._validate`` (the pipeline's
own guardrails) but reject bad input *before* an analysis is ever persisted or
submitted, keeping the frozen snapshot always valid.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from common.errors import ValidationError

from .models import AssumptionSource

# Reasonable upper bounds; not physical maxima but guardrails against typos /
# nonsensical input that would otherwise poison the deterministic snapshot.
_MAX_POWER_DENSITY_W_M2 = 1000.0
_MIN_TEMP_AIR_C = -90.0
_MAX_TEMP_AIR_C = 60.0

# Each validator returns True when the (already-numeric) value is in range.
_BOUNDS: dict[str, tuple[Callable[[float], bool], str]] = {
    "usable_roof_fraction": (lambda v: 0.0 < v <= 1.0, "must be in (0, 1]"),
    "power_density_w_m2": (
        lambda v: 0.0 < v <= _MAX_POWER_DENSITY_W_M2,
        f"must be > 0 and <= {_MAX_POWER_DENSITY_W_M2:g} W/m^2",
    ),
    "system_losses": (lambda v: 0.0 <= v < 1.0, "must be in [0, 1)"),
    "module_eff": (lambda v: 0.0 < v <= 1.0, "must be in (0, 1]"),
    "tilt_deg": (lambda v: 0.0 <= v <= 90.0, "must be in [0, 90]"),
    "azimuth_deg": (lambda v: 0.0 <= v <= 360.0, "must be in [0, 360]"),
    "shading": (lambda v: 0.0 <= v <= 1.0, "must be in [0, 1]"),
    "temp_air": (
        lambda v: _MIN_TEMP_AIR_C <= v <= _MAX_TEMP_AIR_C,
        f"must be in [{_MIN_TEMP_AIR_C:g}, {_MAX_TEMP_AIR_C:g}] degC",
    ),
    "wind": (lambda v: v >= 0.0, "must be >= 0"),
}


def validate_assumptions(overrides: dict[str, Any]) -> None:
    """Validate assumption overrides against DEC-01 bounds.

    Only keys present in ``overrides`` are checked (partial updates are allowed);
    unknown keys are ignored here because the service filters to the recognised
    assumption fields before persisting.

    Args:
        overrides: Raw assumption override mapping (field name -> value).

    Raises:
        ValidationError: If any recognised field is non-numeric or out of range.
            All offending fields are reported together in ``details``.
    """
    errors: dict[str, str] = {}

    source = overrides.get("source")
    if source is not None and source not in AssumptionSource.values:
        errors["source"] = f"must be one of {sorted(AssumptionSource.values)}"

    for field, (in_range, rule) in _BOUNDS.items():
        if field not in overrides:
            continue
        value = overrides[field]
        number = _as_float(value)
        if number is None:
            errors[field] = "must be a number"
        elif not in_range(number):
            errors[field] = rule

    if errors:
        raise ValidationError(
            "One or more assumption values are out of range.",
            details={"assumptions": errors},
        )


def _as_float(value: Any) -> float | None:
    """Coerce ``value`` to ``float`` or return ``None`` (bool is rejected)."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None
