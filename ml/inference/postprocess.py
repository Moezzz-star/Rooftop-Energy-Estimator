"""Morphological cleanup of a probability map into a boolean mask.

Ports the canonical post-processing from ``CONTEXT.md`` section 1: threshold at
``0.2`` then remove small objects and fill small holes.
"""

from __future__ import annotations

import logging

import numpy as np
from skimage.morphology import remove_small_holes, remove_small_objects

logger = logging.getLogger(__name__)


def cleanup_mask(
    prob: np.ndarray,
    threshold: float = 0.2,
    min_object: int = 8,
    min_hole: int = 8,
) -> np.ndarray:
    """Threshold a probability map and clean up small artifacts.

    Args:
        prob: 2-D probability map with values in ``[0, 1]``.
        threshold: Probabilities strictly greater than this become foreground.
        min_object: Minimum connected-component size to keep (pixels).
        min_hole: Maximum hole area to fill (pixels).

    Returns:
        A boolean array with the same shape as ``prob``.

    Raises:
        ValueError: If ``prob`` is not 2-dimensional.
    """
    if prob.ndim != 2:
        raise ValueError(f"expected a 2-D probability map, got shape {prob.shape!r}")

    mask = prob > threshold
    if not mask.any():
        logger.debug("empty mask after threshold", extra={"threshold": threshold})
        return mask

    cleaned = remove_small_objects(mask, min_size=min_object)
    cleaned = remove_small_holes(cleaned, area_threshold=min_hole)
    result: np.ndarray = np.asarray(cleaned, dtype=bool)
    return result


__all__ = ["cleanup_mask"]
