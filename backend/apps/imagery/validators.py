"""Security validation for untrusted uploaded rasters (spec §11).

Uploaded imagery is treated as UNTRUSTED. :class:`RasterUploadValidator`
enforces hard limits (file size, decompression-bomb pixel cap) and content
rules (readable raster, present CRS, minimum band count, supported dtype,
finite/non-degenerate bounds) BEFORE an :class:`~apps.imagery.models.ImageryAsset`
is persisted.

Design notes:
- Only the raster *header* is inspected (``rasterio`` reads headers lazily);
  the full raster is never read to validate, which is what makes the pixel cap
  an effective decompression-bomb guard.
- User-input problems raise :class:`~common.errors.ValidationError` (HTTP 400);
  genuine backend failures (e.g. a non-local storage backend, a missing object)
  surface as :class:`~common.errors.InfrastructureError`.
- Limits are configurable via settings (``IMAGERY_MAX_UPLOAD_BYTES``,
  ``IMAGERY_MAX_PIXELS``, ``IMAGERY_MIN_BANDS``, ``IMAGERY_SUPPORTED_DTYPES``)
  with conservative defaults; nothing is hardcoded at the call site.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Any

from django.conf import settings

from common.errors import InfrastructureError, ValidationError
from common.logging import get_logger

from .providers import ImageryMetadata, metadata_from_dataset

logger = get_logger("imagery.validators")

# Conservative defaults; each is overridable via settings (see from_settings).
DEFAULT_MAX_UPLOAD_BYTES = 200 * 1024 * 1024  # 200 MiB
DEFAULT_MAX_PIXELS = 500_000_000  # width * height * bands decompression-bomb cap
DEFAULT_MIN_BANDS = 3  # RGB inference requirement (canonical bands R,G,B)
# Real-valued raster dtypes we can normalize/infer on. Complex/unknown dtypes
# are rejected: the ML preprocessing (percentile normalize) is undefined for them.
DEFAULT_SUPPORTED_DTYPES: frozenset[str] = frozenset(
    {"uint8", "uint16", "int16", "uint32", "int32", "float32", "float64"}
)


@dataclass(frozen=True)
class RasterUploadLimits:
    """Configurable limits/rules for validating an uploaded raster.

    Attributes:
        max_upload_bytes: Maximum accepted file size in bytes.
        max_pixels: Maximum accepted ``width * height * bands`` product.
        min_bands: Minimum number of bands required (>= 3 for RGB inference).
        supported_dtypes: Accepted per-band pixel dtypes.
    """

    max_upload_bytes: int = DEFAULT_MAX_UPLOAD_BYTES
    max_pixels: int = DEFAULT_MAX_PIXELS
    min_bands: int = DEFAULT_MIN_BANDS
    supported_dtypes: frozenset[str] = DEFAULT_SUPPORTED_DTYPES

    @classmethod
    def from_settings(cls) -> RasterUploadLimits:
        """Build limits from Django settings, falling back to module defaults."""
        return cls(
            max_upload_bytes=int(
                getattr(settings, "IMAGERY_MAX_UPLOAD_BYTES", DEFAULT_MAX_UPLOAD_BYTES)
            ),
            max_pixels=int(getattr(settings, "IMAGERY_MAX_PIXELS", DEFAULT_MAX_PIXELS)),
            min_bands=int(getattr(settings, "IMAGERY_MIN_BANDS", DEFAULT_MIN_BANDS)),
            supported_dtypes=frozenset(
                getattr(settings, "IMAGERY_SUPPORTED_DTYPES", DEFAULT_SUPPORTED_DTYPES)
            ),
        )


class RasterUploadValidator:
    """Validate untrusted uploaded rasters against :class:`RasterUploadLimits`.

    Args:
        limits: Limits to enforce (defaults to :meth:`RasterUploadLimits.from_settings`).
    """

    def __init__(self, limits: RasterUploadLimits | None = None) -> None:
        self._limits = limits or RasterUploadLimits.from_settings()

    def validate_size(self, size_bytes: int | None) -> None:
        """Reject an upload whose declared size exceeds the limit.

        Called before the bytes are stored so an oversized upload never lands
        in object storage. A ``None`` size (unknown) is deferred to the
        post-store, on-disk check in :meth:`validate_raster`.

        Raises:
            ValidationError: If ``size_bytes`` exceeds ``max_upload_bytes``.
        """
        if size_bytes is None:
            return
        if size_bytes > self._limits.max_upload_bytes:
            logger.warning("Rejected oversized imagery upload")
            raise ValidationError(
                "Uploaded imagery exceeds the maximum allowed size.",
                code="imagery_too_large",
                details={"max_bytes": self._limits.max_upload_bytes, "size_bytes": size_bytes},
            )

    def validate_raster(self, path: str, *, checksum: str) -> ImageryMetadata:
        """Validate the stored raster header and return its metadata.

        Inspects the header only (no full read): enforces the pixel cap, then
        checks CRS presence, band count, dtype, and finite/non-degenerate
        bounds. On success returns the extracted :class:`ImageryMetadata`.

        Args:
            path: Local filesystem path to the stored raster.
            checksum: Precomputed hex SHA-256 of the raster bytes.

        Returns:
            The extracted :class:`ImageryMetadata`.

        Raises:
            ValidationError: If the file is unreadable/malformed or violates a rule.
            InfrastructureError: If the on-disk size cannot be determined.
        """
        import rasterio

        self._check_file_size(path)
        try:
            with rasterio.open(path) as ds:
                self._check_dimensions(ds)
                self._check_crs(ds)
                self._check_bands(ds)
                self._check_dtype(ds)
                self._check_bounds(ds)
                metadata = metadata_from_dataset(ds, checksum)
        except (ValidationError, InfrastructureError):
            raise
        except Exception as exc:  # rasterio raises many concrete errors
            logger.warning("Rejected unreadable/malformed imagery upload")
            raise ValidationError(
                "Uploaded file is not a readable raster.",
                code="imagery_unreadable",
                details={"reason": "unreadable"},
            ) from exc
        return metadata

    def _check_file_size(self, path: str) -> None:
        """Re-check the authoritative on-disk size of the stored raster."""
        try:
            size_bytes = os.path.getsize(path)
        except OSError as exc:
            raise InfrastructureError(
                "Failed to stat stored imagery for validation.", details={"path": path}
            ) from exc
        self.validate_size(size_bytes)

    def _check_dimensions(self, ds: Any) -> None:
        """Reject rasters exceeding the pixel cap (decompression-bomb guard)."""
        width, height, bands = int(ds.width), int(ds.height), int(ds.count)
        pixels = width * height * bands
        if pixels > self._limits.max_pixels:
            logger.warning("Rejected oversized-dimension imagery upload")
            raise ValidationError(
                "Raster dimensions exceed the maximum allowed pixel count.",
                code="imagery_too_many_pixels",
                details={
                    "max_pixels": self._limits.max_pixels,
                    "pixels": pixels,
                    "width": width,
                    "height": height,
                    "bands": bands,
                },
            )

    def _check_crs(self, ds: Any) -> None:
        """Reject rasters without a coordinate reference system."""
        if ds.crs is None:
            raise ValidationError(
                "Uploaded raster has no coordinate reference system (CRS).",
                code="imagery_missing_crs",
                details={"reason": "missing_crs"},
            )

    def _check_bands(self, ds: Any) -> None:
        """Reject rasters with fewer than the required number of bands."""
        bands = int(ds.count)
        if bands < self._limits.min_bands:
            raise ValidationError(
                "Uploaded raster has too few bands for RGB inference.",
                code="imagery_too_few_bands",
                details={"min_bands": self._limits.min_bands, "bands": bands},
            )

    def _check_dtype(self, ds: Any) -> None:
        """Reject rasters whose band dtypes are unsupported."""
        for dtype in ds.dtypes:
            if str(dtype) not in self._limits.supported_dtypes:
                raise ValidationError(
                    "Uploaded raster has an unsupported pixel data type.",
                    code="imagery_unsupported_dtype",
                    details={
                        "dtype": str(dtype),
                        "supported": sorted(self._limits.supported_dtypes),
                    },
                )

    def _check_bounds(self, ds: Any) -> None:
        """Reject rasters with non-finite or degenerate bounds."""
        bounds = ds.bounds
        values = (
            float(bounds.left),
            float(bounds.bottom),
            float(bounds.right),
            float(bounds.top),
        )
        if not all(math.isfinite(value) for value in values):
            raise ValidationError(
                "Uploaded raster has non-finite bounds.",
                code="imagery_invalid_bounds",
                details={"reason": "non_finite"},
            )
        left, bottom, right, top = values
        if right <= left or top <= bottom:
            raise ValidationError(
                "Uploaded raster has degenerate (zero-area) bounds.",
                code="imagery_invalid_bounds",
                details={"reason": "degenerate"},
            )


__all__ = [
    "DEFAULT_MAX_PIXELS",
    "DEFAULT_MAX_UPLOAD_BYTES",
    "DEFAULT_MIN_BANDS",
    "DEFAULT_SUPPORTED_DTYPES",
    "RasterUploadLimits",
    "RasterUploadValidator",
]
