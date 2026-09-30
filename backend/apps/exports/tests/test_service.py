"""Unit tests for :class:`ExportService` (rendering + CSV injection safety)."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import pytest

from apps.exports.models import ExportStatus
from apps.exports.services import ExportService
from apps.solar.models import DISCLAIMER

pytestmark = pytest.mark.django_db


def test_safe_cell_escapes_formula_injection() -> None:
    """A cell beginning with a formula trigger is prefixed with a quote."""
    assert ExportService._safe_cell("=SUM(A1:A9)") == "'=SUM(A1:A9)"
    assert ExportService._safe_cell("+1+1") == "'+1+1"
    assert ExportService._safe_cell("@cmd") == "'@cmd"
    assert ExportService._safe_cell("-2") == "'-2"
    assert ExportService._safe_cell("safe") == "safe"
    assert ExportService._safe_cell(None) == ""


def test_build_geojson_produces_feature_collection(
    analysis: Any,
    building_factory: Callable[..., Any],
    solar_estimate_factory: Callable[..., Any],
) -> None:
    """GeoJSON export renders a FeatureCollection with disclaimer + attribution."""
    building = building_factory(analysis, index=0)
    solar_estimate_factory(building)

    artifact = ExportService().build_geojson(analysis)

    assert artifact.status == ExportStatus.READY
    assert artifact.bytes and artifact.bytes > 0
    stored = artifact.storage_key
    assert stored is not None
    from common.storage import get_storage

    payload = json.loads(get_storage().read_bytes(stored))
    assert payload["type"] == "FeatureCollection"
    assert len(payload["features"]) == 1
    # Collection-level DEC-02 disclaimer + DEC-04 OSM/ODbL attribution.
    assert payload["properties"]["disclaimer"] == DISCLAIMER
    assert payload["properties"]["attribution"] == "© OpenStreetMap contributors, ODbL"
    # Per-feature attributes + disclaimer.
    props = payload["features"][0]["properties"]
    assert props["disclaimer"] == DISCLAIMER
    for key in ("index", "area_m2", "usable_area_m2", "confidence", "capacity_kwp", "annual_kwh"):
        assert key in props
    assert props["capacity_kwp"] == 16.8
    assert props["usable_area_m2"] == 84.0


def test_build_csv_is_injection_safe_and_has_summary(
    analysis: Any,
    building_factory: Callable[..., Any],
    solar_estimate_factory: Callable[..., Any],
) -> None:
    """CSV export escapes malicious cells, has a zone summary + disclaimer."""
    building = building_factory(analysis, index=0)
    solar_estimate_factory(building)

    artifact = ExportService().build_csv(analysis)

    from common.storage import get_storage

    assert artifact.storage_key is not None
    text = get_storage().read_bytes(artifact.storage_key).decode("utf-8")
    assert "annual_kwh" in text
    assert DISCLAIMER in text
    # Zone-summary section with aggregate totals.
    assert "Zone summary" in text
    assert "Building count" in text
    assert "Total roof area (m2)" in text
    assert "Average specific yield (kWh/kWp)" in text
    # No rendered line may begin with a bare formula trigger.
    for line in text.splitlines():
        assert not line.startswith(("=", "+", "@"))


def test_safe_cell_escapes_leading_minus() -> None:
    """A leading ``-`` is quoted so negatives cannot start a formula."""
    assert ExportService._safe_cell("-1+1").startswith("'")


def test_build_pdf_produces_valid_report(
    analysis: Any,
    building_factory: Callable[..., Any],
    solar_estimate_factory: Callable[..., Any],
) -> None:
    """PDF export renders a real, non-trivial PDF and marks the artifact ready."""
    building = building_factory(analysis, index=0)
    solar_estimate_factory(building)

    artifact = ExportService().build_pdf(analysis)

    assert artifact.status == ExportStatus.READY
    from common.storage import get_storage

    assert artifact.storage_key is not None
    content = get_storage().read_bytes(artifact.storage_key)
    assert content.startswith(b"%PDF")
    assert content.rstrip().endswith(b"%%EOF")
    # A real templated report is substantially larger than a placeholder.
    assert len(content) > 1500
    assert artifact.checksum and artifact.bytes == len(content)
