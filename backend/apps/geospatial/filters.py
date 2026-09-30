"""Query-parameter parsing helpers for the geospatial app.

Provides a reusable ``bbox`` parser shared by the buildings, features, and
projection endpoints. Parsing lives here (not in views) so the parsing rules
have a single home and are unit-testable.
"""

from __future__ import annotations

from common.errors import ValidationError


def parse_bbox(raw: str | None) -> tuple[float, float, float, float] | None:
    """Parse a ``bbox`` query parameter into ``(west, south, east, north)``.

    Args:
        raw: Comma-separated ``"west,south,east,north"`` string, or ``None``.

    Returns:
        The parsed tuple, or ``None`` when ``raw`` is ``None``/empty.

    Raises:
        ValidationError: If the value is malformed or geometrically invalid.
    """
    if not raw:
        return None
    parts = raw.split(",")
    if len(parts) != 4:
        raise ValidationError("bbox must be 'west,south,east,north'.", details={"bbox": raw})
    try:
        west, south, east, north = (float(p) for p in parts)
    except ValueError as exc:
        raise ValidationError("bbox values must be numeric.", details={"bbox": raw}) from exc
    if west >= east or south >= north:
        raise ValidationError("bbox must satisfy west<east and south<north.", details={"bbox": raw})
    return (west, south, east, north)


def parse_float(raw: str | None, *, field: str) -> float | None:
    """Parse an optional numeric query parameter.

    Args:
        raw: Raw string value, or ``None``.
        field: Field name for error reporting.

    Returns:
        The parsed float, or ``None`` when ``raw`` is absent.

    Raises:
        ValidationError: If the value is non-numeric.
    """
    if raw is None or raw == "":
        return None
    try:
        return float(raw)
    except ValueError as exc:
        raise ValidationError(f"{field} must be numeric.", details={field: raw}) from exc


def parse_int(raw: str | None, *, field: str, default: int) -> int:
    """Parse an optional integer query parameter with a default.

    Raises:
        ValidationError: If the value is present but not an integer.
    """
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValidationError(f"{field} must be an integer.", details={field: raw}) from exc
