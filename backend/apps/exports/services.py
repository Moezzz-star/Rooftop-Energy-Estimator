"""Domain service for building export artifacts (code-architecture §1).

:class:`ExportService` renders an analysis's results into a GeoJSON, CSV, or PDF
artifact, persists the bytes via :class:`common.storage.ObjectStorage`, and
records integrity metadata (checksum, size) + status on the
:class:`~apps.exports.models.ExportArtifact`.

Security: CSV cells are escaped against spreadsheet formula injection (MUST-ADD)
— any cell beginning with ``= + - @`` or a control character is prefixed with a
single quote. Every export carries the DEC-02 indicative-only disclaimer.

Cross-app models/services are imported lazily inside methods to avoid import
cycles.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
from typing import Any

from common.errors import ValidationError
from common.logging import get_logger
from common.storage import ObjectStorage, get_storage

from .models import ExportArtifact, ExportKind, ExportStatus

logger = get_logger("exports.service")

# Leading characters that make a spreadsheet interpret a cell as a formula.
_CSV_INJECTION_PREFIXES = ("=", "+", "-", "@", "\t", "\r")

# DEC-04 — attribution for OpenStreetMap-derived model outputs (ODbL 1.0).
OSM_ATTRIBUTION = "© OpenStreetMap contributors, ODbL"

_KEY_TEMPLATE = "analyses/{analysis_id}/exports/{artifact_id}.{ext}"
_EXTENSIONS = {ExportKind.GEOJSON: "geojson", ExportKind.CSV: "csv", ExportKind.PDF: "pdf"}

# Principal limitations surfaced in the PDF report (§16, §29 limitations).
_LIMITATIONS = (
    "Estimates depend on imagery resolution and acquisition date.",
    "Roof segmentation carries model uncertainty; small or occluded roofs may be missed.",
    "Roof tilt and azimuth are assumed defaults unless measured; shading is approximate.",
    "Irradiance uses a clear-sky model without site-specific weather data.",
    "No building-height, LiDAR, or 3D obstruction data is used.",
)


class ExportService:
    """Render analysis results into downloadable artifacts.

    Args:
        storage: Object storage backend (defaults to the configured backend).
    """

    def __init__(self, storage: ObjectStorage | None = None) -> None:
        self._storage = storage or get_storage()

    def build(self, artifact: ExportArtifact) -> ExportArtifact:
        """Build ``artifact`` from its analysis and persist the bytes.

        Args:
            artifact: A pending :class:`ExportArtifact` to populate.

        Returns:
            The updated artifact (``ready`` on success, ``failed`` on error).

        Raises:
            ValidationError: If the artifact's kind is unsupported.
        """
        analysis = artifact.analysis
        try:
            content, ext = self._render(artifact.kind, analysis)
        except NotImplementedError:
            artifact.status = ExportStatus.FAILED
            artifact.save(update_fields=["status", "updated_at"])
            raise
        key = _KEY_TEMPLATE.format(analysis_id=analysis.pk, artifact_id=artifact.pk, ext=ext)
        self._storage.save(key, content)
        artifact.storage_key = key
        artifact.checksum = hashlib.sha256(content).hexdigest()
        artifact.bytes = len(content)
        artifact.status = ExportStatus.READY
        artifact.save(update_fields=["storage_key", "checksum", "bytes", "status", "updated_at"])
        logger.info(
            "Built export artifact",
            extra={"analysis_id": str(analysis.pk)},
        )
        return artifact

    def build_geojson(self, analysis: Any) -> ExportArtifact:
        """Create + build a GeoJSON export for ``analysis``."""
        return self.build(self._new_artifact(analysis, ExportKind.GEOJSON))

    def build_csv(self, analysis: Any) -> ExportArtifact:
        """Create + build an injection-safe CSV export for ``analysis``."""
        return self.build(self._new_artifact(analysis, ExportKind.CSV))

    def build_pdf(self, analysis: Any) -> ExportArtifact:
        """Create + build a summary PDF report for ``analysis``."""
        return self.build(self._new_artifact(analysis, ExportKind.PDF))

    # -- rendering ----------------------------------------------------------

    def _render(self, kind: str, analysis: Any) -> tuple[bytes, str]:
        """Dispatch to the per-kind renderer, returning ``(bytes, extension)``."""
        if kind == ExportKind.GEOJSON:
            return self._render_geojson(analysis), _EXTENSIONS[ExportKind.GEOJSON]
        if kind == ExportKind.CSV:
            return self._render_csv(analysis), _EXTENSIONS[ExportKind.CSV]
        if kind == ExportKind.PDF:
            return self._render_pdf(analysis), _EXTENSIONS[ExportKind.PDF]
        raise ValidationError("Unsupported export kind.", details={"kind": kind})

    def _render_geojson(self, analysis: Any) -> bytes:
        """Render a GeoJSON FeatureCollection of the analysis buildings.

        Each feature carries roof + solar attributes and the DEC-02 disclaimer;
        the collection carries the disclaimer and DEC-04 OSM/ODbL attribution.
        Geometry serialization reuses the geospatial projection service.
        """
        from apps.solar.models import DISCLAIMER

        buildings = list(self._buildings(analysis))
        by_id = {str(b.pk): b for b in buildings}
        collection = self._feature_collection(buildings)
        for feature in collection.get("features", []):
            building = by_id.get(str(feature.get("id")))
            if building is None:
                continue
            estimate = self._first_estimate(building)
            properties = feature.setdefault("properties", {})
            properties.update(self._geojson_properties(building, estimate))
            properties["disclaimer"] = DISCLAIMER
        collection["properties"] = {
            "disclaimer": DISCLAIMER,
            "attribution": OSM_ATTRIBUTION,
        }
        return json.dumps(collection).encode("utf-8")

    def _geojson_properties(self, building: Any, estimate: Any) -> dict[str, Any]:
        """Return the per-feature attribute mapping for ``building``."""
        return {
            "index": building.index,
            "area_m2": self._round(building.area_m2),
            "usable_area_m2": self._round(self._usable_area(building, estimate)),
            "confidence": self._round(building.confidence, 3),
            "capacity_kwp": self._round(getattr(estimate, "capacity_kwp", None)),
            "annual_kwh": self._round(getattr(estimate, "annual_kwh", None)),
            "specific_yield": self._round(getattr(estimate, "specific_yield", None)),
        }

    def _render_csv(self, analysis: Any) -> bytes:
        """Render an injection-safe CSV of building rows + a zone summary.

        Sections: per-building rows, a blank separator, an aggregate
        zone-summary block (totals + averages), then the DEC-02 disclaimer.
        Every cell is escaped against spreadsheet formula injection.
        """
        from apps.solar.models import DISCLAIMER

        buildings = list(self._buildings(analysis))
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        header = [
            "building_index",
            "area_m2",
            "confidence",
            "capacity_kwp",
            "annual_kwh",
            "specific_yield",
            "usable_area_m2",
        ]
        writer.writerow([self._safe_cell(col) for col in header])
        for building in buildings:
            estimate = self._first_estimate(building)
            writer.writerow(self._csv_row(building, estimate))

        writer.writerow([])
        writer.writerow([self._safe_cell("Zone summary")])
        for label, value in self._summary(buildings).items():
            writer.writerow([self._safe_cell(label), self._safe_cell(value)])

        writer.writerow([])
        writer.writerow([self._safe_cell(DISCLAIMER)])
        return buffer.getvalue().encode("utf-8")

    def _render_pdf(self, analysis: Any) -> bytes:
        """Render the §20 summary report as a real PDF using ReportLab.

        ReportLab is pure-Python and needs no system libraries or network
        access, so the report builds entirely offline. No external tile server
        is contacted; building footprints are drawn as a simple vector figure
        (omitted gracefully when no buildings exist).
        """
        return _PdfReport(self).render(analysis)

    # -- data aggregation ---------------------------------------------------

    def _summary(self, buildings: list[Any]) -> dict[str, Any]:
        """Return the aggregate zone-summary metrics for ``buildings``."""
        total_roof = 0.0
        total_usable = 0.0
        total_capacity = 0.0
        total_annual = 0.0
        yields: list[float] = []
        for building in buildings:
            estimate = self._first_estimate(building)
            total_roof += float(building.area_m2 or 0.0)
            total_usable += float(self._usable_area(building, estimate) or 0.0)
            total_capacity += float(getattr(estimate, "capacity_kwp", 0.0) or 0.0)
            total_annual += float(getattr(estimate, "annual_kwh", 0.0) or 0.0)
            specific = getattr(estimate, "specific_yield", None)
            if specific is not None:
                yields.append(float(specific))
        avg_yield = sum(yields) / len(yields) if yields else 0.0
        return {
            "Building count": len(buildings),
            "Total roof area (m2)": self._round(total_roof),
            "Total usable area (m2)": self._round(total_usable),
            "Total capacity (kWp)": self._round(total_capacity),
            "Total annual energy (kWh)": self._round(total_annual),
            "Average specific yield (kWh/kWp)": self._round(avg_yield),
        }

    def _monthly_totals(self, buildings: list[Any]) -> list[float]:
        """Return the 12 monthly energy totals (kWh) summed over buildings."""
        totals = [0.0] * 12
        for building in buildings:
            estimate = self._first_estimate(building)
            monthly = getattr(estimate, "monthly_kwh", None) or []
            for month, value in enumerate(monthly[:12]):
                try:
                    totals[month] += float(value)
                except (TypeError, ValueError):
                    continue
        return totals

    # -- helpers ------------------------------------------------------------

    def _csv_row(self, building: Any, estimate: Any) -> list[str]:
        """Build one sanitized CSV row for a building + optional estimate."""
        values: list[Any] = [
            building.index,
            building.area_m2,
            building.confidence,
            getattr(estimate, "capacity_kwp", None),
            getattr(estimate, "annual_kwh", None),
            getattr(estimate, "specific_yield", None),
            getattr(estimate, "usable_area_m2", None),
        ]
        return [self._safe_cell(value) for value in values]

    @staticmethod
    def _feature_collection(buildings: list[Any]) -> dict[str, Any]:
        """Serialize buildings into a FeatureCollection (reusing geospatial)."""
        from apps.geospatial.services import BuildingProjectionService

        projector = BuildingProjectionService(max_features=10**9)
        return projector.to_feature_collection(buildings)

    @staticmethod
    def _buildings(analysis: Any) -> Any:
        """Return the analysis's buildings queryset (ordered)."""
        from apps.geospatial.models import Building

        return Building.objects.filter(analysis=analysis).order_by("index")

    @staticmethod
    def _first_estimate(building: Any) -> Any:
        """Return the building's first solar estimate, if any."""
        from apps.solar.models import SolarEstimate

        return SolarEstimate.objects.filter(building=building).first()

    @staticmethod
    def _usable_area(building: Any, estimate: Any) -> float | None:
        """Return the usable roof area (m^2) from the estimate or roof geometry."""
        usable = getattr(estimate, "usable_area_m2", None)
        if usable is not None:
            return float(usable)
        roof = getattr(building, "roof", None)
        roof_usable = getattr(roof, "usable_area_m2", None)
        return None if roof_usable is None else float(roof_usable)

    @staticmethod
    def _round(value: Any, ndigits: int = 2) -> float | None:
        """Round ``value`` to ``ndigits`` for display; ``None`` passes through."""
        if value is None:
            return None
        try:
            return round(float(value), ndigits)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _new_artifact(analysis: Any, kind: str) -> ExportArtifact:
        """Create a fresh pending artifact for ``analysis`` and ``kind``."""
        return ExportArtifact.objects.create(analysis=analysis, kind=kind)

    @staticmethod
    def _safe_cell(value: Any) -> str:
        """Return a CSV-injection-safe string for ``value`` (MUST-ADD).

        Cells beginning with a formula trigger (``= + - @``) or a control
        character are prefixed with a single quote so spreadsheet software treats
        them as text rather than executable formulas.
        """
        if value is None:
            return ""
        text = str(value)
        if text and text[0] in _CSV_INJECTION_PREFIXES:
            return "'" + text
        return text


_MONTH_LABELS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


class _PdfReport:
    """Build the §20 summary PDF report for an analysis using ReportLab.

    ReportLab is pure-Python (no system libraries, no network), so the report
    renders fully offline. No external tile server is contacted; building
    footprints are drawn as a self-contained vector figure. Data is read from
    other apps read-only via the injected :class:`ExportService` helpers.
    """

    def __init__(self, service: ExportService) -> None:
        self._svc = service

    def render(self, analysis: Any) -> bytes:
        """Return the PDF report bytes for ``analysis``."""
        from reportlab.lib.pagesizes import A4  # type: ignore[import-untyped]
        from reportlab.lib.units import cm  # type: ignore[import-untyped]
        from reportlab.platypus import (  # type: ignore[import-untyped]
            SimpleDocTemplate,
            Spacer,
        )

        from apps.solar.models import DISCLAIMER

        buildings = list(self._svc._buildings(analysis))
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
            title="Rooftop Energy Estimate",
        )
        story: list[Any] = []
        story += self._header(analysis)
        story.append(Spacer(1, 12))
        story += self._section("Analysis metadata", self._metadata_table(analysis, buildings))
        story.append(Spacer(1, 10))
        story += self._section("Imagery", self._imagery_table(analysis))
        story.append(Spacer(1, 10))
        story += self._section("Assumptions", self._assumptions_table(analysis))
        story.append(Spacer(1, 10))
        story += self._section("Results summary", self._summary_table(buildings))
        story.append(Spacer(1, 10))
        story += self._section("Monthly energy (kWh)", self._monthly_chart(buildings))
        story.append(Spacer(1, 10))
        story += self._section("Detected roof footprints", self._polygons_figure(buildings))
        story.append(Spacer(1, 10))
        story += self._limitations()
        story.append(Spacer(1, 10))
        story += self._disclaimer(DISCLAIMER)
        doc.build(story)
        return buffer.getvalue()

    # -- flowable builders --------------------------------------------------

    def _styles(self) -> Any:
        from reportlab.lib.styles import getSampleStyleSheet  # type: ignore[import-untyped]

        return getSampleStyleSheet()

    def _header(self, analysis: Any) -> list[Any]:
        from reportlab.platypus import Paragraph  # type: ignore[import-untyped]

        styles = self._styles()
        project_name = getattr(getattr(analysis, "project", None), "name", "-")
        subtitle = f"Project: {self._esc(project_name)}  |  Analysis: {self._esc(analysis.name)}"
        return [
            Paragraph("Rooftop Energy Estimate", styles["Title"]),
            Paragraph(subtitle, styles["Normal"]),
        ]

    @staticmethod
    def _esc(value: Any) -> str:
        """Escape XML-significant characters for safe use in a Paragraph."""
        from xml.sax.saxutils import escape

        return escape(str(value))

    def _section(self, title: str, body: Any) -> list[Any]:
        from reportlab.platypus import Paragraph  # type: ignore[import-untyped]

        styles = self._styles()
        return [Paragraph(title, styles["Heading2"]), body]

    def _table(self, rows: list[list[str]]) -> Any:
        from reportlab.lib import colors  # type: ignore[import-untyped]
        from reportlab.platypus import Table, TableStyle  # type: ignore[import-untyped]

        table = Table(rows, hAlign="LEFT", colWidths=[6 * self._cm(), 9 * self._cm()])
        table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c8d0d8")),
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef2f5")),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        return table

    def _cm(self) -> float:
        from reportlab.lib.units import cm  # type: ignore[import-untyped]

        return float(cm)

    def _metadata_table(self, analysis: Any, buildings: list[Any]) -> Any:
        from django.utils import timezone

        centroid = self._centroid(analysis, buildings)
        location = "—" if centroid is None else f"lat {centroid[1]:.5f}, lon {centroid[0]:.5f}"
        model_version = self._version_label(getattr(analysis, "model_version", None))
        method = getattr(analysis, "calculation_version", None)
        method_version = self._version_label(method)
        methodology = (
            getattr(method, "description", "") or "pvlib clear-sky (Ineichen) hourly model"
        )
        rows = [
            ["Field", "Value"],
            ["Date generated", timezone.now().strftime("%Y-%m-%d %H:%M %Z")],
            ["Status", str(analysis.status)],
            ["Location (centroid)", location],
            ["Model version", model_version],
            ["Calculation version", method_version],
            ["Methodology", methodology],
        ]
        return self._table(rows)

    def _imagery_table(self, analysis: Any) -> Any:
        asset = self._imagery_asset(analysis)
        if asset is None:
            return self._table([["Field", "Value"], ["Imagery", "No imagery asset recorded"]])
        bounds = asset.bounds or {}
        bounds_text = ", ".join(f"{k}={v}" for k, v in bounds.items()) if bounds else "—"
        resolution = "—" if asset.resolution_m is None else f"{asset.resolution_m:.3f} m/px"
        acquired = "—" if asset.acquired_at is None else asset.acquired_at.strftime("%Y-%m-%d")
        rows = [
            ["Field", "Value"],
            ["Source / provider", str(asset.provider)],
            ["CRS", str(asset.crs)],
            ["Resolution", resolution],
            ["Bands", str(asset.bands)],
            ["Bounds", bounds_text],
            ["Acquired", acquired],
            ["Attribution", OSM_ATTRIBUTION],
        ]
        return self._table(rows)

    def _assumptions_table(self, analysis: Any) -> Any:
        assumption = self._assumption(analysis)
        if assumption is None:
            return self._table([["Field", "Value"], ["Assumptions", "Defaults (not yet frozen)"]])
        rows = [
            ["Field", "Value"],
            ["Source", str(assumption.source)],
            ["Usable roof fraction", f"{assumption.usable_roof_fraction:.2f}"],
            ["PV power density (W/m2)", f"{assumption.power_density_w_m2:.0f}"],
            ["System losses", f"{assumption.system_losses:.2f}"],
            ["Module efficiency", f"{assumption.module_eff:.2f}"],
            ["Tilt (deg)", f"{assumption.tilt_deg:.0f}"],
            ["Azimuth (deg)", f"{assumption.azimuth_deg:.0f}"],
            ["Shading factor", f"{assumption.shading:.2f}"],
        ]
        return self._table(rows)

    def _summary_table(self, buildings: list[Any]) -> Any:
        summary = self._svc._summary(buildings)
        rows = [["Metric", "Value"]]
        rows += [[label, str(value)] for label, value in summary.items()]
        return self._table(rows)

    def _monthly_chart(self, buildings: list[Any]) -> Any:
        from reportlab.graphics.charts.barcharts import (  # type: ignore[import-untyped]
            VerticalBarChart,
        )
        from reportlab.graphics.shapes import Drawing  # type: ignore[import-untyped]
        from reportlab.lib import colors  # type: ignore[import-untyped]

        monthly = [round(v, 1) for v in self._svc._monthly_totals(buildings)]
        drawing = Drawing(400, 200)
        chart = VerticalBarChart()
        chart.x = 30
        chart.y = 25
        chart.width = 350
        chart.height = 150
        chart.data = [monthly]
        chart.categoryAxis.categoryNames = list(_MONTH_LABELS)
        chart.valueAxis.valueMin = 0
        chart.bars[0].fillColor = colors.HexColor("#f2a900")
        drawing.add(chart)
        return drawing

    def _polygons_figure(self, buildings: list[Any]) -> Any:
        from reportlab.graphics.shapes import (  # type: ignore[import-untyped]
            Drawing,
            Polygon,
        )
        from reportlab.lib import colors  # type: ignore[import-untyped]
        from reportlab.platypus import Paragraph  # type: ignore[import-untyped]

        rings = self._exterior_rings(buildings)
        if not rings:
            return Paragraph("No roof footprints detected.", self._styles()["Normal"])

        width, height, pad = 360.0, 240.0, 10.0
        xs = [x for ring in rings for x, _ in ring]
        ys = [y for ring in rings for _, y in ring]
        min_x, max_x, min_y, max_y = min(xs), max(xs), min(ys), max(ys)
        span_x = (max_x - min_x) or 1e-9
        span_y = (max_y - min_y) or 1e-9
        scale = min((width - 2 * pad) / span_x, (height - 2 * pad) / span_y)

        drawing = Drawing(width, height)
        for ring in rings:
            points: list[float] = []
            for x, y in ring:
                points.append(pad + (x - min_x) * scale)
                points.append(pad + (y - min_y) * scale)
            drawing.add(
                Polygon(
                    points,
                    strokeColor=colors.HexColor("#1f6f54"),
                    strokeWidth=0.7,
                    fillColor=colors.HexColor("#8fd3b6"),
                )
            )
        return drawing

    def _limitations(self) -> list[Any]:
        from reportlab.platypus import (  # type: ignore[import-untyped]
            ListFlowable,
            ListItem,
            Paragraph,
        )

        styles = self._styles()
        items = [ListItem(Paragraph(text, styles["Normal"])) for text in _LIMITATIONS]
        return [
            Paragraph("Principal limitations", styles["Heading2"]),
            ListFlowable(items, bulletType="bullet"),
        ]

    def _disclaimer(self, text: str) -> list[Any]:
        from reportlab.lib.styles import ParagraphStyle  # type: ignore[import-untyped]
        from reportlab.platypus import Paragraph  # type: ignore[import-untyped]

        base = self._styles()["Normal"]
        style = ParagraphStyle("Disclaimer", parent=base, fontName="Helvetica-Bold", fontSize=9)
        return [
            Paragraph(text, style),
            Paragraph(OSM_ATTRIBUTION, base),
        ]

    # -- data helpers -------------------------------------------------------

    @staticmethod
    def _version_label(version: Any) -> str:
        """Return ``name@version`` for a version FK, or an em dash if absent."""
        if version is None:
            return "—"
        name = getattr(version, "name", "")
        value = getattr(version, "version", "")
        return f"{name}@{value}" if name else str(value)

    @staticmethod
    def _imagery_asset(analysis: Any) -> Any:
        from apps.imagery.models import ImageryAsset

        return ImageryAsset.objects.filter(analysis=analysis).order_by("created_at").first()

    @staticmethod
    def _assumption(analysis: Any) -> Any:
        from apps.analyses.models import AnalysisAssumption

        return AnalysisAssumption.objects.filter(analysis=analysis).first()

    def _centroid(self, analysis: Any, buildings: list[Any]) -> tuple[float, float] | None:
        """Return an approximate ``(lon, lat)`` centre for the analysis."""
        points = [b.centroid for b in buildings if getattr(b, "centroid", None) is not None]
        if points:
            lon = sum(p.x for p in points) / len(points)
            lat = sum(p.y for p in points) / len(points)
            return (lon, lat)
        asset = self._imagery_asset(analysis)
        bounds = getattr(asset, "bounds", None) or {}
        if {"left", "right", "top", "bottom"} <= set(bounds):
            return (
                (float(bounds["left"]) + float(bounds["right"])) / 2,
                (float(bounds["top"]) + float(bounds["bottom"])) / 2,
            )
        return None

    @staticmethod
    def _exterior_rings(buildings: list[Any]) -> list[list[tuple[float, float]]]:
        """Return exterior-ring coordinate lists for each building footprint."""
        rings: list[list[tuple[float, float]]] = []
        for building in buildings:
            geometry = getattr(building, "geometry", None)
            if geometry is None:
                continue
            try:
                exterior = geometry.coords[0]
                rings.append([(float(x), float(y)) for x, y in exterior])
            except (IndexError, TypeError, ValueError):
                continue
        return rings
