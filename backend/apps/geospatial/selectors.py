"""Read queries for the geospatial app (selectors).

Selectors keep read logic out of write services and views (code-architecture
§8). All queries are scoped by the ownership chain
(``building.analysis.project.owner``) so a caller only ever sees their own data.
"""

from __future__ import annotations

from typing import Any

from django.db.models import QuerySet

# DEC-02 canonical disclaimer — reuse the single source of truth from the solar
# app rather than re-declaring the text (avoids drift). Imported lazily-safe:
# ``solar.models`` only depends on ``common`` so there is no import cycle.
from apps.solar.models import DISCLAIMER
from common.errors import NotFoundError
from common.logging import get_logger

from .models import Building

logger = get_logger("geospatial.selectors")

# Direct model fields orderable via ``?order=<field>`` / ``?order=-<field>``.
_ORDER_FIELDS: dict[str, str] = {
    "area": "area_m2",
    "confidence": "confidence",
    "index": "index",
}

# Solar fields orderable only via a join+aggregate (a building may have several
# estimates); use ``Max`` to avoid row multiplication. Documented as supported
# only when the solar relation is present (else ordering is ignored).
_ANNOTATED_ORDER_FIELDS: dict[str, str] = {
    "capacity": "solar_estimates__capacity_kwp",
    "annual_kwh": "solar_estimates__annual_kwh",
}

_DEFAULT_ORDER = "-area"


def buildings_for_owner(owner: Any) -> QuerySet[Building]:
    """Return all buildings visible to ``owner`` (ownership-scoped base query)."""
    return Building.objects.filter(analysis__project__owner=owner)


def list_buildings(
    analysis_id: Any,
    owner: Any,
    *,
    bbox: tuple[float, float, float, float] | None = None,
    min_area: float | None = None,
    min_confidence: float | None = None,
    order: str = _DEFAULT_ORDER,
) -> QuerySet[Building]:
    """Return an ownership-scoped, filtered, ordered building queryset.

    Args:
        analysis_id: Analysis whose buildings to list.
        owner: The requesting user (ownership scope).
        bbox: Optional ``(west, south, east, north)`` filter (EPSG:4326).
        min_area: Optional minimum ``area_m2``.
        min_confidence: Optional minimum ``confidence``.
        order: Ordering key. Accepts ``area``/``confidence``/``index`` and, when
            the solar relation is present, ``capacity``/``annual_kwh``. Prefix
            with ``-`` for descending (e.g. ``-area``); defaults to ``-area``.

    Returns:
        A lazily-evaluated :class:`QuerySet` of :class:`Building`.
    """
    qs = buildings_for_owner(owner).filter(analysis_id=analysis_id)
    if bbox is not None:
        qs = _apply_bbox(qs, bbox)
    if min_area is not None:
        qs = qs.filter(area_m2__gte=min_area)
    if min_confidence is not None:
        qs = qs.filter(confidence__gte=min_confidence)
    return _apply_ordering(qs, order)


def _apply_ordering(qs: QuerySet[Building], order: str) -> QuerySet[Building]:
    """Apply an ``?order=`` clause, tolerating an absent solar relation."""
    key = order.lstrip("-")
    descending = order.startswith("-")
    if key in _ORDER_FIELDS:
        field = _ORDER_FIELDS[key]
        return qs.order_by(f"-{field}" if descending else field)
    if key in _ANNOTATED_ORDER_FIELDS:
        return _apply_annotated_ordering(qs, key, descending=descending)
    logger.warning("Unsupported ordering key '%s'; defaulting to area desc", order)
    return qs.order_by("-area_m2")


def _apply_annotated_ordering(
    qs: QuerySet[Building], key: str, *, descending: bool
) -> QuerySet[Building]:
    """Order by an aggregated solar field, falling back if unavailable."""
    from django.core.exceptions import FieldError
    from django.db.models import Max

    alias = f"_order_{key}"
    try:
        annotated = qs.annotate(**{alias: Max(_ANNOTATED_ORDER_FIELDS[key])})
        return annotated.order_by(f"-{alias}" if descending else alias)
    except FieldError:
        logger.warning("Solar relation unavailable; ignoring order '%s'", key)
        return qs.order_by("-area_m2")


def get_building(building_id: Any, owner: Any) -> Building:
    """Return a single owned building with its roof preloaded.

    Raises:
        NotFoundError: If the building does not exist or is not owned by
            ``owner``.
    """
    try:
        return buildings_for_owner(owner).select_related("roof", "analysis").get(pk=building_id)
    except Building.DoesNotExist as exc:
        raise NotFoundError("Building not found.", details={"id": str(building_id)}) from exc


def _apply_bbox(
    qs: QuerySet[Building], bbox: tuple[float, float, float, float]
) -> QuerySet[Building]:
    """Filter ``qs`` to buildings intersecting ``bbox`` (EPSG:4326)."""
    from django.contrib.gis.geos import Polygon

    west, south, east, north = bbox
    envelope = Polygon.from_bbox((west, south, east, north))
    envelope.srid = 4326
    return qs.filter(geometry__intersects=envelope)


def results_summary(analysis_id: Any, owner: Any) -> dict[str, Any]:
    """Aggregate a results summary for an analysis (#16, §9).

    Args:
        analysis_id: Analysis to summarise.
        owner: Requesting user (ownership scope).

    Returns:
        A dict with building/area/energy totals, average specific yield, the
        assumed system losses and snapshot version identifiers, a transparent
        ``data_quality`` block, and the DEC-02 disclaimer. Solar totals fall
        back to ``0`` when the solar relation is absent.
    """
    from django.db.models import Count, Sum

    from .services import DataQualityService

    analysis = _get_owned_analysis(analysis_id, owner)
    qs = buildings_for_owner(owner).filter(analysis_id=analysis_id)
    base = qs.aggregate(
        building_count=Count("id"),
        total_area_m2=Sum("area_m2"),
        total_usable_area_m2=Sum("roof__usable_area_m2"),
    )
    solar = _solar_totals(qs)
    summary: dict[str, Any] = {
        "building_count": base["building_count"] or 0,
        "total_area_m2": base["total_area_m2"] or 0.0,
        "total_usable_area_m2": base["total_usable_area_m2"] or 0.0,
        "total_capacity_kwp": solar["capacity_kwp"],
        "total_annual_kwh": solar["annual_kwh"],
        "average_specific_yield": solar["specific_yield"],
        "system_losses": _assumed_system_losses(analysis),
        "model_version": _version_label(getattr(analysis, "model_version", None)),
        "calculation_version": _version_label(getattr(analysis, "calculation_version", None)),
        "disclaimer": DISCLAIMER,
    }
    if analysis is not None:
        summary["data_quality"] = DataQualityService().summarize(analysis)
    return summary


def _get_owned_analysis(analysis_id: Any, owner: Any) -> Any:
    """Return the owned ``analyses.Analysis`` or ``None`` (without importing it)."""
    from django.apps import apps as django_apps

    model = django_apps.get_model("analyses", "Analysis")
    return model.objects.filter(pk=analysis_id, project__owner=owner).first()


def _assumed_system_losses(analysis: Any) -> float | None:
    """Read the frozen ``system_losses`` assumption defensively."""
    if analysis is None:
        return None
    assumption = getattr(analysis, "assumption", None)
    value = getattr(assumption, "system_losses", None)
    return None if value is None else float(value)


def _version_label(version: Any) -> Any:
    """Return the ``version`` identifier of a snapshot FK, or ``None``."""
    return None if version is None else getattr(version, "version", None)


def _solar_totals(qs: QuerySet[Building]) -> dict[str, float | None]:
    """Sum/average solar metrics across buildings, tolerating an absent app."""
    from django.core.exceptions import FieldError
    from django.db.models import Avg, Sum

    try:
        agg = qs.aggregate(
            capacity_kwp=Sum("solar_estimates__capacity_kwp"),
            annual_kwh=Sum("solar_estimates__annual_kwh"),
            specific_yield=Avg("solar_estimates__specific_yield"),
        )
    except FieldError:
        logger.warning("Solar relation unavailable; reporting zero solar totals")
        return {"capacity_kwp": 0.0, "annual_kwh": 0.0, "specific_yield": None}
    return {
        "capacity_kwp": agg["capacity_kwp"] or 0.0,
        "annual_kwh": agg["annual_kwh"] or 0.0,
        "specific_yield": None if agg["specific_yield"] is None else float(agg["specific_yield"]),
    }
