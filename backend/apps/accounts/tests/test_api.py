"""Integration tests for the accounts API (DB-backed, pytest-django).

Covers registration (hashed password), login token issuance, ``/me/`` auth,
duplicate-email conflict envelope, and anonymous rejection. These require the
PostGIS test database provided by CI/Docker.
"""

from __future__ import annotations

from typing import Any

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

REGISTER_URL = "/api/v1/auth/register/"
LOGIN_URL = "/api/v1/auth/login/"
ME_URL = "/api/v1/me/"


def test_register_creates_user_with_hashed_password(api_client: APIClient) -> None:
    resp = api_client.post(
        REGISTER_URL,
        {"email": "alice@example.com", "password": "s3cure-pw-9021"},
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["user"]["email"] == "alice@example.com"
    assert "access" in resp.data["tokens"]
    assert "refresh" in resp.data["tokens"]

    user = get_user_model().objects.get(email="alice@example.com")
    assert user.password != "s3cure-pw-9021"
    assert user.check_password("s3cure-pw-9021")


def test_register_duplicate_email_returns_409_envelope(
    api_client: APIClient, user_factory: Any
) -> None:
    user_factory(email="dup@example.com", password="s3cure-pw-9021")

    resp = api_client.post(
        REGISTER_URL,
        {"email": "dup@example.com", "password": "s3cure-pw-9021"},
        format="json",
    )
    assert resp.status_code == 409
    assert resp.data["error"]["code"] == "conflict"


def test_login_returns_tokens(api_client: APIClient, user_factory: Any) -> None:
    user_factory(email="bob@example.com", password="s3cure-pw-9021")

    resp = api_client.post(
        LOGIN_URL,
        {"email": "bob@example.com", "password": "s3cure-pw-9021"},
        format="json",
    )
    assert resp.status_code == 200
    assert "access" in resp.data
    assert "refresh" in resp.data


def test_me_requires_auth(api_client: APIClient) -> None:
    resp = api_client.get(ME_URL)
    assert resp.status_code == 401


def test_me_returns_current_user(auth_client: APIClient, user: Any) -> None:
    resp = auth_client.get(ME_URL)
    assert resp.status_code == 200
    assert resp.data["email"] == user.email
    assert resp.data["id"] == str(user.id)
