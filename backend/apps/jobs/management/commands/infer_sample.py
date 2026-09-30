"""``python manage.py infer_sample`` — end-to-end offline sample run.

Ensures seed data exists, creates (or reuses) a demo analysis over the bundled
sample area with the bundled sample imagery, and runs the full pipeline. To work
WITHOUT a running Celery worker, the pipeline is executed synchronously in-
process when the job is still queued (i.e. not already run eagerly). Prints the
resulting building count and total annual kWh. Used by ``make infer-sample``.

The segmentation model defaults to the tiny CI model when the real 90MB artifact
is absent (DEC-05), so this command runs fully offline.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db.models import Sum

_ANALYSIS_NAME = "Sample rooftop analysis"


class Command(BaseCommand):
    """Run the deterministic offline sample pipeline end-to-end."""

    help = "Seed, create/reuse a sample analysis, run the pipeline, print results."

    def handle(self, *args: Any, **options: Any) -> None:
        """Execute the sample analysis pipeline synchronously."""
        # Run the Celery task in-process (no broker/worker needed) so the sample
        # pipeline works fully offline via `make infer-sample`.
        from celery import current_app

        current_app.conf.task_always_eager = True
        current_app.conf.task_eager_propagates = True

        call_command("seed")
        analysis = self._get_or_create_analysis()
        self._run_pipeline(analysis)
        self._report(analysis)

    def _get_or_create_analysis(self) -> Any:
        """Create (or reuse) the demo sample analysis with imagery."""
        from apps.analyses.services import AnalysisService
        from apps.imagery.services import ImageryService

        project = self._demo_project()
        existing = project.analyses.filter(name=_ANALYSIS_NAME).first()
        if existing is not None:
            self.stdout.write(f"reusing analysis {existing.pk} ({existing.status})")
            return existing

        area = self._sample_area_geometry()
        analysis = AnalysisService().create(project=project, name=_ANALYSIS_NAME, area=area)
        ImageryService().register_bundled_sample(analysis)
        self.stdout.write(f"created analysis {analysis.pk}")
        return analysis

    def _run_pipeline(self, analysis: Any) -> None:
        """Submit and, if not already processed, run the pipeline inline."""
        from apps.analyses.models import AnalysisStatus
        from apps.jobs.models import JobStatus
        from apps.jobs.services import JobOrchestrator, PipelineRunner

        if analysis.status == AnalysisStatus.COMPLETED:
            self.stdout.write("analysis already completed; skipping run")
            return

        # Reuse an existing job (e.g. a prior interrupted run) rather than
        # re-submitting; otherwise submit fresh (eager mode runs it in-process).
        job = self._existing_job(analysis)
        if job is None:
            service = self._analysis_service()
            _analysis, job = service.submit(analysis, idempotency_key=uuid.uuid4().hex)
        if job is None:  # pragma: no cover - jobs app is present here
            self.stderr.write("submit did not create a job")
            return

        job.refresh_from_db()
        if job.status == JobStatus.QUEUED:
            # No worker in a plain `manage.py` invocation: run synchronously.
            self.stdout.write("running pipeline synchronously (no worker)")
            orchestrator = JobOrchestrator()
            orchestrator.mark_running(job)
            PipelineRunner(orchestrator=orchestrator).run(job)
        else:
            self.stdout.write(f"pipeline already executed (job status={job.status})")

    @staticmethod
    def _existing_job(analysis: Any) -> Any:
        """Return the analysis's job if one already exists, else ``None``."""
        from apps.jobs.models import ProcessingJob

        return ProcessingJob.objects.filter(analysis=analysis).first()

    def _report(self, analysis: Any) -> None:
        """Print the building count and total annual energy."""
        from apps.geospatial.models import Building
        from apps.solar.models import SolarEstimate

        analysis.refresh_from_db()
        building_count = Building.objects.filter(analysis=analysis).count()
        total = (
            SolarEstimate.objects.filter(building__analysis=analysis).aggregate(
                total=Sum("annual_kwh")
            )["total"]
            or 0.0
        )
        self.stdout.write(f"analysis status: {analysis.status}")
        self.stdout.write(f"buildings:       {building_count}")
        self.stdout.write(f"total annual kWh: {float(total):.1f}")

    @staticmethod
    def _analysis_service() -> Any:
        """Return an :class:`AnalysisService` instance."""
        from apps.analyses.services import AnalysisService

        return AnalysisService()

    @staticmethod
    def _demo_project() -> Any:
        """Resolve the demo project created by ``seed``."""
        from django.apps import apps as django_apps

        project_model = django_apps.get_model("projects", "Project")
        return project_model.objects.filter(name="Demo Project").order_by("created_at").first()

    @staticmethod
    def _sample_area_geometry() -> Any:
        """Load the bundled sample area GeoJSON as a GEOS geometry."""
        from django.contrib.gis.geos import GEOSGeometry

        configured = getattr(settings, "SAMPLE_AREA_PATH", "")
        path = (
            Path(configured)
            if configured
            else Path(settings.BASE_DIR).parent / "sample-data" / "sample_area.geojson"
        )
        payload = json.loads(path.read_text())
        feature = payload["features"][0] if payload.get("type") == "FeatureCollection" else payload
        geometry = feature.get("geometry", feature)
        geom = GEOSGeometry(json.dumps(geometry))
        if geom.srid is None:
            geom.srid = 4326
        return geom
