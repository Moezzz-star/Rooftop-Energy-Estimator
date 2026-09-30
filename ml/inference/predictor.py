"""Windowed, batched U-Net inference producing a probability map.

Wraps a pre-loaded Keras model and a :class:`~ml.preprocessing.tiling.Tiler`.
Reflect-pads inputs smaller than the tile, runs batched tiled prediction, and
overlap-averages the result back to the original spatial shape.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Protocol

import numpy as np

from ml.preprocessing.tiling import Tiler

logger = logging.getLogger(__name__)


class ModelNotFoundError(FileNotFoundError):
    """Raised when a Keras model file cannot be found on disk."""


class _KerasModel(Protocol):
    """Minimal structural type for the subset of Keras used here."""

    def predict(self, x: Any, *, verbose: int = ...) -> Any:
        """Run a forward pass over a batch of tiles."""
        ...


def load_keras_model(path: str | Path) -> Any:
    """Load a Keras model from ``path`` with ``compile=False``.

    Args:
        path: Filesystem path to a ``.keras`` model file.

    Returns:
        The loaded Keras model object.

    Raises:
        ModelNotFoundError: If ``path`` does not exist, with remediation hint.
        RuntimeError: If TensorFlow/Keras is unavailable or loading fails.
    """
    model_path = Path(path)
    if not model_path.is_file():
        raise ModelNotFoundError(
            f"Keras model not found at '{model_path}'. Download it with "
            "'python scripts/download_model.py' (see docs), or generate the tiny "
            "CI model with 'python scripts/generate_ci_model.py'."
        )
    try:
        from tensorflow import keras  # type: ignore[import-untyped]
    except ImportError as exc:  # pragma: no cover - env-dependent
        raise RuntimeError(
            "TensorFlow/Keras is required to load models but is not installed."
        ) from exc
    try:
        return keras.models.load_model(model_path, compile=False)
    except (OSError, ValueError) as exc:
        raise RuntimeError(f"failed to load Keras model at '{model_path}'") from exc


class UNetPredictor:
    """Produce per-pixel building probabilities from an RGB image.

    The predictor never loads model files itself; inject a pre-loaded model
    (use :func:`load_keras_model`). It handles reflect-padding, windowed tiling,
    batched prediction, and overlap-average stitching.
    """

    def __init__(
        self,
        model: _KerasModel,
        tiler: Tiler,
        batch_size: int = 16,
    ) -> None:
        """Initialize the predictor.

        Args:
            model: A loaded Keras model with a ``predict`` method mapping
                ``(N, tile, tile, 3)`` inputs to ``(N, tile, tile, 1)`` sigmoids.
            tiler: Configured tiler providing coordinates and stitching.
            batch_size: Number of tiles per ``model.predict`` call.

        Raises:
            ValueError: If ``batch_size`` is not positive.
        """
        if batch_size <= 0:
            raise ValueError(f"batch_size must be positive, got {batch_size}")
        self.model = model
        self.tiler = tiler
        self.batch_size = batch_size

    def predict_prob(self, image: np.ndarray) -> np.ndarray:
        """Return a probability map for ``image``.

        Args:
            image: Normalized image shaped ``(H, W, 3)`` with values in ``[0, 1]``.

        Returns:
            A ``float32`` array shaped ``(H, W)`` with probabilities in ``[0, 1]``.

        Raises:
            ValueError: If ``image`` is not ``(H, W, 3)``.
        """
        if image.ndim != 3 or image.shape[2] != 3:
            raise ValueError(f"expected image of shape (H, W, 3), got {image.shape!r}")

        orig_h, orig_w = image.shape[:2]
        tile = self.tiler.tile

        pad_h = max(0, tile - orig_h)
        pad_w = max(0, tile - orig_w)
        if pad_h or pad_w:
            padded = np.pad(
                image,
                ((0, pad_h), (0, pad_w), (0, 0)),
                mode="reflect",
            )
            logger.debug(
                "reflect-padded small image",
                extra={"pad_h": pad_h, "pad_w": pad_w},
            )
        else:
            padded = image

        padded = padded.astype(np.float32, copy=False)
        canvas_h, canvas_w = padded.shape[:2]
        coords = self.tiler.tiles(canvas_h, canvas_w)

        tiles = [padded[r : r + tile, c : c + tile, :] for (r, c) in coords]

        preds: list[np.ndarray] = []
        for start in range(0, len(tiles), self.batch_size):
            batch = np.stack(tiles[start : start + self.batch_size], axis=0)
            raw = self.model.predict(batch, verbose=0)
            batch_out = np.asarray(raw, dtype=np.float32)
            # Squeeze trailing single channel if present -> (N, tile, tile).
            if batch_out.ndim == 4 and batch_out.shape[-1] == 1:
                batch_out = batch_out[..., 0]
            preds.extend(batch_out[i] for i in range(batch_out.shape[0]))

        stitched = self.tiler.stitch(preds, coords, (canvas_h, canvas_w))
        return stitched[:orig_h, :orig_w].astype(np.float32)


__all__ = ["UNetPredictor", "load_keras_model", "ModelNotFoundError"]
