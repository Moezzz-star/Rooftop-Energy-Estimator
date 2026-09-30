"""End-to-end segmentation inference orchestration.

Chains the canonical stages: percentile normalize -> U-Net predict ->
morphological cleanup -> vectorize, returning a GeoDataFrame of building
polygons. Pure logic; no Django. Dependencies are injected in the constructor.
"""

from __future__ import annotations

import logging
from typing import Any

import geopandas as gpd  # type: ignore[import-untyped]
import numpy as np

from ml.configs import (
    DEFAULT_INFERENCE,
    DEFAULT_PREPROCESS,
    InferenceConfig,
    PreprocessConfig,
)
from ml.inference.postprocess import cleanup_mask
from ml.inference.predictor import UNetPredictor
from ml.inference.vectorize import mask_to_features
from ml.preprocessing.normalize import percentile_normalize

logger = logging.getLogger(__name__)


class InferencePipeline:
    """Compose preprocessing, prediction, cleanup, and vectorization."""

    def __init__(
        self,
        predictor: UNetPredictor,
        preprocess_config: PreprocessConfig | None = None,
        inference_config: InferenceConfig | None = None,
    ) -> None:
        """Initialize the pipeline.

        Args:
            predictor: Configured U-Net predictor.
            preprocess_config: Normalization config; defaults to DEC-01 values.
            inference_config: Threshold/morphology/vectorize config; defaults to
                the canonical values.
        """
        self.predictor = predictor
        self.preprocess_config = preprocess_config or DEFAULT_PREPROCESS
        self.inference_config = inference_config or DEFAULT_INFERENCE

    def run(
        self,
        image: np.ndarray,
        transform: Any,
        crs: Any,
    ) -> gpd.GeoDataFrame:
        """Run the full inference pipeline on a single image.

        Args:
            image: Raw image array shaped ``(H, W, C)`` or ``(C, H, W)`` with at
                least the bands referenced by the preprocessing config.
            transform: Affine transform mapping pixels to ``crs`` coordinates.
            crs: Source coordinate reference system (must not be ``None``).

        Returns:
            A GeoDataFrame of building polygons (see
            :func:`ml.inference.vectorize.mask_to_features`).
        """
        pcfg = self.preprocess_config
        icfg = self.inference_config

        normalized = percentile_normalize(
            image, pmin=pcfg.pmin, pmax=pcfg.pmax, bands=pcfg.bands, eps=pcfg.eps
        )
        logger.info(
            "normalized imagery",
            extra={"height": normalized.shape[0], "width": normalized.shape[1]},
        )

        prob = self.predictor.predict_prob(normalized)
        logger.info("ran inference", extra={"prob_max": float(prob.max())})

        mask = cleanup_mask(
            prob,
            threshold=icfg.threshold,
            min_object=icfg.min_object,
            min_hole=icfg.min_hole,
        )

        features = mask_to_features(
            mask,
            transform=transform,
            crs=crs,
            simplify_tol_m=icfg.simplify_tol_m,
            min_area_m2=icfg.min_area_m2,
            prob=prob,
        )
        logger.info("vectorized features", extra={"count": len(features)})
        return features


__all__ = ["InferencePipeline"]
