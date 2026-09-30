"""Service-level tests for untrusted upload handling and metadata persistence.

Covers the security path end-to-end within the imagery service boundary:
oversized rejection, orphan cleanup on rejected uploads, and persistence of the
full :class:`~apps.imagery.models.ImageryAsset` metadata record for a valid
upload. Requires the DB + GeoDjango + rasterio stack.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.imagery.models import DEFAULT_ATTRIBUTION, DEFAULT_LICENSE, ImageryAsset
from apps.imagery.services import ImageryService
from apps.imagery.validators import RasterUploadLimits, RasterUploadValidator
from common.errors import ValidationError
from common.storage import FilesystemStorage

from .conftest import write_geotiff

rasterio = pytest.importorskip("rasterio")

pytestmark = pytest.mark.django_db


def _upload(path: Path, name: str = "scene.tif") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, path.read_bytes(), content_type="image/tiff")


def _remaining_objects(storage: FilesystemStorage) -> list[str]:
    return list(storage.list("analyses/"))


def test_register_upload_persists_full_metadata(
    tmp_path: Path,
    analysis_factory: Callable[..., Any],
) -> None:
    """A valid upload persists the full metadata record (spec §11)."""
    analysis = analysis_factory()
    storage = FilesystemStorage(root=tmp_path)
    src = write_geotiff(tmp_path / "src.tif", bands=3, dtype="uint8", nodata=0.0)
    service = ImageryService(storage=storage)

    asset = service.register_upload(analysis, _upload(src, "rooftops.tif"))

    asset.refresh_from_db()
    assert asset.provider == "uploaded_raster"
    assert asset.original_filename == "rooftops.tif"
    assert asset.crs == "EPSG:32632"
    assert asset.bands == 3
    assert asset.width == 8
    assert asset.height == 8
    assert asset.dtype == "uint8"
    assert asset.nodata == 0.0
    assert len(asset.transform) == 6
    assert len(asset.checksum) == 64
    assert asset.license == DEFAULT_LICENSE
    assert asset.attribution == DEFAULT_ATTRIBUTION
    assert asset.lineage["origin"] == "upload"
    assert asset.lineage["filename"] == "rooftops.tif"
    assert "ingested_at" in asset.lineage
    assert asset.bounds["right"] > asset.bounds["left"]


def test_register_upload_rejects_oversized_and_stores_nothing(
    tmp_path: Path,
    analysis_factory: Callable[..., Any],
) -> None:
    """An oversized upload is rejected and never lands in storage."""
    analysis = analysis_factory()
    storage = FilesystemStorage(root=tmp_path)
    src = write_geotiff(tmp_path / "src.tif")
    service = ImageryService(
        storage=storage,
        validator=RasterUploadValidator(RasterUploadLimits(max_upload_bytes=1)),
    )

    upload = _upload(src)
    with pytest.raises(ValidationError) as exc:
        service.register_upload(analysis, upload)

    assert exc.value.code == "imagery_too_large"
    assert ImageryAsset.objects.filter(analysis=analysis).count() == 0
    assert _remaining_objects(storage) == []


def test_register_upload_cleans_up_orphan_on_rejection(
    tmp_path: Path,
    analysis_factory: Callable[..., Any],
) -> None:
    """A malformed upload is stored then deleted, leaving no orphan bytes."""
    analysis = analysis_factory()
    storage = FilesystemStorage(root=tmp_path)
    bad = tmp_path / "bad.tif"
    bad.write_bytes(b"not a raster at all")
    service = ImageryService(storage=storage)

    upload = _upload(bad)
    with pytest.raises(ValidationError) as exc:
        service.register_upload(analysis, upload)

    assert exc.value.code == "imagery_unreadable"
    assert ImageryAsset.objects.filter(analysis=analysis).count() == 0
    assert _remaining_objects(storage) == []


def test_register_upload_rejects_missing_crs_and_cleans_up(
    tmp_path: Path,
    analysis_factory: Callable[..., Any],
) -> None:
    """A CRS-less upload is rejected and cleaned up (no orphan)."""
    analysis = analysis_factory()
    storage = FilesystemStorage(root=tmp_path)
    src = write_geotiff(tmp_path / "no_crs.tif", crs=None)
    service = ImageryService(storage=storage)

    upload = _upload(src)
    with pytest.raises(ValidationError) as exc:
        service.register_upload(analysis, upload)

    assert exc.value.code == "imagery_missing_crs"
    assert _remaining_objects(storage) == []
