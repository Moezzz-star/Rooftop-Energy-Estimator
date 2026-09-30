"""Service-level tests for :class:`AnalysisService` and :class:`AssumptionResolver`."""

from __future__ import annotations

from typing import Any

import pytest
from django.contrib.gis.geos import GEOSGeometry

from apps.analyses.models import Analysis, AnalysisStatus
from apps.analyses.services import AnalysisService, AssumptionResolver
from apps.audit.models import AuditEvent
from apps.ml_models.services import ModelRegistryService
from apps.solar.services import SolarMethodRegistry
from common.errors import ConflictError, ValidationError

pytestmark = pytest.mark.django_db

_POLYGON = GEOSGeometry(
    '{"type": "Polygon", "coordinates": '
    "[[[11.574, 48.137], [11.575, 48.137], [11.575, 48.138], "
    "[11.574, 48.138], [11.574, 48.137]]]}",
    srid=4326,
)


def test_create_makes_draft_with_defaults(project: Any) -> None:
    """Create yields a draft analysis, one area, and DEC-01 assumptions."""
    analysis = AnalysisService().create(project, "A", _POLYGON)
    assert analysis.status == AnalysisStatus.DRAFT
    assert analysis.areas.count() == 1
    assert analysis.assumption.usable_roof_fraction == 0.70
    assert analysis.assumption.power_density_w_m2 == 200.0


def test_create_applies_assumption_overrides(project: Any) -> None:
    """Provided assumption overrides replace the defaults."""
    analysis = AnalysisService().create(
        project, "A", _POLYGON, assumptions={"tilt_deg": 35.0, "source": "user"}
    )
    assert analysis.assumption.tilt_deg == 35.0
    assert analysis.assumption.source == "user"


def test_snapshot_freezes_versions(project: Any) -> None:
    """Snapshot pins the active model and solar-method versions."""
    ModelRegistryService.get_or_create_default()
    SolarMethodRegistry.get_or_create_default()
    analysis = AnalysisService().create(project, "A", _POLYGON)

    AnalysisService().snapshot(analysis)
    assert analysis.model_version is not None
    assert analysis.calculation_version is not None
    assert analysis.snapshot["processing_config"]["tiling"]["tile"] == 256


def test_submit_requires_key(project: Any) -> None:
    """Submitting without a key raises ValidationError."""
    ModelRegistryService.get_or_create_default()
    SolarMethodRegistry.get_or_create_default()
    analysis = AnalysisService().create(project, "A", _POLYGON)
    with pytest.raises(ValidationError):
        AnalysisService().submit(analysis, "")


def test_resubmit_different_key_conflicts(project: Any) -> None:
    """A second submit with a different key conflicts."""
    ModelRegistryService.get_or_create_default()
    SolarMethodRegistry.get_or_create_default()
    analysis = AnalysisService().create(project, "A", _POLYGON)
    AnalysisService().submit(analysis, "key-1")
    with pytest.raises(ConflictError):
        AnalysisService().submit(analysis, "key-2")


def test_assumption_resolver_returns_effective_values(project: Any) -> None:
    """The resolver returns all assumption fields for the pipeline."""
    analysis = AnalysisService().create(project, "A", _POLYGON)
    resolved = AssumptionResolver().resolve(analysis)
    assert resolved["usable_roof_fraction"] == 0.70
    assert set(resolved) >= {"tilt_deg", "azimuth_deg", "shading", "system_losses"}


def test_update_draft_blocked_after_submit(project: Any) -> None:
    """Editing a non-draft analysis raises ConflictError."""
    ModelRegistryService.get_or_create_default()
    SolarMethodRegistry.get_or_create_default()
    analysis = AnalysisService().create(project, "A", _POLYGON)
    AnalysisService().submit(analysis, "key-1")
    analysis = Analysis.objects.get(pk=analysis.pk)
    with pytest.raises(ConflictError):
        AnalysisService().update_draft(analysis, {"name": "B"})


# --- E1: bounded assumption validation --------------------------------------

_OUT_OF_RANGE: dict[str, Any] = {
    "usable_roof_fraction": 0.0,  # (0, 1]
    "power_density_w_m2": 0.0,  # > 0
    "system_losses": 1.0,  # [0, 1)
    "module_eff": 1.5,  # (0, 1]
    "tilt_deg": 91.0,  # [0, 90]
    "azimuth_deg": 361.0,  # [0, 360]
    "shading": 1.5,  # [0, 1]
    "temp_air": 200.0,  # bounded range
    "wind": -1.0,  # >= 0
}

_IN_RANGE: dict[str, Any] = {
    "usable_roof_fraction": 1.0,
    "power_density_w_m2": 250.0,
    "system_losses": 0.0,
    "module_eff": 0.22,
    "tilt_deg": 0.0,
    "azimuth_deg": 360.0,
    "shading": 0.5,
    "temp_air": 25.0,
    "wind": 0.0,
}


@pytest.mark.parametrize("field", sorted(_OUT_OF_RANGE))
def test_create_rejects_out_of_range_assumption(project: Any, field: str) -> None:
    """Each out-of-range assumption field is rejected on create."""
    with pytest.raises(ValidationError):
        AnalysisService().create(project, "A", _POLYGON, assumptions={field: _OUT_OF_RANGE[field]})


@pytest.mark.parametrize("field", sorted(_IN_RANGE))
def test_create_accepts_in_range_assumption(project: Any, field: str) -> None:
    """Each in-range boundary assumption value is accepted on create."""
    analysis = AnalysisService().create(
        project, "A", _POLYGON, assumptions={field: _IN_RANGE[field]}
    )
    assert getattr(analysis.assumption, field) == _IN_RANGE[field]


def test_create_rejects_non_numeric_assumption(project: Any) -> None:
    """A non-numeric assumption value is rejected."""
    with pytest.raises(ValidationError):
        AnalysisService().create(project, "A", _POLYGON, assumptions={"tilt_deg": "flat"})


def test_create_rejects_invalid_source(project: Any) -> None:
    """An unknown assumption source classification is rejected."""
    with pytest.raises(ValidationError):
        AnalysisService().create(project, "A", _POLYGON, assumptions={"source": "guessed"})


def test_update_draft_rejects_out_of_range(project: Any) -> None:
    """A draft update with an out-of-range override is rejected."""
    analysis = AnalysisService().create(project, "A", _POLYGON)
    with pytest.raises(ValidationError):
        AnalysisService().update_draft(analysis, {"assumptions": {"tilt_deg": 120.0}})


# --- E2/E3: immutable snapshot + reopen determinism -------------------------


def test_snapshot_freezes_assumptions_and_versions(project: Any) -> None:
    """Snapshot captures frozen assumptions and pinned version labels."""
    ModelRegistryService.get_or_create_default()
    SolarMethodRegistry.get_or_create_default()
    analysis = AnalysisService().create(project, "A", _POLYGON, assumptions={"tilt_deg": 33.0})

    AnalysisService().snapshot(analysis)

    frozen = analysis.snapshot["assumptions"]
    assert frozen["tilt_deg"] == 33.0
    assert frozen["usable_roof_fraction"] == 0.70
    assert analysis.snapshot["model_version"]
    assert analysis.snapshot["calculation_version"]


def test_snapshot_is_stable_after_submit(project: Any) -> None:
    """The frozen snapshot equals what was captured and stays stable (reopen)."""
    ModelRegistryService.get_or_create_default()
    SolarMethodRegistry.get_or_create_default()
    analysis = AnalysisService().create(project, "A", _POLYGON, assumptions={"tilt_deg": 33.0})
    AnalysisService().submit(analysis, "key-1")

    frozen = Analysis.objects.get(pk=analysis.pk).snapshot
    # Reopen: reloading the persisted analysis reproduces the identical snapshot.
    reopened = Analysis.objects.get(pk=analysis.pk).snapshot
    assert reopened == frozen
    assert frozen["assumptions"]["tilt_deg"] == 33.0
    assert "code_commit" in frozen


def test_snapshot_preserves_existing_imagery_key(project: Any) -> None:
    """Re-snapshotting does not clobber imagery metadata added by the pipeline."""
    ModelRegistryService.get_or_create_default()
    SolarMethodRegistry.get_or_create_default()
    analysis = AnalysisService().create(project, "A", _POLYGON)
    analysis.snapshot = {"imagery": {"checksum": "abc123"}}

    AnalysisService().snapshot(analysis)

    assert analysis.snapshot["imagery"] == {"checksum": "abc123"}


# --- E4: delete cascade + surviving audit event -----------------------------


def test_deleting_project_records_surviving_audit_event(project: Any) -> None:
    """Deleting a project cascades to analyses and records a surviving event."""
    analysis = AnalysisService().create(project, "A", _POLYGON)
    analysis_id = analysis.pk

    project.delete()

    assert not Analysis.objects.filter(pk=analysis_id).exists()
    events = AuditEvent.objects.filter(action="analysis.deleted", target_id=str(analysis_id))
    assert events.count() == 1
    event = events.get()
    assert event.metadata["project_id"] == str(project.pk)


def test_deleting_analysis_records_audit_event(project: Any) -> None:
    """Directly deleting an analysis records a surviving audit event."""
    analysis = AnalysisService().create(project, "A", _POLYGON)
    analysis_id = analysis.pk

    analysis.delete()

    assert AuditEvent.objects.filter(
        action="analysis.deleted", target_id=str(analysis_id)
    ).exists()
