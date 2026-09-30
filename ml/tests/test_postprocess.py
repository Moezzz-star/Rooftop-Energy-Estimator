"""Tests for :func:`ml.inference.postprocess.cleanup_mask`."""

from __future__ import annotations

import numpy as np

from ml.inference.postprocess import cleanup_mask


def test_threshold_produces_boolean_mask() -> None:
    """Output is a boolean array of the same shape."""
    prob = np.zeros((10, 10), dtype=np.float32)
    prob[2:6, 2:6] = 0.9
    mask = cleanup_mask(prob, threshold=0.2)
    assert mask.dtype == bool
    assert mask.shape == prob.shape
    assert mask[2:6, 2:6].all()


def test_removes_small_objects() -> None:
    """A tiny speck below min_object is removed while a large blob survives."""
    prob = np.zeros((20, 20), dtype=np.float32)
    prob[0, 0] = 0.99  # single-pixel speck (size 1 < 8)
    prob[5:12, 5:12] = 0.99  # 49-pixel blob
    mask = cleanup_mask(prob, threshold=0.2, min_object=8, min_hole=8)
    assert not mask[0, 0]
    assert mask[5:12, 5:12].all()


def test_fills_small_holes() -> None:
    """A small hole inside a blob is filled."""
    prob = np.full((20, 20), 0.99, dtype=np.float32)
    prob[10, 10] = 0.0  # single-pixel hole
    mask = cleanup_mask(prob, threshold=0.2, min_object=8, min_hole=8)
    assert mask[10, 10]


def test_empty_after_threshold() -> None:
    """An all-low probability map yields an all-False mask."""
    prob = np.full((8, 8), 0.05, dtype=np.float32)
    mask = cleanup_mask(prob, threshold=0.2)
    assert not mask.any()
