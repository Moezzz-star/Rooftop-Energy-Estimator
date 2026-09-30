"""Pytest fixtures shared across the backend test suite.

Provides an unauthenticated API client, a user factory, a created user, and an
authenticated (JWT) API client. Integration tests that hit the database use
the ``django_db`` marker; pure-unit tests need none of these fixtures.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken


@pytest.fixture
def api_client() -> APIClient:
    """Return an unauthenticated DRF API client."""
    return APIClient()


@pytest.fixture
def user_factory(db: Any) -> Callable[..., Any]:
    """Return a factory that creates and persists users.

    The factory accepts keyword overrides (e.g. ``email``, ``password``);
    sensible defaults are applied and each call produces a unique email.
    """
    model = get_user_model()
    counter = {"n": 0}

    def _create(**overrides: Any) -> Any:
        counter["n"] += 1
        defaults: dict[str, Any] = {
            "email": overrides.pop("email", f"user{counter['n']}@example.com"),
            "password": overrides.pop("password", "pw-test-12345"),
        }
        defaults.update(overrides)
        password = defaults.pop("password")
        user = model(**defaults)
        user.set_password(password)
        user.save()
        return user

    return _create


@pytest.fixture
def user(user_factory: Callable[..., Any]) -> Any:
    """Return a single persisted user."""
    return user_factory()


@pytest.fixture
def auth_client(api_client: APIClient, user: Any) -> APIClient:
    """Return an API client authenticated as ``user`` via a JWT access token."""
    token = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return api_client
