"""Domain services for the accounts app.

:class:`AccountService` owns user registration and authentication logic. It is
constructed with its dependencies injected (a user manager and an authentication
callable) so it can be unit-tested against test doubles (code-architecture §6).
Views and serializers hold no business logic; they call this service.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from django.contrib.auth import authenticate as django_authenticate
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError

from common.errors import ConflictError, ValidationError
from common.logging import get_logger

logger = get_logger("accounts.service")

# Type alias for Django's ``authenticate(...)`` signature we depend on.
AuthenticateFn = Callable[..., Any | None]


class AccountService:
    """Register and authenticate users.

    Args:
        user_manager: A manager exposing ``create_user`` and a queryset
            (defaults to the active user model's manager).
        authenticate_fn: Callable used to verify credentials (defaults to
            Django's ``authenticate``); injected for testability.
    """

    def __init__(
        self,
        user_manager: Any | None = None,
        authenticate_fn: AuthenticateFn | None = None,
    ) -> None:
        self._users = (
            user_manager if user_manager is not None else get_user_model()._default_manager
        )
        self._authenticate = authenticate_fn or django_authenticate

    def register(self, email: str, password: str, **extra: Any) -> Any:
        """Create a new user after validating uniqueness and password strength.

        Args:
            email: Desired login email (normalized/lowercased by the manager).
            password: Raw password; run through Django's password validators.
            **extra: Optional additional user fields.

        Returns:
            The newly created user instance.

        Raises:
            ConflictError: If the email is already registered.
            ValidationError: If the password fails validation.
        """
        normalized = (email or "").strip().lower()
        if not normalized:
            raise ValidationError("An email address is required.", details={"email": "required"})

        if self._users.filter(email=normalized).exists():
            logger.info("Registration rejected: duplicate email")
            raise ConflictError(
                "An account with this email already exists.",
                details={"email": "already_registered"},
            )

        self._validate_password(password)

        try:
            user = self._users.create_user(email=normalized, password=password, **extra)
        except IntegrityError as exc:  # race: unique constraint hit concurrently
            logger.warning("Registration hit unique constraint on email")
            raise ConflictError(
                "An account with this email already exists.",
                details={"email": "already_registered"},
            ) from exc

        logger.info("User registered", extra={"trace_id": None})
        return user

    def authenticate(self, email: str, password: str) -> Any:
        """Verify credentials and return the matching active user.

        Args:
            email: Login email.
            password: Raw password.

        Returns:
            The authenticated user.

        Raises:
            ValidationError: If credentials are missing or invalid.
        """
        normalized = (email or "").strip().lower()
        if not normalized or not password:
            raise ValidationError("Email and password are required.")

        user = self._authenticate(username=normalized, password=password)
        if user is None:
            logger.info("Authentication failed: invalid credentials")
            raise ValidationError(
                "Invalid email or password.",
                code="authentication_failed",
                http_status=401,
            )
        logger.info("User authenticated")
        return user

    def _validate_password(self, password: str) -> None:
        """Run Django's configured password validators, mapping failures."""
        try:
            validate_password(password)
        except DjangoValidationError as exc:
            raise ValidationError(
                "Password does not meet the security requirements.",
                details={"password": list(exc.messages)},
            ) from exc
