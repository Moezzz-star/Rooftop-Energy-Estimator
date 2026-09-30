"""Tests for :func:`ml.preprocessing.normalize.percentile_normalize`."""

from __future__ import annotations

import numpy as np

from ml.preprocessing.normalize import percentile_normalize


def test_output_shape_and_range() -> None:
    """Output is (H, W, 3) float32 with values in [0, 1]."""
    rng = np.random.default_rng(0)
    img = rng.uniform(0, 5000, size=(32, 40, 4)).astype(np.float32)
    out = percentile_normalize(img)
    assert out.shape == (32, 40, 3)
    assert out.dtype == np.float32
    assert out.min() >= 0.0
    assert out.max() <= 1.0


def test_channels_first_input() -> None:
    """A (C, H, W) array is handled and yields channel-last output."""
    rng = np.random.default_rng(1)
    img = rng.uniform(0, 1000, size=(4, 16, 24)).astype(np.float32)
    out = percentile_normalize(img)
    assert out.shape == (16, 24, 3)


def test_constant_band_guard_yields_zeros() -> None:
    """A band with zero dynamic range is emitted as all zeros."""
    img = np.zeros((10, 10, 3), dtype=np.float32)
    img[..., 0] = 7.0  # constant band 1
    img[..., 1] = 7.0  # constant band 2
    img[..., 2] = 7.0  # constant band 3
    out = percentile_normalize(img)
    assert np.all(out == 0.0)


def test_nan_and_inf_are_sanitized() -> None:
    """NaN/inf inputs do not propagate into the output."""
    rng = np.random.default_rng(2)
    img = rng.uniform(1, 100, size=(12, 12, 3)).astype(np.float32)
    img[0, 0, 0] = np.nan
    img[1, 1, 1] = np.inf
    img[2, 2, 2] = -np.inf
    out = percentile_normalize(img)
    assert np.isfinite(out).all()


def test_bands_selection_order() -> None:
    """Selecting bands (3, 2, 1) reverses channel order of a ramp image."""
    img = np.zeros((8, 8, 3), dtype=np.float32)
    img[..., 0] = np.tile(np.linspace(0, 1, 8), (8, 1))
    img[..., 1] = np.tile(np.linspace(0, 2, 8), (8, 1))
    img[..., 2] = np.tile(np.linspace(0, 3, 8), (8, 1))
    out = percentile_normalize(img, bands=(3, 2, 1))
    # First output channel comes from band 3 (index 2).
    assert out[..., 0].max() == 1.0
