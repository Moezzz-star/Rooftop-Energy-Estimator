"""Object storage abstraction (system-architecture §4).

Domain services depend only on the :class:`ObjectStorage` protocol; no domain
code touches the filesystem or boto3 directly. :func:`get_storage` selects the
concrete implementation from the ``STORAGE_BACKEND`` setting so a filesystem
deployment can switch to S3/MinIO with no domain change.

Keys are opaque logical paths (e.g. ``analyses/{id}/rasters/scene.tif``).
"""

from __future__ import annotations

import hashlib
import shutil
from collections.abc import Iterable
from pathlib import Path
from typing import BinaryIO, Protocol, cast, runtime_checkable

from django.conf import settings

from common.errors import InfrastructureError, NotFoundError
from common.logging import get_logger

logger = get_logger("storage")

_CHUNK = 1024 * 1024  # 1 MiB streaming chunk for hashing/copying


@runtime_checkable
class ObjectStorage(Protocol):
    """Protocol for artifact/raster storage backends."""

    def save(self, key: str, data: bytes | BinaryIO, content_type: str | None = None) -> str:
        """Persist ``data`` under ``key`` and return the stored URI/key."""
        ...

    def open(self, key: str) -> BinaryIO:
        """Open ``key`` for binary reading."""
        ...

    def read_bytes(self, key: str) -> bytes:
        """Return the full contents of ``key`` as bytes."""
        ...

    def exists(self, key: str) -> bool:
        """Return whether ``key`` exists."""
        ...

    def delete(self, key: str) -> None:
        """Delete ``key`` (no error if it is already absent)."""
        ...

    def url(self, key: str, expires: int | None = None) -> str:
        """Return a local path or presigned URL for ``key``."""
        ...

    def list(self, prefix: str) -> Iterable[str]:
        """Yield keys beginning with ``prefix``."""
        ...

    def copy(self, src_key: str, dst_key: str) -> None:
        """Copy ``src_key`` to ``dst_key``."""
        ...

    def checksum(self, key: str) -> str:
        """Return the hex SHA-256 checksum of ``key``'s contents."""
        ...


class FilesystemStorage:
    """Filesystem-backed :class:`ObjectStorage` rooted at ``MEDIA_ROOT``.

    Keys are interpreted as relative POSIX paths beneath the root. Path
    traversal outside the root is rejected.
    """

    def __init__(self, root: str | Path | None = None) -> None:
        self._root = Path(root or settings.MEDIA_ROOT).resolve()

    def _resolve(self, key: str) -> Path:
        """Resolve ``key`` to an absolute path, guarding against traversal."""
        candidate = (self._root / key).resolve()
        if not str(candidate).startswith(str(self._root)):
            raise InfrastructureError(
                "Resolved storage path escapes the storage root.",
                details={"key": key},
            )
        return candidate

    def save(self, key: str, data: bytes | BinaryIO, content_type: str | None = None) -> str:
        """Write ``data`` to ``key``, creating parent directories."""
        path = self._resolve(key)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("wb") as fh:
                if isinstance(data, bytes):
                    fh.write(data)
                else:
                    shutil.copyfileobj(data, fh, _CHUNK)
        except OSError as exc:
            logger.error("Failed to save object", extra={"key": key})
            raise InfrastructureError(
                "Failed to write object to storage.", details={"key": key}
            ) from exc
        return key

    def open(self, key: str) -> BinaryIO:
        """Open ``key`` for binary reading."""
        path = self._resolve(key)
        try:
            return path.open("rb")
        except FileNotFoundError as exc:
            raise NotFoundError("Object not found.", details={"key": key}) from exc
        except OSError as exc:
            raise InfrastructureError("Failed to open object.", details={"key": key}) from exc

    def read_bytes(self, key: str) -> bytes:
        """Return the full contents of ``key``."""
        with self.open(key) as fh:
            return fh.read()

    def exists(self, key: str) -> bool:
        """Return whether ``key`` exists as a file."""
        return self._resolve(key).is_file()

    def delete(self, key: str) -> None:
        """Delete ``key`` if present; a missing key is not an error."""
        path = self._resolve(key)
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            raise InfrastructureError("Failed to delete object.", details={"key": key}) from exc

    def url(self, key: str, expires: int | None = None) -> str:
        """Return a filesystem URI for ``key`` (no expiry semantics)."""
        return self._resolve(key).as_uri()

    def list(self, prefix: str) -> Iterable[str]:
        """Yield keys beneath ``prefix`` relative to the storage root."""
        base = self._resolve(prefix)
        search_root = base if base.is_dir() else base.parent
        if not search_root.exists():
            return
        for path in sorted(search_root.rglob("*")):
            if not path.is_file():
                continue
            key = path.relative_to(self._root).as_posix()
            if key.startswith(prefix):
                yield key

    def copy(self, src_key: str, dst_key: str) -> None:
        """Copy ``src_key`` to ``dst_key``."""
        src = self._resolve(src_key)
        dst = self._resolve(dst_key)
        if not src.is_file():
            raise NotFoundError("Source object not found.", details={"key": src_key})
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
        except OSError as exc:
            raise InfrastructureError(
                "Failed to copy object.",
                details={"src": src_key, "dst": dst_key},
            ) from exc

    def checksum(self, key: str) -> str:
        """Return the streaming SHA-256 hex digest of ``key``."""
        digest = hashlib.sha256()
        with self.open(key) as fh:
            for chunk in iter(lambda: fh.read(_CHUNK), b""):
                digest.update(chunk)
        return digest.hexdigest()


class S3Storage:
    """S3/MinIO-backed storage (stub).

    A full boto3 implementation is added when the ``s3`` backend is enabled.
    Instantiation fails fast if boto3 is unavailable so misconfiguration is
    obvious rather than silently degrading.
    """

    def __init__(self) -> None:
        try:
            import boto3  # noqa: F401  (import probe only)
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise InfrastructureError(
                "boto3 is required for the S3 storage backend but is not installed."
            ) from exc
        raise NotImplementedError("S3Storage is not yet implemented.")


def get_storage() -> ObjectStorage:
    """Return the configured :class:`ObjectStorage` implementation.

    Selection is driven by the ``STORAGE_BACKEND`` setting (``filesystem`` by
    default). Unknown values raise :class:`InfrastructureError`.
    """
    backend = getattr(settings, "STORAGE_BACKEND", "filesystem").lower()
    if backend == "filesystem":
        return FilesystemStorage()
    if backend == "s3":
        # S3Storage is an intentional stub whose __init__ always raises; the cast
        # documents that the completed implementation will satisfy ObjectStorage.
        return cast(ObjectStorage, S3Storage())
    raise InfrastructureError("Unknown STORAGE_BACKEND configured.", details={"backend": backend})
