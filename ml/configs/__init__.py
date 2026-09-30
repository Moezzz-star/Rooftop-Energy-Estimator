"""Configuration dataclasses for the ML pipeline.

Defaults encode the canonical decisions from ``docs/decisions/CONTEXT.md``
(notably DEC-01 solar defaults and the canonical preprocessing/tiling values).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PreprocessConfig:
    """Per-image percentile normalization configuration.

    Attributes:
        pmin: Lower percentile used for per-band normalization.
        pmax: Upper percentile used for per-band normalization.
        bands: 1-based band indices interpreted as (R, G, B) = (B04, B03, B02).
        eps: Guard threshold; bands whose ``hi - lo`` is below this are zeroed.
    """

    pmin: float = 2.0
    pmax: float = 98.0
    bands: tuple[int, ...] = (1, 2, 3)
    eps: float = 1e-6


@dataclass(frozen=True)
class TilingConfig:
    """Sliding-window tiling configuration.

    Attributes:
        tile: Square tile side length in pixels.
        stride: Step between consecutive tile starts in pixels.
    """

    tile: int = 256
    stride: int = 128


@dataclass(frozen=True)
class InferenceConfig:
    """Segmentation inference and post-processing configuration.

    Attributes:
        batch_size: Number of tiles per model prediction batch.
        threshold: Probability threshold applied to produce a binary mask.
        min_object: Minimum connected-component size retained (pixels).
        min_hole: Minimum hole area filled (pixels).
        min_area_m2: Minimum polygon area retained after vectorization (m^2).
        simplify_tol_m: Polygon simplification tolerance in metres.
    """

    batch_size: int = 16
    threshold: float = 0.2
    min_object: int = 8
    min_hole: int = 8
    min_area_m2: float = 20.0
    simplify_tol_m: float = 0.5


@dataclass(frozen=True)
class SolarConfig:
    """Default solar-estimation assumptions (DEC-01).

    Attributes:
        usable_roof_fraction: Fraction of roof area usable for modules.
        power_density_w_m2: Installed DC power density per usable m^2.
        system_losses: Aggregate AC-side system loss fraction.
        module_eff: Nominal module efficiency (informational).
        gamma_pdc: Temperature coefficient of DC power (1/degC).
        eta_inv_nom: Nominal inverter efficiency.
        temp_air: Ambient air temperature assumption (degC).
        wind: Wind speed assumption (m/s).
        tilt_deg: Default fixed module tilt (degrees).
        azimuth_deg: Default fixed module azimuth (degrees, 180 = equatorward N. hemi).
        shading: Fraction of direct POA irradiance retained (1 = no shading).
    """

    usable_roof_fraction: float = 0.70
    power_density_w_m2: float = 200.0
    system_losses: float = 0.14
    module_eff: float = 0.20
    gamma_pdc: float = -0.0035
    eta_inv_nom: float = 0.96
    temp_air: float = 20.0
    wind: float = 1.0
    tilt_deg: float = 20.0
    azimuth_deg: float = 180.0
    shading: float = 1.0


DEFAULT_PREPROCESS = PreprocessConfig()
DEFAULT_TILING = TilingConfig()
DEFAULT_INFERENCE = InferenceConfig()
DEFAULT_SOLAR = SolarConfig()

__all__ = [
    "PreprocessConfig",
    "TilingConfig",
    "InferenceConfig",
    "SolarConfig",
    "DEFAULT_PREPROCESS",
    "DEFAULT_TILING",
    "DEFAULT_INFERENCE",
    "DEFAULT_SOLAR",
]
