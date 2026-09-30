"""Unit tests for :class:`apps.accounts.services.AccountService`.

These use in-memory test doubles for the user manager and the authenticate
callable, so they run without a database.
"""

from __future__ import annotations

from typing import Any

import pytest

from apps.accounts.services import AccountService
from common.errors import ConflictError, ValidationError


class _FakeQuerySet:
    def __init__(self, exists: bool) -> None:
        self._exists = exists

    def exists(self) -> bool:
        return self._exists


class _FakeManager:
    """Minimal stand-in for the User model's default manager."""

    def __init__(self, email_taken: bool = False) -> None:
        self.email_taken = email_taken
        self.created: dict[str, Any] | None = None

    def filter(self, **_: Any) -> _FakeQuerySet:
        return _FakeQuerySet(self.email_taken)

    def create_user(self, **kwargs: Any) -> dict[str, Any]:
        self.created = kwargs
        return kwargs


def test_register_creates_user_with_normalized_email() -> None:
    manager = _FakeManager(email_taken=False)
    service = AccountService(user_manager=manager)

    user = service.register(email="  New@Example.COM ", password="s3cure-pw-9021")

    assert user["email"] == "new@example.com"
    assert manager.created is not None


def test_register_duplicate_email_raises_conflict() -> None:
    service = AccountService(user_manager=_FakeManager(email_taken=True))

    with pytest.raises(ConflictError):
        service.register(email="dup@example.com", password="s3cure-pw-9021")


def test_register_empty_email_raises_validation() -> None:
    service = AccountService(user_manager=_FakeManager())

    with pytest.raises(ValidationError):
        service.register(email="", password="s3cure-pw-9021")


def test_register_weak_password_raises_validation() -> None:
    service = AccountService(user_manager=_FakeManager())

    with pytest.raises(ValidationError):
        service.register(email="weak@example.com", password="1")


def test_authenticate_invalid_credentials_raises() -> None:
    service = AccountService(
        user_manager=_FakeManager(),
        authenticate_fn=lambda **_: None,
    )

    with pytest.raises(ValidationError):
        service.authenticate(email="x@example.com", password="wrong")


def test_authenticate_returns_user_on_success() -> None:
    sentinel = object()
    service = AccountService(
        user_manager=_FakeManager(),
        authenticate_fn=lambda **_: sentinel,
    )

    assert service.authenticate(email="x@example.com", password="right") is sentinel
