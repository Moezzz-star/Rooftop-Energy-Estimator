"""Checksummed download of the production U-Net model (DEC-05).

Downloads ``unet_buildings.keras`` from a configurable URL and verifies its
SHA-256 against an expected value. No secrets are hardcoded: the URL and expected
checksum come from CLI arguments or environment variables.

Environment variables:
    MODEL_URL:        Source URL for the model file.
    MODEL_SHA256:     Expected lowercase hex SHA-256 digest.
    MODEL_OUTPUT:     Optional destination path.

Usage:
    MODEL_URL=https://host/unet_buildings.keras \\
    MODEL_SHA256=<digest> \\
    python scripts/download_model.py --output path/to/unet_buildings.keras
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
import tempfile
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)

_CHUNK = 1 << 20  # 1 MiB
_DEFAULT_OUTPUT = (
    Path(__file__).resolve().parents[1] / "models" / "unet_buildings.keras"
)


class ChecksumMismatchError(RuntimeError):
    """Raised when a downloaded file's SHA-256 does not match the expected value."""


def _sha256(path: Path) -> str:
    """Return the lowercase hex SHA-256 digest of the file at ``path``."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_model(url: str, expected_sha256: str, output: Path) -> Path:
    """Download ``url`` to ``output`` and verify its SHA-256.

    Args:
        url: Source URL for the model file.
        expected_sha256: Expected lowercase hex SHA-256 digest.
        output: Destination path (parent dirs are created as needed).

    Returns:
        The verified output path.

    Raises:
        ValueError: If ``url`` or ``expected_sha256`` is empty.
        ChecksumMismatchError: If the downloaded digest does not match.
        OSError: If the download or file write fails.
    """
    if not url:
        raise ValueError(
            "No model URL provided. Set MODEL_URL or pass --url. See DEC-05."
        )
    if not expected_sha256:
        raise ValueError(
            "No expected SHA-256 provided. Set MODEL_SHA256 or pass --sha256."
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    expected = expected_sha256.strip().lower()

    logger.info("downloading model", extra={"url": url, "output": str(output)})
    with tempfile.NamedTemporaryFile(
        delete=False, dir=output.parent, suffix=".part"
    ) as tmp:
        tmp_path = Path(tmp.name)
    try:
        with urllib.request.urlopen(url) as response:  # noqa: S310 - configurable URL
            with tmp_path.open("wb") as out:
                while True:
                    chunk = response.read(_CHUNK)
                    if not chunk:
                        break
                    out.write(chunk)

        actual = _sha256(tmp_path)
        if actual != expected:
            raise ChecksumMismatchError(
                f"SHA-256 mismatch for downloaded model: expected {expected}, "
                f"got {actual}. The file was NOT installed."
            )
        tmp_path.replace(output)
        logger.info("model verified and installed", extra={"sha256": actual})
        return output
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download + verify the U-Net model.")
    parser.add_argument("--url", default=os.environ.get("MODEL_URL", ""))
    parser.add_argument("--sha256", default=os.environ.get("MODEL_SHA256", ""))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(os.environ.get("MODEL_OUTPUT", str(_DEFAULT_OUTPUT))),
    )
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    args = _parse_args()
    download_model(args.url, args.sha256, args.output)
