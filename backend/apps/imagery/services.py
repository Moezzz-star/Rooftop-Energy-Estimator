"""Domain services for the imagery app.

:class:`ImageryService` owns raster ingestion: it persists uploaded bytes to
object storage, computes a checksum, extracts metadata via an
:class:`~apps.imagery.providers.ImageryProvider`, derives a 4326 footprint, and
records an :class:`~apps.imagery.models.ImageryAsset`. Dependencies (storage +
provider) are injected via ``__init__`` for testability (code-architecture §6).

Infrastructure/library errors (rasterio, storage) are mapped to
:class:`common.errors.InfrastructureError` at the boundary; no third-party
exception leaks to callers.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from django.conf import settings
from django.utils import timezone

from common.errors import InfrastructureError, ValidationError
from common.logging import get_logger
from common.storage import ObjectStorage, get_storage

from .models import DEFAULT_ATTRIBUTION, DEFAULT_LICENSE, ImageryAsset
from .providers import ImageryMetadata, UploadedRasterProvider
from .validators import RasterUploadValidator

logger = get_logger("imagery.service")

# Storage key template: analyses/{analysis_id}/imagery/{token}-{name}
_KEY_TEMPLATE = "analyses/{analysis_id}/imagery/{token}-{name}"
_SAMPLE_FILENAME = "sample_imagery.tif"


class ImageryService:
    """Ingest rasters and expose their metadata.

    Args:
        storage: Object storage backend (defaults to the configured backend).
        provider: Provider used to read raster metadata/windows (defaults to
            :class:`UploadedRasterProvider` bound to ``storage``).
        validator: Security validator applied to untrusted uploads (defaults to
            :class:`RasterUploadValidator` built from settings).
    """

    def __init__(
        self,
        storage: ObjectStorage | None = None,
        provider: UploadedRasterProvider | None = None,
        validator: RasterUploadValidator | None = None,
    ) -> None:
        self._storage = storage or get_storage()
        self._provider = provider or UploadedRasterProvider(storage=self._storage)
        self._validator = validator or RasterUploadValidator()

    def register_upload(self, analysis: Any, file: Any) -> ImageryAsset:
        """Persist an uploaded raster and record an :class:`ImageryAsset`.

        The upload is treated as UNTRUSTED (spec §11): its declared size is
        checked before storage, and after storage the raster header is validated
        (readable raster, pixel cap, CRS, band count, dtype, bounds). If
        validation fails the stored bytes are deleted so no orphan remains.

        Args:
            analysis: The owning ``analyses.Analysis`` instance.
            file: An uploaded file-like object (``django...UploadedFile``).

        Returns:
            The persisted :class:`ImageryAsset`.

        Raises:
            ValidationError: If no file was supplied or the raster is invalid.
            InfrastructureError: If storage or metadata extraction fails.
        """
        if file is None:
            raise ValidationError("An imagery file is required.", details={"file": "required"})

        self._validator.validate_size(getattr(file, "size", None))

        filename = self._safe_name(getattr(file, "name", "upload.tif"))
        key = _KEY_TEMPLATE.format(analysis_id=analysis.pk, token=uuid.uuid4().hex, name=filename)
        logger.info(
            "Registering imagery upload",
            extra={"analysis_id": str(analysis.pk)},
        )
        self._storage.save(key, file)
        metadata = self._validate_stored_upload(key)
        lineage = {
            "origin": "upload",
            "filename": filename,
            "ingested_at": timezone.now().isoformat(),
        }
        return self._build_asset(
            analysis, key, metadata, lineage=lineage, original_filename=filename
        )

    def register_from_storage(self, analysis: Any, storage_key: str) -> ImageryAsset:
        """Record an :class:`ImageryAsset` for a raster already in storage.

        Used by the ingest task and internal callers when the bytes are present
        under ``storage_key`` (no re-upload).

        Args:
            analysis: The owning ``analyses.Analysis`` instance.
            storage_key: Existing object-storage key.

        Returns:
            The persisted :class:`ImageryAsset`.
        """
        logger.info(
            "Registering imagery from storage",
            extra={"analysis_id": str(analysis.pk)},
        )
        metadata = self._provider.read_metadata(storage_key)
        lineage = {
            "origin": "storage",
            "storage_key": storage_key,
            "ingested_at": timezone.now().isoformat(),
        }
        return self._build_asset(
            analysis,
            storage_key,
            metadata,
            lineage=lineage,
            original_filename=self._safe_name(storage_key),
        )

    def register_bundled_sample(self, analysis: Any) -> ImageryAsset:
        """Register the bundled ``sample_imagery.tif`` as an asset.

        Copies the bundled sample raster into object storage under an
        analysis-scoped key and reads its real metadata. This backs the
        frontend "select sample imagery" step and the offline sample pipeline.

        Args:
            analysis: The owning ``analyses.Analysis`` instance.

        Returns:
            The persisted :class:`ImageryAsset`.

        Raises:
            InfrastructureError: If the bundled sample is missing or unreadable.
        """
        source = self._sample_path()
        if not source.is_file():
            raise InfrastructureError(
                "Bundled sample imagery is not available.",
                details={"path": str(source)},
            )
        key = _KEY_TEMPLATE.format(
            analysis_id=analysis.pk, token=uuid.uuid4().hex, name=_SAMPLE_FILENAME
        )
        try:
            with source.open("rb") as handle:
                self._storage.save(key, handle)
        except OSError as exc:
            raise InfrastructureError(
                "Failed to copy bundled sample imagery into storage.",
                details={"path": str(source)},
            ) from exc
        logger.info(
            "Registered bundled sample imagery",
            extra={"analysis_id": str(analysis.pk)},
        )
        metadata = self._provider.read_metadata(key)
        lineage = {
            "origin": "sample",
            "filename": _SAMPLE_FILENAME,
            "ingested_at": timezone.now().isoformat(),
        }
        return self._build_asset(
            analysis, key, metadata, lineage=lineage, original_filename=_SAMPLE_FILENAME
        )

    def read_metadata(self, ref: str) -> ImageryMetadata:
        """Return metadata for the raster referenced by ``ref``.

        Args:
            ref: Object-storage key.

        Returns:
            The extracted :class:`ImageryMetadata`.
        """
        return self._provider.read_metadata(ref)

    def _validate_stored_upload(self, key: str) -> ImageryMetadata:
        """Validate a just-stored untrusted upload; clean up on rejection.

        Deletes the stored bytes if validation fails so no orphan object is left
        behind, then re-raises the original error.
        """
        try:
            path = self._provider.local_path(key)
            checksum = self._storage.checksum(key)
            return self._validator.validate_raster(path, checksum=checksum)
        except (ValidationError, InfrastructureError):
            self._delete_quietly(key)
            raise

    def _delete_quietly(self, key: str) -> None:
        """Best-effort delete of ``key``; log and swallow storage failures."""
        try:
            self._storage.delete(key)
            logger.info("Cleaned up rejected imagery upload")
        except InfrastructureError:
            logger.warning("Failed to clean up rejected imagery upload")

    def _build_asset(
        self,
        analysis: Any,
        key: str,
        metadata: ImageryMetadata,
        *,
        lineage: dict[str, Any],
        original_filename: str = "",
        license_: str = DEFAULT_LICENSE,
        attribution: str = DEFAULT_ATTRIBUTION,
    ) -> ImageryAsset:
        """Persist an :class:`ImageryAsset` from extracted ``metadata``."""
        footprint = self._footprint(metadata)
        asset = ImageryAsset.objects.create(
            analysis=analysis,
            provider=self._provider.name,
            original_filename=original_filename,
            storage_key=key,
            checksum=metadata.checksum,
            crs=metadata.crs,
            resolution_m=metadata.resolution_m,
            bounds=metadata.bounds,
            transform=list(metadata.transform),
            width=metadata.width,
            height=metadata.height,
            bands=metadata.bands,
            nodata=metadata.nodata,
            dtype=metadata.dtype,
            license=license_,
            attribution=attribution,
            lineage=lineage,
            footprint=footprint,
        )
        logger.info(
            "Imagery asset recorded",
            extra={"analysis_id": str(analysis.pk)},
        )
        return asset

    def _footprint(self, metadata: ImageryMetadata) -> Any | None:
        """Build a 4326 footprint polygon from native-CRS bounds.

        Returns ``None`` when the CRS is missing or reprojection fails; a null
        footprint is acceptable (the metadata bounds remain authoritative).
        """
        from django.contrib.gis.geos import Polygon

        if not metadata.crs:
            return None
        bounds = metadata.bounds
        try:
            from rasterio.warp import transform_bounds

            left, bottom, right, top = transform_bounds(
                metadata.crs,
                "EPSG:4326",
                bounds["left"],
                bounds["bottom"],
                bounds["right"],
                bounds["top"],
            )
        except Exception as exc:  # reprojection is best-effort
            logger.warning("Failed to reproject footprint to 4326")
            logger.debug("footprint reprojection error: %s", exc)
            return None
        polygon = Polygon.from_bbox((left, bottom, right, top))
        polygon.srid = 4326
        return polygon

    @staticmethod
    def _safe_name(name: str) -> str:
        """Return a filesystem-safe basename for ``name``."""
        base = Path(name).name or "upload.tif"
        return base.replace("/", "_").replace("\\", "_")

    @staticmethod
    def _sample_path() -> Path:
        """Return the filesystem path to the bundled sample raster.

        Honours the ``SAMPLE_IMAGERY_PATH`` setting when present; otherwise
        resolves ``sample-data/sample_imagery.tif`` relative to the repo root
        (``BASE_DIR`` is the ``backend/`` directory).
        """
        configured = getattr(settings, "SAMPLE_IMAGERY_PATH", "")
        if configured:
            return Path(configured)
        return Path(settings.BASE_DIR).parent / "sample-data" / _SAMPLE_FILENAME


__all__ = ["ImageryService"]
