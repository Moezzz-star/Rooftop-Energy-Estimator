"""Domain service for the ML model registry.

:class:`ModelRegistryService` is the single entry point for resolving the
active model version, fetching a version by id, and verifying artifact
integrity. It reads the model artifact path from ``settings.ML_MODEL_PATH``
and raises framework-agnostic domain errors (:mod:`common.errors`).
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict
from pathlib import Path

from django.conf import settings

from common.errors import InfrastructureError, NotFoundError
from common.logging import get_logger

from .models import MLModelVersion, ModelStatus

logger = get_logger("ml_models.registry")

_CHUNK = 1024 * 1024  # 1 MiB streaming chunk for hashing.

# Canonical model identity (DEC-05). The 90 MB artifact is not in git; this
# metadata lets tests and the pipeline reference an active model even when the
# file is absent. Checksum verification is a separate, explicit step.
_DEFAULT_NAME = "unet_buildings"
_DEFAULT_VERSION = "1.0.0"


class ModelRegistryService:
    """Resolve and verify registered model versions.

    Dependencies are injected via ``__init__`` for testability.
    """

    def __init__(self, model_path: str | None = None) -> None:
        """Initialize the service.

        Args:
            model_path: Filesystem path to the model artifact. Defaults to
                ``settings.ML_MODEL_PATH`` when omitted.
        """
        self._model_path = (
            model_path if model_path is not None else getattr(settings, "ML_MODEL_PATH", "")
        )

    def active(self) -> MLModelVersion:
        """Return the model version to use for new analyses.

        Selection order: the (single) ``production`` version, else the most
        recently created ``registered`` version.

        Returns:
            The active :class:`MLModelVersion`.

        Raises:
            NotFoundError: If no production or registered version exists.
        """
        production = (
            MLModelVersion.objects.filter(status=ModelStatus.PRODUCTION)
            .order_by("-created_at")
            .first()
        )
        if production is not None:
            return production

        registered = (
            MLModelVersion.objects.filter(status=ModelStatus.REGISTERED)
            .order_by("-created_at")
            .first()
        )
        if registered is not None:
            return registered

        logger.warning("No active model version available")
        raise NotFoundError("No active model version is registered.")

    def get(self, model_id: str) -> MLModelVersion:
        """Fetch a model version by primary key.

        Args:
            model_id: UUID primary key of the version.

        Returns:
            The matching :class:`MLModelVersion`.

        Raises:
            NotFoundError: If no version has that id.
        """
        try:
            return MLModelVersion.objects.get(pk=model_id)
        except MLModelVersion.DoesNotExist as exc:
            raise NotFoundError("Model version not found.") from exc

    def verify_checksum(self, model_version: MLModelVersion, path: str | None = None) -> str:
        """Verify the on-disk artifact matches the recorded SHA-256 checksum.

        Args:
            model_version: The version whose ``checksum`` is authoritative.
            path: Artifact path; defaults to the configured model path.

        Returns:
            The computed hex SHA-256 digest.

        Raises:
            InfrastructureError: If the file is missing/unreadable or the
                computed digest does not match ``model_version.checksum``.
        """
        artifact_path = path if path is not None else self._model_path
        if not artifact_path:
            raise InfrastructureError("Model artifact path is not configured.")

        digest = self._sha256(artifact_path)

        expected = model_version.checksum
        if not expected:
            raise InfrastructureError("No expected checksum recorded for this model version.")
        if digest != expected:
            logger.error(
                "Model checksum mismatch",
                extra={"expected": expected, "computed": digest},
            )
            raise InfrastructureError("Model artifact checksum mismatch.")

        logger.info("Model checksum verified", extra={"checksum": digest})
        return digest

    @staticmethod
    def _sha256(path: str) -> str:
        """Stream a file and return its hex SHA-256 digest."""
        hasher = hashlib.sha256()
        try:
            with Path(path).open("rb") as handle:
                for chunk in iter(lambda: handle.read(_CHUNK), b""):
                    hasher.update(chunk)
        except OSError as exc:
            raise InfrastructureError("Model artifact could not be read.") from exc
        return hasher.hexdigest()

    @classmethod
    def get_or_create_default(cls) -> MLModelVersion:
        """Register (idempotently) the canonical ``unet_buildings`` version.

        Captures the canonical model metadata so tests and the pipeline can
        reference an active model even when the 90 MB artifact is absent
        (DEC-05). The row is created in ``production`` status.

        Returns:
            The canonical :class:`MLModelVersion`.
        """
        from ml.configs import DEFAULT_PREPROCESS, DEFAULT_TILING

        model, created = MLModelVersion.objects.get_or_create(
            name=_DEFAULT_NAME,
            version=_DEFAULT_VERSION,
            defaults={
                "status": ModelStatus.PRODUCTION,
                "checksum": "",
                "training_dataset_version": "osm-buildings",
                "preprocess_config": asdict(DEFAULT_PREPROCESS),
                "input_resolution": DEFAULT_TILING.tile,
                "signature": {
                    "input_shape": [DEFAULT_TILING.tile, DEFAULT_TILING.tile, 3],
                    "input_dtype": "float32",
                    "input_range": [0.0, 1.0],
                    "output": "sigmoid",
                    "output_channels": 1,
                },
                "metrics": {},
            },
        )
        if created:
            logger.info(
                "Registered default model version",
                extra={"model_name": model.name, "model_version": model.version},
            )
        return model
