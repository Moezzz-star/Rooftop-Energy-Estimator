"""Sliding-window tiling and overlap-average stitching.

Ports the canonical tiling from ``CONTEXT.md`` section 1: ``tile=256``,
``stride=128``, forcing the final start along each axis to ``length - tile`` so
edge pixels are always covered, and overlap-average stitching of predictions.
"""

from __future__ import annotations

import logging

import numpy as np

logger = logging.getLogger(__name__)


class Tiler:
    """Generate tile coordinates and stitch overlapping predictions.

    The tiler assumes callers reflect-pad rasters smaller than ``tile`` before
    requesting coordinates (see :class:`ml.inference.predictor.UNetPredictor`).
    """

    def __init__(self, tile: int = 256, stride: int = 128) -> None:
        """Initialize the tiler.

        Args:
            tile: Square tile side length in pixels (must be positive).
            stride: Step between consecutive tile starts (must be positive).

        Raises:
            ValueError: If ``tile`` or ``stride`` is not positive.
        """
        if tile <= 0:
            raise ValueError(f"tile must be positive, got {tile}")
        if stride <= 0:
            raise ValueError(f"stride must be positive, got {stride}")
        self.tile = tile
        self.stride = stride

    def _starts(self, length: int) -> list[int]:
        """Compute tile start offsets along one axis of the given length.

        The final start is forced to ``length - tile`` so the trailing edge is
        always fully covered. Assumes ``length >= tile``.
        """
        if length <= self.tile:
            return [0]
        starts = list(range(0, length - self.tile + 1, self.stride))
        last = length - self.tile
        if starts[-1] != last:
            starts.append(last)
        return starts

    def tiles(self, h: int, w: int) -> list[tuple[int, int]]:
        """Return the list of ``(row, col)`` tile start coordinates.

        Args:
            h: Image height in pixels (assumed ``>= tile`` after any padding).
            w: Image width in pixels (assumed ``>= tile`` after any padding).

        Returns:
            Row-major list of ``(row, col)`` top-left tile origins.
        """
        rows = self._starts(h)
        cols = self._starts(w)
        return [(r, c) for r in rows for c in cols]

    def stitch(
        self,
        preds: list[np.ndarray],
        coords: list[tuple[int, int]],
        shape: tuple[int, int],
    ) -> np.ndarray:
        """Overlap-average tile predictions back into a full map.

        Args:
            preds: Per-tile 2-D probability arrays, each ``(tile, tile)``.
            coords: Matching ``(row, col)`` origins from :meth:`tiles`.
            shape: Target ``(height, width)`` to crop the result to. May be
                smaller than the padded canvas used during tiling.

        Returns:
            A ``float32`` array of shape ``shape`` holding the overlap-averaged
            probabilities.

        Raises:
            ValueError: If ``preds`` and ``coords`` lengths differ.
        """
        if len(preds) != len(coords):
            raise ValueError(
                f"preds ({len(preds)}) and coords ({len(coords)}) length mismatch"
            )
        # Canvas must cover both the requested shape and every tile extent.
        canvas_h = shape[0]
        canvas_w = shape[1]
        for (row, col), pred in zip(coords, preds):
            canvas_h = max(canvas_h, row + pred.shape[0])
            canvas_w = max(canvas_w, col + pred.shape[1])

        prob_sum = np.zeros((canvas_h, canvas_w), dtype=np.float64)
        weight_sum = np.zeros((canvas_h, canvas_w), dtype=np.float64)

        for (row, col), pred in zip(coords, preds):
            th, tw = pred.shape[:2]
            prob_sum[row : row + th, col : col + tw] += pred.astype(np.float64)
            weight_sum[row : row + th, col : col + tw] += 1.0

        with np.errstate(invalid="ignore", divide="ignore"):
            averaged = np.where(weight_sum > 0, prob_sum / weight_sum, 0.0)

        cropped = averaged[: shape[0], : shape[1]]
        return cropped.astype(np.float32)


__all__ = ["Tiler"]
