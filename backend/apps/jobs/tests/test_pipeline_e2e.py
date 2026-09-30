"""End-to-end pipeline test (the critical integration test).

Runs the full offline CPU sample path with REAL inference (tiny CI model), REAL
pvlib solar estimation, and REAL vectorization. Relies on
``config.settings.test`` (``CELERY_TASK_ALWAYS_EAGER=True``) so submitting the
analysis runs the pipeline inline.

Requires the geo/raster/TF stack (rasterio, geopandas, shapely, scikit-image,
pvlib, tensorflow-cpu) and the bundled sample raster + tiny CI model.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from django.conf import settings

from apps.analyses.models import AnalysisStatus
from apps.geospatial.models import Building
from apps.jobs.models import JobStatus, StageStatus
from apps.ml_models.services import ModelRegistryService
from apps.solar.models import DISCLAIMER, SolarEstimate

pytestmark = pytest.mark.django_db

_CI_MODEL = Path(settings.BASE_DIR).parent / "ml" / "tests" / "fixtures" / "ci_unet.keras"


@pytest.fixture(autouse=True)
def _use_ci_model(settings: Any) -> None:
    """Point the pipeline at the tiny CI model for offline inference."""
    settings.ML_MODEL_PATH = str(_CI_MODEL)


def test_full_pipeline_completes_offline(analysis: Any) -> None:
    """Submitting the sample analysis runs the whole pipeline to success."""
    from apps.analyses.services import AnalysisService

    # An active model version is required by the DEC-09 submit snapshot.
    ModelRegistryService.get_or_create_default()

    _analysis, job = AnalysisService().submit(analysis, idempotency_key="e2e-key")
    assert job is not None

    job.refresh_from_db()
    analysis.refresh_from_db()

    # Job + analysis reached success.
    assert job.status == JobStatus.SUCCEEDED, job.error
    assert job.finished_at is not None
    assert analysis.status == AnalysisStatus.COMPLETED

    # All ten stages succeeded with recorded durations.
    stages = list(job.stages.all())
    assert len(stages) == 10
    assert all(s.status == StageStatus.SUCCEEDED for s in stages), [
        (s.name, s.status) for s in stages
    ]
    assert all(s.duration_ms is not None for s in stages)

    # Provenance captured which model was used + stage timings.
    assert job.provenance["model_source"] in {"configured", "ci_fallback"}
    assert "stage_timings_ms" in job.provenance

    # Buildings may be sparse with the tiny CI model; when present each carries a
    # complete solar estimate (12 monthly values + the DEC-02 disclaimer).
    buildings = list(Building.objects.filter(analysis=analysis))
    for building in buildings:
        estimate = SolarEstimate.objects.filter(building=building).first()
        assert estimate is not None
        assert len(estimate.monthly_kwh) == 12
        assert estimate.disclaimer == DISCLAIMER
