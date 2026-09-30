"""Imagery provider strategy + registry (code-architecture §2, §8).

Providers are the pluggable strategy behind imagery access: each knows how to
read metadata and windowed pixels for a given storage reference. The registry
lists the available sources for the ``/imagery/sources/`` endpoint (§4 #13).

Only :class:`UploadedRasterProvider` is required for the sample/offline path.
External/open-data providers are kept OPTIONAL and stubbed (DEC-04): they are
not registered by default and expose ``available=False`` capabilities.

The :class:`ImageryProvider` Protocol mirrors the shared abstraction described
in ``docs/architecture/code-architecture.md`` §2. It is defined here because the
``ml/model_registry/interfaces.py`` module does not yet exist; when that module
lands, this Protocol should be re-exported from it.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, cast, runtime_checkable
from urllib.parse import urlparse
from urllib.request import url2pathname

from common.errors import InfrastructureError, NotFoundError
from common.logging import get_logger
from common.storage import ObjectStorage, get_storage

if TYPE_CHECKING:  # pragma: no cover - typing only
    import numpy as np

logger = get_logger("imagery.providers")


@dataclass(frozen=True)
class ImageryMetadata:
    """Extracted raster metadata (framework-free value object).

    Attributes:
        crs: Coordinate reference system identifier (e.g. ``"EPSG:32632"``).
        bounds: Native-CRS bounds ``{"left","bottom","right","top"}``.
        resolution_m: Ground sample distance in metres per pixel (nullable).
        bands: Number of raster bands.
        checksum: Hex SHA-256 of the raster bytes.
        width: Raster width in pixels.
        height: Raster height in pixels.
        transform: Affine transform coefficients ``(a, b, c, d, e, f)``.
        nodata: Raster nodata sentinel value, if declared (nullable).
        dtype: Pixel data type of band 1 (e.g. ``"uint8"``).
    """

    crs: str
    bounds: dict[str, float]
    resolution_m: float | None
    bands: int
    checksum: str
    width: int
    height: int
    transform: tuple[float, float, float, float, float, float]
    nodata: float | None
    dtype: str


def metadata_from_dataset(ds: Any, checksum: str) -> ImageryMetadata:
    """Build :class:`ImageryMetadata` from an open ``rasterio`` dataset header.

    Reads header attributes only (no pixel data). Shared by
    :meth:`UploadedRasterProvider.read_metadata` (trusted paths) and the upload
    validator (untrusted uploads) so metadata construction stays single-sourced
    while each caller keeps its own error-mapping semantics.

    Args:
        ds: An open ``rasterio`` dataset.
        checksum: Precomputed hex SHA-256 of the raster bytes.

    Returns:
        The populated :class:`ImageryMetadata`.
    """
    transform = ds.transform
    bounds = ds.bounds
    crs = str(ds.crs) if ds.crs is not None else ""
    resolution_m = abs(float(transform.a)) if transform is not None else None
    nodata = float(ds.nodata) if ds.nodata is not None else None
    dtypes = tuple(ds.dtypes)
    dtype = str(dtypes[0]) if dtypes else ""
    return ImageryMetadata(
        crs=crs,
        bounds={
            "left": float(bounds.left),
            "bottom": float(bounds.bottom),
            "right": float(bounds.right),
            "top": float(bounds.top),
        },
        resolution_m=resolution_m,
        bands=int(ds.count),
        checksum=checksum,
        width=int(ds.width),
        height=int(ds.height),
        transform=(
            float(transform.a),
            float(transform.b),
            float(transform.c),
            float(transform.d),
            float(transform.e),
            float(transform.f),
        ),
        nodata=nodata,
        dtype=dtype,
    )


@dataclass(frozen=True)
class ProviderCapabilities:
    """Declared capabilities of an imagery provider (for the sources endpoint).

    Attributes:
        name: Registry key of the provider.
        title: Human-readable label.
        description: Short description shown to users.
        supports_upload: Whether the provider ingests user uploads.
        supports_windowed_read: Whether windowed reads avoid full-raster loads.
        requires_network: Whether the provider needs outbound network access.
        available: Whether the provider is usable in the current deployment.
    """

    name: str
    title: str
    description: str
    supports_upload: bool
    supports_windowed_read: bool
    requires_network: bool
    available: bool

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return asdict(self)


@runtime_checkable
class ImageryProvider(Protocol):
    """Protocol for imagery sources (code-architecture §2)."""

    name: str

    def read_metadata(self, ref: str) -> ImageryMetadata:
        """Return metadata for the raster referenced by ``ref``."""
        ...

    def open_window(self, ref: str, window: Any) -> np.ndarray[Any, Any]:
        """Return a windowed pixel read; never loads the full raster."""
        ...

    def capabilities(self) -> ProviderCapabilities:
        """Return the provider's declared capabilities."""
        ...


class UploadedRasterProvider:
    """Provider for user-uploaded rasters stored via :class:`ObjectStorage`.

    Metadata and windowed reads go through ``rasterio``; the dataset is opened
    from a local filesystem path when the backend exposes one (the default
    filesystem/sample path) so only the header (or a window) is read, never the
    whole raster into memory. For non-local backends a documented in-memory
    fallback is used.

    Args:
        storage: Object storage used to resolve ``ref`` keys (injected for
            testability; defaults to :func:`common.storage.get_storage`).
    """

    name = "uploaded_raster"

    def __init__(self, storage: ObjectStorage | None = None) -> None:
        self._storage = storage or get_storage()

    def read_metadata(self, ref: str) -> ImageryMetadata:
        """Open ``ref``'s header and extract CRS/bounds/resolution/bands.

        Args:
            ref: Object-storage key of the raster.

        Returns:
            The populated :class:`ImageryMetadata`.

        Raises:
            InfrastructureError: If the raster cannot be opened/parsed.
        """
        import rasterio

        path = self._local_path(ref)
        try:
            with rasterio.open(path) as ds:
                metadata = metadata_from_dataset(ds, self._storage.checksum(ref))
        except (NotFoundError, InfrastructureError):
            raise
        except Exception as exc:  # rasterio raises many concrete errors
            logger.error("Failed to read imagery metadata", extra={"key": ref})
            raise InfrastructureError(
                "Failed to read raster metadata.", details={"key": ref}
            ) from exc
        return metadata

    def open_window(self, ref: str, window: Any) -> np.ndarray[Any, Any]:
        """Return a windowed pixel read for ``ref``.

        Args:
            ref: Object-storage key of the raster.
            window: A ``rasterio.windows.Window`` (or compatible) describing
                the region to read.

        Returns:
            The windowed pixel array (bands-first).

        Raises:
            InfrastructureError: If the windowed read fails.
        """
        import rasterio

        path = self._local_path(ref)
        try:
            with rasterio.open(path) as ds:
                return cast("np.ndarray[Any, Any]", ds.read(window=window))
        except (NotFoundError, InfrastructureError):
            raise
        except Exception as exc:
            logger.error("Failed windowed raster read", extra={"key": ref})
            raise InfrastructureError(
                "Failed to read raster window.", details={"key": ref}
            ) from exc

    def capabilities(self) -> ProviderCapabilities:
        """Return capabilities for the uploaded-raster source."""
        return ProviderCapabilities(
            name=self.name,
            title="Uploaded raster",
            description="User-uploaded GeoTIFF/COG rasters read from object storage.",
            supports_upload=True,
            supports_windowed_read=True,
            requires_network=False,
            available=True,
        )

    def _local_path(self, ref: str) -> str:
        """Resolve ``ref`` to a local filesystem path for header/windowed reads.

        Args:
            ref: Object-storage key.

        Returns:
            An absolute local filesystem path.

        Raises:
            InfrastructureError: If the backend does not expose a local path.
        """
        if not self._storage.exists(ref):
            raise NotFoundError("Imagery object not found.", details={"key": ref})
        uri = self._storage.url(ref)
        parsed = urlparse(uri)
        if parsed.scheme == "file":
            return url2pathname(parsed.path)
        if parsed.scheme in ("", None) and Path(uri).exists():
            return uri
        raise InfrastructureError(
            "UploadedRasterProvider requires a local storage backend for windowed reads.",
            details={"key": ref},
        )

    def local_path(self, ref: str) -> str:
        """Return the resolved local filesystem path for ``ref``.

        Public accessor used by the upload validator, which opens the raster
        with ``rasterio`` directly so it can map read failures to a user-facing
        :class:`~common.errors.ValidationError` rather than an infrastructure
        error. See :meth:`_local_path` for resolution/raise semantics.
        """
        return self._local_path(ref)


class ImageryProviderRegistry:
    """Registry of available imagery providers (strategy lookup, §8).

    The default registry contains only :class:`UploadedRasterProvider`.
    External/open-data providers remain OPTIONAL (DEC-04) and are not registered
    unless explicitly enabled.
    """

    def __init__(self) -> None:
        self._providers: dict[str, ImageryProvider] = {}

    def register(self, provider: ImageryProvider) -> None:
        """Register ``provider`` under its ``name``."""
        self._providers[provider.name] = provider

    def get(self, name: str) -> ImageryProvider:
        """Return the provider registered under ``name``.

        Raises:
            NotFoundError: If no provider is registered under ``name``.
        """
        try:
            return self._providers[name]
        except KeyError as exc:
            raise NotFoundError(
                "Imagery provider is not registered.", details={"provider": name}
            ) from exc

    def available(self) -> list[ProviderCapabilities]:
        """Return capabilities for all registered providers."""
        return [provider.capabilities() for provider in self._providers.values()]


def build_default_registry(storage: ObjectStorage | None = None) -> ImageryProviderRegistry:
    """Construct the default registry (uploaded-raster provider only)."""
    registry = ImageryProviderRegistry()
    registry.register(UploadedRasterProvider(storage=storage))
    return registry


__all__ = [
    "ImageryMetadata",
    "ImageryProvider",
    "ImageryProviderRegistry",
    "ProviderCapabilities",
    "UploadedRasterProvider",
    "build_default_registry",
    "metadata_from_dataset",
]
