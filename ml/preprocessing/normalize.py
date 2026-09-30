"""Per-image, per-band percentile normalization (canonical preprocessing).

Ports the canonical preprocessing described in ``CONTEXT.md`` section 1:
per-image per-band percentile stretch with ``pmin=2``/``pmax=98``, clipped to
``[0, 1]``, with a guard for near-constant bands and NaN sanitization.
"""

from __future__ import annotations

import logging

import numpy as np

logger = logging.getLogger(__name__)


def percentile_normalize(
    img: np.ndarray,
    pmin: float = 2.0,
    pmax: float = 98.0,
    bands: tuple[int, ...] = (1, 2, 3),
    eps: float = 1e-6,
) -> np.ndarray:
    """Percentile-normalize selected bands of an image to ``[0, 1]``.

    The normalization is computed per image and per band using percentiles over
    the whole image. Each selected band ``b`` is stretched using its ``pmin`` and
    ``pmax`` percentiles, clipped to ``[0, 1]``. Bands whose dynamic range
    ``hi - lo`` is below ``eps`` are set to all zeros to avoid division blow-up.
    Non-finite values are replaced with zero via :func:`numpy.nan_to_num`.

    Args:
        img: Input array shaped ``(H, W, C)`` or ``(C, H, W)`` where ``C`` is
            large enough to index all requested ``bands``. Band indices are
            1-based (``(1, 2, 3)`` selects R, G, B = B04, B03, B02).
        pmin: Lower percentile in ``[0, 100]``.
        pmax: Upper percentile in ``[0, 100]``.
        bands: 1-based band indices to extract, in output channel order.
        eps: Minimum dynamic range; bands below this become all zeros.

    Returns:
        A ``float32`` array shaped ``(H, W, len(bands))`` with values in ``[0, 1]``.

    Raises:
        ValueError: If ``img`` is not 3-dimensional or a requested band index is
            out of range.
    """
    if img.ndim != 3:
        raise ValueError(f"expected a 3-D image, got shape {img.shape!r}")

    # Detect channel axis. When both the first and last axes are large enough
    # to hold the requested bands, treat the *smaller* axis as the channel axis
    # (a real raster's channel count is far below its height/width).
    max_band = max(bands)
    first, last = img.shape[0], img.shape[-1]
    first_ok = first >= max_band
    last_ok = last >= max_band
    if first_ok and last_ok:
        channels_last = last <= first
    elif last_ok:
        channels_last = True
    elif first_ok:
        channels_last = False
    else:
        raise ValueError(
            f"band index {max_band} out of range for image shape {img.shape!r}"
        )

    arr = img if channels_last else np.moveaxis(img, 0, -1)
    height, width, _ = arr.shape
    out = np.zeros((height, width, len(bands)), dtype=np.float32)

    for out_idx, band in enumerate(bands):
        channel = arr[..., band - 1].astype(np.float64)
        finite = channel[np.isfinite(channel)]
        if finite.size == 0:
            logger.debug("band has no finite values", extra={"band": band})
            continue
        lo = float(np.percentile(finite, pmin))
        hi = float(np.percentile(finite, pmax))
        if hi - lo < eps:
            logger.debug(
                "band dynamic range below eps -> zeros",
                extra={"band": band, "lo": lo, "hi": hi, "eps": eps},
            )
            continue
        scaled = (channel - lo) / (hi - lo)
        scaled = np.clip(scaled, 0.0, 1.0)
        out[..., out_idx] = np.nan_to_num(scaled, nan=0.0, posinf=0.0, neginf=0.0)

    return out


__all__ = ["percentile_normalize"]
