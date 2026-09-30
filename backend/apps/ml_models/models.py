"""Persistence models for the ML model registry.

A :class:`MLModelVersion` records the immutable metadata of a trained
segmentation model: its identity (``name``/``version``), integrity
(``checksum``), reproducibility inputs (``training_dataset_version``,
``preprocess_config``, ``input_resolution``, ``signature``), quality
(``metrics``) and lifecycle (``status``). Rows are referenced with
``PROTECT`` by immutable Analysis snapshots (DEC-09) and are therefore never
hard-deleted.
"""

from __future__ import annotations

from django.db import models

from common.models import BaseModel


class ModelStatus(models.TextChoices):
    """Lifecycle states of a registered model version (§3, §14)."""

    CANDIDATE = "candidate", "Candidate"
    REGISTERED = "registered", "Registered"
    PRODUCTION = "production", "Production"
    ROLLED_BACK = "rolled_back", "Rolled back"


class MLModelVersion(BaseModel):
    """Immutable metadata for a single trained model version.

    Attributes:
        name: Model family name (e.g. ``"unet_buildings"``).
        version: Semantic version string within the family (e.g. ``"1.0.0"``).
        checksum: Hex SHA-256 of the serialized model artifact (may be empty
            until the artifact is downloaded; see DEC-05).
        training_dataset_version: Identifier of the training label set
            (OpenStreetMap ODbL labels, DEC-04).
        preprocess_config: Canonical preprocessing parameters (DEC-01/§1).
        input_resolution: Model input tile edge length in pixels (256).
        signature: Input/output tensor contract of the model.
        metrics: Evaluation metrics recorded at registration time.
        status: Lifecycle state (candidate/registered/production/rolled_back).
        mlflow_run_id: Optional MLflow run identifier for provenance.
    """

    name = models.CharField(max_length=128)
    version = models.CharField(max_length=64)
    checksum = models.CharField(max_length=64, blank=True)
    training_dataset_version = models.CharField(max_length=128, blank=True)
    preprocess_config = models.JSONField(default=dict)
    input_resolution = models.PositiveIntegerField(default=256)
    signature = models.JSONField(default=dict)
    metrics = models.JSONField(default=dict)
    status = models.CharField(
        max_length=16,
        choices=ModelStatus.choices,
        default=ModelStatus.CANDIDATE,
    )
    mlflow_run_id = models.CharField(max_length=128, null=True, blank=True)

    class Meta:
        verbose_name = "ML model version"
        verbose_name_plural = "ML model versions"
        constraints = [
            models.UniqueConstraint(
                fields=["name", "version"],
                name="uq_mlmodelversion_name_version",
            ),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        """Return a human-readable identifier."""
        return f"{self.name}@{self.version} ({self.status})"
