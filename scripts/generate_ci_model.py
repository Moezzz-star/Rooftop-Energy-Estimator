"""Generate a tiny, deterministic CI U-Net model for tests (DEC-05).

Builds a small randomly-initialized Keras model matching the production contract
``(256, 256, 3) -> sigmoid (1 channel)`` and saves it to
``ml/tests/fixtures/ci_unet.keras``. This lets the test-suite run *real*
inference without the 90 MB production model.

Usage:
    python scripts/generate_ci_model.py [--output PATH]
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_SEED = 42
_DEFAULT_OUTPUT = (
    Path(__file__).resolve().parents[1] / "ml" / "tests" / "fixtures" / "ci_unet.keras"
)


def build_ci_model() -> "object":
    """Build and return a tiny, deterministic U-Net-like Keras model.

    Returns:
        An uncompiled Keras model with input ``(256, 256, 3)`` and a single-channel
        sigmoid output of the same spatial size.

    Raises:
        RuntimeError: If TensorFlow/Keras is not installed.
    """
    try:
        import numpy as np
        import tensorflow as tf
        from tensorflow import keras
        from tensorflow.keras import layers
    except ImportError as exc:  # pragma: no cover - env-dependent
        raise RuntimeError(
            "TensorFlow is required to generate the CI model but is not installed."
        ) from exc

    np.random.seed(_SEED)
    tf.random.set_seed(_SEED)
    tf.keras.utils.set_random_seed(_SEED)

    inputs = keras.Input(shape=(256, 256, 3), name="image")
    # Tiny encoder.
    c1 = layers.Conv2D(4, 3, activation="relu", padding="same")(inputs)
    p1 = layers.MaxPooling2D(2)(c1)
    c2 = layers.Conv2D(8, 3, activation="relu", padding="same")(p1)
    # Tiny decoder with skip connection.
    u1 = layers.UpSampling2D(2)(c2)
    concat = layers.Concatenate()([u1, c1])
    c3 = layers.Conv2D(4, 3, activation="relu", padding="same")(concat)
    outputs = layers.Conv2D(1, 1, activation="sigmoid", name="mask")(c3)

    model = keras.Model(inputs=inputs, outputs=outputs, name="ci_unet")
    return model


def main(output: Path = _DEFAULT_OUTPUT) -> Path:
    """Build the CI model and save it to ``output``.

    Args:
        output: Destination ``.keras`` path (parent dirs created as needed).

    Returns:
        The path the model was written to.
    """
    model = build_ci_model()
    output.parent.mkdir(parents=True, exist_ok=True)
    model.save(output)  # type: ignore[attr-defined]
    logger.info("saved CI model", extra={"path": str(output)})
    return output


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate the tiny CI U-Net model.")
    parser.add_argument(
        "--output",
        type=Path,
        default=_DEFAULT_OUTPUT,
        help="Destination .keras path.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    args = _parse_args()
    path = main(args.output)
    logger.info("CI model ready at %s", path)
