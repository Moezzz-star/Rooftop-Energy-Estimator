"""Tests for :class:`ml.preprocessing.tiling.Tiler`."""

from __future__ import annotations

import numpy as np

from ml.preprocessing.tiling import Tiler


def test_tiles_force_final_edge_start() -> None:
    """The last start along each axis is exactly length - tile."""
    tiler = Tiler(tile=256, stride=128)
    coords = tiler.tiles(600, 700)
    rows = sorted({r for r, _ in coords})
    cols = sorted({c for _, c in coords})
    assert rows[0] == 0
    assert cols[0] == 0
    assert rows[-1] == 600 - 256
    assert cols[-1] == 700 - 256


def test_tiles_small_image_single_tile() -> None:
    """An image not larger than a tile yields a single (0, 0) coordinate."""
    tiler = Tiler(tile=256, stride=128)
    assert tiler.tiles(100, 100) == [(0, 0)]


def test_stitch_reconstructs_constant_field() -> None:
    """Overlap-averaging constant tiles reproduces the constant everywhere."""
    tiler = Tiler(tile=256, stride=128)
    h, w = 500, 480
    coords = tiler.tiles(h, w)
    preds = [np.full((256, 256), 0.7, dtype=np.float32) for _ in coords]
    stitched = tiler.stitch(preds, coords, (h, w))
    assert stitched.shape == (h, w)
    assert np.allclose(stitched, 0.7, atol=1e-5)


def test_stitch_averages_overlap() -> None:
    """Two overlapping tiles average their values in the overlap region."""
    tiler = Tiler(tile=4, stride=2)
    coords = [(0, 0), (0, 2)]
    left = np.full((4, 4), 1.0, dtype=np.float32)
    right = np.full((4, 4), 3.0, dtype=np.float32)
    stitched = tiler.stitch([left, right], coords, (4, 6))
    # Columns 2..3 are covered by both tiles -> average of 1 and 3 = 2.
    assert np.allclose(stitched[:, 2:4], 2.0)
    assert np.allclose(stitched[:, 0:2], 1.0)
    assert np.allclose(stitched[:, 4:6], 3.0)


def test_stitch_length_mismatch_raises() -> None:
    """Mismatched preds/coords lengths raise ValueError."""
    tiler = Tiler(tile=4, stride=2)
    try:
        tiler.stitch([np.zeros((4, 4))], [(0, 0), (0, 2)], (4, 6))
    except ValueError:
        return
    raise AssertionError("expected ValueError")
