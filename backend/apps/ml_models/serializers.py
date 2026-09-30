"""DRF serializers for the ML model registry (read-only model cards)."""

from __future__ import annotations

from rest_framework import serializers

from .models import MLModelVersion


class MLModelVersionSerializer(serializers.ModelSerializer[MLModelVersion]):
    """Serialize a model version as a public, read-only model card.

    ``checksum`` and ``mlflow_run_id`` are internal provenance details and are
    intentionally excluded from the public representation.
    """

    class Meta:
        model = MLModelVersion
        fields = (
            "id",
            "name",
            "version",
            "training_dataset_version",
            "preprocess_config",
            "input_resolution",
            "signature",
            "metrics",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields
