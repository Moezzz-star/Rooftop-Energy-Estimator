"""DRF serializers for the jobs app.

Serializers shape read responses only; orchestration logic lives in
:class:`apps.jobs.services.JobOrchestrator` (code-architecture §6). The stage
serializer exposes the machine ``name`` + ``sequence`` the frontend mirrors for
its progress UI.
"""

from __future__ import annotations

from rest_framework import serializers

from .models import JobStage, ProcessingJob


class JobStageSerializer(serializers.ModelSerializer[JobStage]):
    """Read representation of a single durable :class:`JobStage`."""

    class Meta:
        model = JobStage
        fields = [
            "name",
            "sequence",
            "status",
            "started_at",
            "finished_at",
            "duration_ms",
            "detail",
        ]
        read_only_fields = fields


class JobSerializer(serializers.ModelSerializer[ProcessingJob]):
    """Read representation of a :class:`ProcessingJob` with ordered stages."""

    stages = JobStageSerializer(many=True, read_only=True)
    analysis_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = ProcessingJob
        fields = [
            "id",
            "analysis_id",
            "status",
            "celery_task_id",
            "queued_at",
            "started_at",
            "finished_at",
            "error",
            "failure_code",
            "cleanup_status",
            "cancel_requested",
            "retry_count",
            "provenance",
            "stages",
        ]
        read_only_fields = fields
