"""Pytest fixtures for the ``ml`` test-suite.

Ensures the tiny CI U-Net fixture exists (generating it on the fly if missing)
and exposes it to tests that run real inference. Tests requiring TensorFlow are
skipped cleanly when it is not installed.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
_CI_MODEL_PATH = _FIXTURE_DIR / "ci_unet.keras"


def _tensorflow_available() -> bool:
    """Return whether TensorFlow can be imported in this environment."""
    return importlib.util.find_spec("tensorflow") is not None


@pytest.fixture(scope="session")
def ci_model_path() -> Path:
    """Return the path to the tiny CI U-Net model, generating it if missing.

    Skips the requesting test when TensorFlow is unavailable.
    """
    if not _tensorflow_available():
        pytest.skip("TensorFlow not installed; cannot build/load the CI model")
    if not _CI_MODEL_PATH.is_file():
        from scripts.generate_ci_model import main as generate_ci_model

        generate_ci_model(_CI_MODEL_PATH)
    return _CI_MODEL_PATH
