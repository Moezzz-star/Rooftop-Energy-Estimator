"""Integration tests for the model registry HTTP endpoints (§4 #22-23)."""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.ml_models.models import MLModelVersion, ModelStatus

pytestmark = pytest.mark.django_db


def test_list_requires_authentication(api_client: APIClient) -> None:
    """Anonymous callers are rejected."""
    response = api_client.get("/api/v1/models/")
    assert response.status_code == 401


def test_list_returns_active_versions_only(auth_client: APIClient) -> None:
    """The list excludes candidate and rolled-back versions."""
    MLModelVersion.objects.create(name="unet", version="1.0", status=ModelStatus.PRODUCTION)
    MLModelVersion.objects.create(name="unet", version="0.9", status=ModelStatus.REGISTERED)
    MLModelVersion.objects.create(name="unet", version="0.1", status=ModelStatus.CANDIDATE)

    response = auth_client.get("/api/v1/models/")
    assert response.status_code == 200
    assert response.data["count"] == 2


def test_detail_returns_model_card(auth_client: APIClient) -> None:
    """Detail returns the card and omits internal checksum."""
    version = MLModelVersion.objects.create(
        name="unet", version="1.0", status=ModelStatus.PRODUCTION, checksum="abc"
    )
    response = auth_client.get(f"/api/v1/models/{version.pk}/")
    assert response.status_code == 200
    assert response.data["name"] == "unet"
    assert "checksum" not in response.data
