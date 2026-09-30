"""Unit tests for :class:`ModelRegistryService`.

Checksum tests run without a database (pure hashing). Selection-logic tests
touch the ORM and are marked ``django_db``.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from apps.ml_models.models import MLModelVersion, ModelStatus
from apps.ml_models.services import ModelRegistryService
from common.errors import InfrastructureError, NotFoundError


def test_verify_checksum_matches(tmp_path: Path) -> None:
    """A matching artifact returns the computed digest."""
    artifact = tmp_path / "model.bin"
    artifact.write_bytes(b"weights")
    expected = hashlib.sha256(b"weights").hexdigest()
    version = MLModelVersion(name="m", version="1", checksum=expected)

    service = ModelRegistryService(model_path=str(artifact))
    assert service.verify_checksum(version) == expected


def test_verify_checksum_mismatch_raises(tmp_path: Path) -> None:
    """A digest mismatch raises :class:`InfrastructureError`."""
    artifact = tmp_path / "model.bin"
    artifact.write_bytes(b"weights")
    version = MLModelVersion(name="m", version="1", checksum="deadbeef")

    service = ModelRegistryService(model_path=str(artifact))
    with pytest.raises(InfrastructureError):
        service.verify_checksum(version)


def test_verify_checksum_missing_file_raises(tmp_path: Path) -> None:
    """A missing artifact raises :class:`InfrastructureError`."""
    version = MLModelVersion(name="m", version="1", checksum="abc")
    service = ModelRegistryService(model_path=str(tmp_path / "absent.bin"))
    with pytest.raises(InfrastructureError):
        service.verify_checksum(version)


def test_verify_checksum_unconfigured_path_raises() -> None:
    """An empty configured path raises :class:`InfrastructureError`."""
    version = MLModelVersion(name="m", version="1", checksum="abc")
    service = ModelRegistryService(model_path="")
    with pytest.raises(InfrastructureError):
        service.verify_checksum(version)


@pytest.mark.django_db
def test_active_prefers_production() -> None:
    """``active`` returns the production version over registered ones."""
    MLModelVersion.objects.create(name="unet", version="0.9", status=ModelStatus.REGISTERED)
    prod = MLModelVersion.objects.create(name="unet", version="1.0", status=ModelStatus.PRODUCTION)
    service = ModelRegistryService()
    assert service.active().pk == prod.pk


@pytest.mark.django_db
def test_active_falls_back_to_latest_registered() -> None:
    """Without a production version, the newest registered one is returned."""
    MLModelVersion.objects.create(name="unet", version="0.8", status=ModelStatus.CANDIDATE)
    newest = MLModelVersion.objects.create(
        name="unet", version="0.9", status=ModelStatus.REGISTERED
    )
    service = ModelRegistryService()
    assert service.active().pk == newest.pk


@pytest.mark.django_db
def test_active_raises_when_none() -> None:
    """``active`` raises :class:`NotFoundError` when nothing is registered."""
    service = ModelRegistryService()
    with pytest.raises(NotFoundError):
        service.active()


@pytest.mark.django_db
def test_get_or_create_default_is_idempotent() -> None:
    """The canonical default is created once and reused thereafter."""
    first = ModelRegistryService.get_or_create_default()
    second = ModelRegistryService.get_or_create_default()
    assert first.pk == second.pk
    assert first.name == "unet_buildings"
    assert first.version == "1.0.0"
    assert first.status == ModelStatus.PRODUCTION
    assert MLModelVersion.objects.filter(name="unet_buildings").count() == 1


@pytest.mark.django_db
def test_get_by_id_and_not_found() -> None:
    """``get`` returns by id and raises for unknown ids."""
    version = MLModelVersion.objects.create(name="unet", version="1.0")
    service = ModelRegistryService()
    assert service.get(str(version.pk)).pk == version.pk
    with pytest.raises(NotFoundError):
        service.get("00000000-0000-0000-0000-000000000000")
