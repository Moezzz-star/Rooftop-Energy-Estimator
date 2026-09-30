"""Domain services for the analysis lifecycle.

* :class:`AnalysisService` creates draft analyses, submits them (freezing the
  DEC-09 snapshot and enqueuing the processing pipeline), and builds the
  snapshot itself.
* :class:`AssumptionResolver` returns the effective assumptions the pipeline
  should use for a given analysis.

Cross-app dependencies that are built in later waves (``jobs``) or that would
introduce import cycles are imported lazily inside methods. Geometry is
received already parsed (by the serializer) as a GEOS geometry.
"""

from __future__ import annotations

import subprocess
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Polygon
from django.db import IntegrityError, transaction

from common.errors import ConflictError, ValidationError
from common.logging import get_logger

from .models import Analysis, AnalysisArea, AnalysisAssumption, AnalysisStatus
from .validation import validate_assumptions

logger = get_logger("analyses.service")

# Assumption fields resolved for the pipeline / used to build solar inputs.
_ASSUMPTION_FIELDS: tuple[str, ...] = (
    "source",
    "usable_roof_fraction",
    "power_density_w_m2",
    "system_losses",
    "module_eff",
    "tilt_deg",
    "azimuth_deg",
    "shading",
    "temp_air",
    "wind",
)


class AnalysisService:
    """Create and submit analyses; own the immutable snapshot (DEC-09)."""

    @transaction.atomic
    def create(
        self,
        project: Any,
        name: str,
        area: GEOSGeometry,
        assumptions: dict[str, Any] | None = None,
    ) -> Analysis:
        """Create a draft analysis with its area and assumptions.

        Args:
            project: Owning ``projects.Project`` instance.
            name: Analysis name.
            area: Parsed EPSG:4326 polygon/multipolygon geometry.
            assumptions: Optional overrides for DEC-01 defaults.

        Returns:
            The created draft :class:`Analysis`.

        Raises:
            ValidationError: If the geometry is not a (multi)polygon.
        """
        analysis = Analysis.objects.create(
            project=project,
            name=name,
            status=AnalysisStatus.DRAFT,
        )
        AnalysisArea.objects.create(
            analysis=analysis,
            label=name,
            area=self._as_multipolygon(area),
        )
        self._create_assumption(analysis, assumptions)
        logger.info(
            "Created draft analysis",
            extra={"analysis_id": str(analysis.pk)},
        )
        return analysis

    @transaction.atomic
    def update_draft(self, analysis: Analysis, data: dict[str, Any]) -> Analysis:
        """Apply a partial update to a draft analysis.

        Args:
            analysis: The analysis to edit.
            data: Validated fields (``name``, ``area``, ``assumptions``).

        Returns:
            The updated :class:`Analysis`.

        Raises:
            ConflictError: If the analysis is no longer a draft.
        """
        if not analysis.is_draft:
            raise ConflictError("Only draft analyses can be edited.")

        name = data.get("name")
        if name is not None:
            analysis.name = name
            analysis.save(update_fields=["name", "updated_at"])

        area = data.get("area")
        if area is not None:
            analysis.areas.all().delete()
            AnalysisArea.objects.create(
                analysis=analysis,
                label=analysis.name,
                area=self._as_multipolygon(area),
            )

        assumptions = data.get("assumptions")
        if assumptions:
            self._apply_assumptions(analysis, assumptions)

        logger.info("Updated draft analysis", extra={"analysis_id": str(analysis.pk)})
        return analysis

    def submit(self, analysis: Analysis, idempotency_key: str) -> tuple[Analysis, Any]:
        """Submit a draft analysis: freeze the snapshot and enqueue the pipeline.

        Idempotent: re-submitting an already-submitted analysis with the same
        key returns the existing job without creating a duplicate.

        Args:
            analysis: The analysis to submit.
            idempotency_key: Client-supplied idempotency key.

        Returns:
            Tuple of ``(analysis, job)``; ``job`` may be ``None`` if the jobs
            app is not yet available.

        Raises:
            ValidationError: If ``idempotency_key`` is empty.
            ConflictError: If the analysis is already submitted with a
                different key, or a duplicate key is detected.
        """
        if not idempotency_key:
            raise ValidationError("Idempotency-Key is required.")

        if analysis.status != AnalysisStatus.DRAFT:
            return self._handle_resubmit(analysis, idempotency_key)

        self.snapshot(analysis)
        analysis.idempotency_key = idempotency_key
        analysis.status = AnalysisStatus.QUEUED
        analysis.submitted_at = datetime.now(UTC)

        try:
            with transaction.atomic():
                analysis.save(
                    update_fields=[
                        "idempotency_key",
                        "status",
                        "submitted_at",
                        "model_version",
                        "calculation_version",
                        "snapshot",
                        "updated_at",
                    ]
                )
        except IntegrityError as exc:
            logger.warning(
                "Duplicate idempotency key on submit",
                extra={"analysis_id": str(analysis.pk)},
            )
            raise ConflictError("Duplicate idempotency key for this project.") from exc

        job = self._enqueue(analysis)
        logger.info(
            "Submitted analysis",
            extra={"analysis_id": str(analysis.pk)},
        )
        return analysis, job

    def snapshot(self, analysis: Analysis) -> dict[str, Any]:
        """Freeze the immutable snapshot for ``analysis`` (DEC-09).

        Resolves and pins the active ML model version and solar methodology
        version, and records reproducibility metadata: code commit, processing
        config, the pinned version identifiers, and a frozen copy of the
        assumption values so a reopened analysis reproduces identical numbers
        even if the ``AnalysisAssumption`` row were somehow altered later.

        Writes are merge-safe: existing snapshot keys (notably ``imagery``,
        which the jobs pipeline populates at runtime) are preserved rather than
        clobbered. Mutates ``analysis`` in place.

        Args:
            analysis: The analysis to snapshot.

        Returns:
            The snapshot JSON payload.
        """
        from apps.ml_models.services import ModelRegistryService
        from apps.solar.services import SolarMethodRegistry

        model_version = ModelRegistryService().active()
        calculation_version = SolarMethodRegistry().get_active()
        analysis.model_version = model_version
        analysis.calculation_version = calculation_version

        snapshot: dict[str, Any] = dict(analysis.snapshot or {})
        snapshot["code_commit"] = self._code_commit()
        snapshot["processing_config"] = self._processing_config()
        snapshot["assumptions"] = self._frozen_assumptions(analysis)
        snapshot["model_version"] = self._version_label(model_version)
        snapshot["calculation_version"] = self._version_label(calculation_version)
        # Preserve any imagery metadata already written by the pipeline; only
        # seed an empty placeholder when the key is absent.
        snapshot.setdefault("imagery", {})

        analysis.snapshot = snapshot
        return snapshot

    def _handle_resubmit(self, analysis: Analysis, idempotency_key: str) -> tuple[Analysis, Any]:
        """Return the existing job for an idempotent re-submit, else conflict."""
        if analysis.idempotency_key == idempotency_key:
            return analysis, self._existing_job(analysis)
        raise ConflictError("Analysis has already been submitted.")

    def _create_assumption(
        self, analysis: Analysis, assumptions: dict[str, Any] | None
    ) -> AnalysisAssumption:
        """Create the 1:1 assumption row using defaults + validated overrides."""
        overrides = assumptions or {}
        validate_assumptions(overrides)
        fields = {key: value for key, value in overrides.items() if key in _ASSUMPTION_FIELDS}
        return AnalysisAssumption.objects.create(analysis=analysis, **fields)

    @staticmethod
    def _apply_assumptions(analysis: Analysis, assumptions: dict[str, Any]) -> None:
        """Update the assumption row in place with validated overrides."""
        validate_assumptions(assumptions)
        assumption = analysis.assumption
        updated: list[str] = []
        for key, value in assumptions.items():
            if key in _ASSUMPTION_FIELDS:
                setattr(assumption, key, value)
                updated.append(key)
        if updated:
            assumption.save(update_fields=[*updated, "updated_at"])

    @staticmethod
    def _as_multipolygon(area: GEOSGeometry) -> MultiPolygon:
        """Normalize a polygon/multipolygon to a 4326 ``MultiPolygon``."""
        if isinstance(area, MultiPolygon):
            geom = area
        elif isinstance(area, Polygon):
            geom = MultiPolygon(area)
        else:
            raise ValidationError("Area must be a Polygon or MultiPolygon.")
        if geom.srid is None:
            geom.srid = 4326
        return geom

    @staticmethod
    def _enqueue(analysis: Analysis) -> Any:
        """Enqueue the processing pipeline via the jobs orchestrator.

        The jobs app is delivered in a later wave; the import is lazy and
        guarded so submit succeeds (job=None) until it is available.
        """
        try:
            from apps.jobs.services import JobOrchestrator
        except ImportError:
            # TODO(jobs): jobs app not yet available; pipeline enqueue skipped.
            logger.warning(
                "Jobs app unavailable; pipeline not enqueued",
                extra={"analysis_id": str(analysis.pk)},
            )
            return None
        return JobOrchestrator().submit(analysis)

    @staticmethod
    def _existing_job(analysis: Analysis) -> Any:
        """Return the analysis's existing job, if the jobs app is present."""
        return getattr(analysis, "job", None)

    @staticmethod
    def _frozen_assumptions(analysis: Analysis) -> dict[str, Any]:
        """Capture the current assumption values as a plain JSON mapping."""
        assumption = getattr(analysis, "assumption", None)
        if assumption is None:
            return {}
        return {field: getattr(assumption, field) for field in _ASSUMPTION_FIELDS}

    @staticmethod
    def _version_label(version: Any) -> str:
        """Return a stable ``name@version`` label for a pinned version row."""
        if version is None:
            return ""
        name = getattr(version, "name", "")
        number = getattr(version, "version", "")
        return f"{name}@{number}" if name or number else str(version)

    @staticmethod
    def _code_commit() -> str:
        """Best-effort current git commit SHA (``"unknown"`` on failure)."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
                check=True,
            )
        except (OSError, subprocess.SubprocessError):
            return "unknown"
        return result.stdout.strip() or "unknown"

    @staticmethod
    def _processing_config() -> dict[str, Any]:
        """Return the canonical processing configuration for the snapshot."""
        from ml.configs import (
            DEFAULT_INFERENCE,
            DEFAULT_PREPROCESS,
            DEFAULT_TILING,
        )

        return {
            "preprocess": asdict(DEFAULT_PREPROCESS),
            "tiling": asdict(DEFAULT_TILING),
            "inference": asdict(DEFAULT_INFERENCE),
        }


class AssumptionResolver:
    """Resolve the effective assumptions for a submitted analysis."""

    def resolve(self, analysis: Analysis) -> dict[str, Any]:
        """Return the effective assumptions dict for the pipeline.

        Args:
            analysis: The analysis whose assumptions to resolve.

        Returns:
            A mapping of assumption field names to their effective values.

        Raises:
            ValidationError: If the analysis has no assumption row.
        """
        assumption = getattr(analysis, "assumption", None)
        if assumption is None:
            raise ValidationError("Analysis has no assumptions.")
        return {field: getattr(assumption, field) for field in _ASSUMPTION_FIELDS}
