"""Tests for :class:`common.storage.FilesystemStorage` (pure, no database)."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from common.errors import InfrastructureError, NotFoundError
from common.storage import FilesystemStorage


@pytest.fixture
def storage(tmp_path: Path) -> FilesystemStorage:
    return FilesystemStorage(root=tmp_path)


def test_save_and_read_bytes_roundtrip(storage: FilesystemStorage) -> None:
    key = "analyses/abc/rasters/scene.bin"
    payload = b"hello rooftop"
    assert storage.save(key, payload) == key
    assert storage.exists(key) is True
    assert storage.read_bytes(key) == payload


def test_save_stream(storage: FilesystemStorage, tmp_path: Path) -> None:
    source = tmp_path / "src.bin"
    source.write_bytes(b"streamed-content")
    with source.open("rb") as fh:
        storage.save("out/streamed.bin", fh)
    assert storage.read_bytes("out/streamed.bin") == b"streamed-content"


def test_checksum_matches_sha256(storage: FilesystemStorage) -> None:
    payload = b"checksum me"
    storage.save("k.bin", payload)
    assert storage.checksum("k.bin") == hashlib.sha256(payload).hexdigest()


def test_open_missing_raises_not_found(storage: FilesystemStorage) -> None:
    with pytest.raises(NotFoundError):
        storage.open("does/not/exist.bin")


def test_delete_is_idempotent(storage: FilesystemStorage) -> None:
    storage.save("temp.bin", b"x")
    storage.delete("temp.bin")
    storage.delete("temp.bin")  # no error on second delete
    assert storage.exists("temp.bin") is False


def test_copy_and_list(storage: FilesystemStorage) -> None:
    storage.save("src/a.bin", b"a")
    storage.copy("src/a.bin", "dst/a.bin")
    assert storage.read_bytes("dst/a.bin") == b"a"
    listed = set(storage.list("src"))
    assert "src/a.bin" in listed


def test_copy_missing_source_raises(storage: FilesystemStorage) -> None:
    with pytest.raises(NotFoundError):
        storage.copy("nope.bin", "dst.bin")


def test_path_traversal_rejected(storage: FilesystemStorage) -> None:
    with pytest.raises(InfrastructureError):
        storage.save("../escape.bin", b"x")
