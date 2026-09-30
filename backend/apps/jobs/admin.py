"""Django admin registration for the jobs app."""

from __future__ import annotations

from django.contrib import admin

from .models import JobStage, ProcessingJob


class JobStageInline(admin.TabularInline):  # type: ignore[type-arg]
    """Inline read-only view of a job's stages."""

    model = JobStage
    extra = 0
    can_delete = False
    readonly_fields = ("name", "sequence", "status", "duration_ms", "detail")
    ordering = ("sequence",)


@admin.register(ProcessingJob)
class ProcessingJobAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """Read-mostly admin for processing jobs."""

    list_display = ("id", "analysis_id", "status", "cancel_requested", "created_at")
    list_filter = ("status", "cancel_requested")
    search_fields = ("id", "analysis__id", "celery_task_id")
    readonly_fields = ("provenance", "worker_info", "error")
    inlines = [JobStageInline]
