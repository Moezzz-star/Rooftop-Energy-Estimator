"""Segmentation and solar inference logic (pure, framework-free)."""

from ml.inference.pipeline import InferencePipeline
from ml.inference.postprocess import cleanup_mask
from ml.inference.predictor import (
    ModelNotFoundError,
    UNetPredictor,
    load_keras_model,
)
from ml.inference.solar import SolarInputs, SolarModel, SolarResult
from ml.inference.vectorize import mask_to_features

__all__ = [
    "InferencePipeline",
    "cleanup_mask",
    "UNetPredictor",
    "load_keras_model",
    "ModelNotFoundError",
    "SolarInputs",
    "SolarModel",
    "SolarResult",
    "mask_to_features",
]
