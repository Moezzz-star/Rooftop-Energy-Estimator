"""Tests for imagery metadata extraction and the provider registry.

The metadata test performs a real ``rasterio`` read of the bundled sample raster
(``sample-data/sample_imagery.tif``): EPSG:32632, ~0.5 m/px, 3 bands. It is
skipped when rasterio is unavailable.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from apps.imagery.providers import (
    ImageryProviderRegistry,
    UploadedRasterProvider,
    build_default_registry,
)

from .conftest import SAMPLE_TIF

rasterio = pytest.importorskip("rasterio")


@pytest.mark.skipif(not SAMPLE_TIF.is_file(), reason="bundled sample raster missing")
def test_read_metadata_of_sample_raster(tmp_path: Path, settings: Any) -> None:
    """UploadedRasterProvider reports the sample raster's real metadata."""
    settings.MEDIA_ROOT = tmp_path
    from common.storage import FilesystemStorage

    storage = FilesystemStorage(root=tmp_path)
    storage.save("scene.tif", SAMPLE_TIF.read_bytes())

    provider = UploadedRasterProvider(storage=storage)
    meta = provider.read_metadata("scene.tif")

    assert meta.crs == "EPSG:32632"
    assert meta.bands == 3
    assert meta.resolution_m == pytest.approx(0.5, abs=1e-6)
    assert meta.width == 512
    assert meta.height == 512
    assert len(meta.checksum) == 64


def test_default_registry_lists_uploaded_raster() -> None:
    """The default registry exposes the uploaded-raster provider only."""
    registry = build_default_registry()
    caps = {c.name: c for c in registry.available()}

    assert "uploaded_raster" in caps
    assert caps["uploaded_raster"].supports_upload is True
    assert caps["uploaded_raster"].available is True


def test_registry_get_unknown_raises() -> None:
    """Requesting an unregistered provider raises NotFoundError."""
    from common.errors import NotFoundError

    registry = ImageryProviderRegistry()
    with pytest.raises(NotFoundError):
        registry.get("does_not_exist")
