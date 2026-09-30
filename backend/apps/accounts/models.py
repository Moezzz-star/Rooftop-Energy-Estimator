"""Persistence models for the accounts app.

Defines the custom :class:`User` (email as the identifier, UUID primary key via
:class:`common.models.BaseModel`) and its :class:`UserManager`. This model is
the ownership root of the domain graph (DEC-08): ``User -> Project -> Analysis``.

Models hold persistence and simple invariants only; all domain logic lives in
:mod:`apps.accounts.services` (code-architecture §6).
"""

from __future__ import annotations

from typing import Any, ClassVar

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone

from common.models import BaseModel


class UserManager(BaseUserManager["User"]):
    """Manager creating users keyed on a normalized, required email address.

    Subclasses :class:`BaseUserManager` so authentication backends can call
    ``get_by_natural_key`` (email lookup) and ``normalize_email``.
    """

    use_in_migrations = True

    def _create_user(self, email: str, password: str | None, **extra: Any) -> User:
        """Create, hash-set the password for, and persist a user.

        Args:
            email: Login identifier; must be non-empty.
            password: Raw password (hashed by Django before storage) or ``None``.
            **extra: Additional model field values (e.g. ``is_staff``).

        Returns:
            The persisted :class:`User`.

        Raises:
            ValueError: If ``email`` is empty.
        """
        if not email:
            raise ValueError("An email address is required.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra: Any) -> User:
        """Create a standard (non-staff, non-superuser) user."""
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra)

    def create_superuser(self, email: str, password: str | None = None, **extra: Any) -> User:
        """Create a superuser (staff + superuser flags forced on)."""
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        if extra.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin, BaseModel):
    """Application user identified by a unique email address.

    Inherits a UUID primary key and audit timestamps from
    :class:`common.models.BaseModel`, password/last-login handling from
    :class:`~django.contrib.auth.base_user.AbstractBaseUser`, and the
    permission fields from :class:`~django.contrib.auth.models.PermissionsMixin`.
    There is no ``username``; :attr:`USERNAME_FIELD` is ``email``.
    """

    email = models.EmailField(unique=True, db_index=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = []

    class Meta:
        ordering = ["-date_joined"]
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self) -> str:
        """Return the user's email (safe, non-secret identifier)."""
        return self.email
