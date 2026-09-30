"""Real-inference test using the tiny CI U-Net model (DEC-05).

Loads (or generates) the tiny CI model and runs the actual
:class:`ml.inference.predictor.UNetPredictor` and
:class:`ml.inference.pipeline.InferencePipeline` on synthetic imagery.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from rasterio.transform import from_origin  # type: ignore[import-untyped]

from ml.inference.pipeline import InferencePipeline
from ml.inference.predictor import UNetPredictor, load_keras_model
from ml.preprocessing.tiling import Tiler


def test_predict_prob_shape_and_range(ci_model_path: Path) -> None:
    """Real inference returns a (H, W) prob map with values in [0, 1]."""
    model = load_keras_model(ci_model_path)
    predictor = UNetPredictor(model, Tiler(tile=256, stride=128), batch_size=4)

    rng = np.random.default_rng(0)
    image = rng.uniform(0.0, 1.0, size=(300, 320, 3)).astype(np.float32)
    prob = predictor.predict_prob(image)

    assert prob.shape == (300, 320)
    assert prob.dtype == np.float32
    assert float(prob.min()) >= 0.0
    assert float(prob.max()) <= 1.0


def test_predict_prob_small_image_is_reflect_padded(ci_model_path: Path) -> None:
    """An image smaller than a tile is reflect-padded and still returns HxW."""
    model = load_keras_model(ci_model_path)
    predictor = UNetPredictor(model, Tiler(tile=256, stride=128))
    image = np.random.default_rng(1).uniform(0, 1, size=(64, 80, 3)).astype(np.float32)
    prob = predictor.predict_prob(image)
    assert prob.shape == (64, 80)


def test_pipeline_runs_end_to_end(ci_model_path: Path) -> None:
    """The full pipeline runs and returns a GeoDataFrame with the columns."""
    model = load_keras_model(ci_model_path)
    predictor = UNetPredictor(model, Tiler(tile=256, stride=128), batch_size=4)
    pipeline = InferencePipeline(predictor)

    rng = np.random.default_rng(2)
    image = rng.uniform(0.0, 1.0, size=(300, 300, 3)).astype(np.float32)
    transform = from_origin(500_000.0, 5_400_000.0, 0.5, 0.5)
    gdf = pipeline.run(image, transform=transform, crs="EPSG:32632")

    assert set(gdf.columns) == {
        "geometry",
        "area_m2",
        "centroid_lon",
        "centroid_lat",
        "confidence",
    }


def test_missing_model_raises_clear_error(tmp_path: Path) -> None:
    """Loading a non-existent model raises a clear FileNotFoundError."""
    missing = tmp_path / "does_not_exist.keras"
    with pytest.raises(FileNotFoundError):
        load_keras_model(missing)
