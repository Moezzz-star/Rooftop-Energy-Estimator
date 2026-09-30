"""Unit tests for the untrusted-upload raster validator (spec §11).

These are pure validator tests: they build tiny GeoTIFFs on disk with rasterio
and assert the security rules (size, pixel cap, CRS, bands, dtype, bounds,
malformed content). No database is required.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from apps.imagery.validators import RasterUploadLimits, RasterUploadValidator
from common.errors import ValidationError

from .conftest import write_geotiff

rasterio = pytest.importorskip("rasterio")


def _checksum(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_validate_size_rejects_oversized() -> None:
    """A declared size above the limit is rejected before storage."""
    validator = RasterUploadValidator(RasterUploadLimits(max_upload_bytes=10))
    with pytest.raises(ValidationError) as exc:
        validator.validate_size(11)
    assert exc.value.code == "imagery_too_large"


def test_validate_size_allows_within_limit_and_none() -> None:
    """Sizes within the limit (and unknown sizes) pass the pre-store check."""
    validator = RasterUploadValidator(RasterUploadLimits(max_upload_bytes=10))
    validator.validate_size(10)
    validator.validate_size(None)


def test_validate_raster_rejects_non_raster(tmp_path: Path) -> None:
    """A malformed/non-raster file is rejected as unreadable."""
    bad = tmp_path / "not_a_raster.tif"
    bad.write_bytes(b"definitely not a geotiff")
    validator = RasterUploadValidator(RasterUploadLimits())
    checksum = _checksum(bad)
    with pytest.raises(ValidationError) as exc:
        validator.validate_raster(str(bad), checksum=checksum)
    assert exc.value.code == "imagery_unreadable"


def test_validate_raster_rejects_missing_crs(tmp_path: Path) -> None:
    """A raster without a CRS is rejected."""
    path = write_geotiff(tmp_path / "no_crs.tif", crs=None)
    validator = RasterUploadValidator(RasterUploadLimits())
    checksum = _checksum(path)
    with pytest.raises(ValidationError) as exc:
        validator.validate_raster(str(path), checksum=checksum)
    assert exc.value.code == "imagery_missing_crs"


def test_validate_raster_rejects_too_few_bands(tmp_path: Path) -> None:
    """A raster with fewer than three bands is rejected."""
    path = write_geotiff(tmp_path / "one_band.tif", bands=1)
    validator = RasterUploadValidator(RasterUploadLimits())
    checksum = _checksum(path)
    with pytest.raises(ValidationError) as exc:
        validator.validate_raster(str(path), checksum=checksum)
    assert exc.value.code == "imagery_too_few_bands"


def test_validate_raster_rejects_pixel_cap(tmp_path: Path) -> None:
    """A raster exceeding the pixel cap is rejected from the header alone."""
    path = write_geotiff(tmp_path / "big.tif", width=8, height=8, bands=3)
    validator = RasterUploadValidator(RasterUploadLimits(max_pixels=1))
    checksum = _checksum(path)
    with pytest.raises(ValidationError) as exc:
        validator.validate_raster(str(path), checksum=checksum)
    assert exc.value.code == "imagery_too_many_pixels"


def test_validate_raster_rejects_unsupported_dtype(tmp_path: Path) -> None:
    """A dtype outside the supported set is rejected."""
    path = write_geotiff(tmp_path / "u8.tif", dtype="uint8")
    validator = RasterUploadValidator(
        RasterUploadLimits(supported_dtypes=frozenset({"uint16"}))
    )
    checksum = _checksum(path)
    with pytest.raises(ValidationError) as exc:
        validator.validate_raster(str(path), checksum=checksum)
    assert exc.value.code == "imagery_unsupported_dtype"


def test_validate_raster_accepts_valid_and_returns_metadata(tmp_path: Path) -> None:
    """A valid raster passes and yields full metadata incl. nodata/dtype/transform."""
    path = write_geotiff(tmp_path / "ok.tif", bands=3, dtype="uint8", nodata=0.0)
    validator = RasterUploadValidator(RasterUploadLimits())
    meta = validator.validate_raster(str(path), checksum=_checksum(path))

    assert meta.crs == "EPSG:32632"
    assert meta.bands == 3
    assert meta.width == 8
    assert meta.height == 8
    assert meta.dtype == "uint8"
    assert meta.nodata == 0.0
    assert len(meta.transform) == 6
    assert meta.resolution_m == pytest.approx(0.5, abs=1e-6)
