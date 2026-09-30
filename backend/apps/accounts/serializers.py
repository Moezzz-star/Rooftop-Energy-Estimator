"""DRF serializers for the accounts app.

Serializers validate and shape data only; they contain no business logic
(code-architecture §6). Registration/authentication decisions live in
:class:`apps.accounts.services.AccountService`.
"""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer[User]):
    """Public representation of a user (no password or permission internals)."""

    class Meta:
        model = User
        fields = ["id", "email", "is_active", "is_staff", "date_joined", "created_at"]
        read_only_fields = fields


class RegisterSerializer(serializers.Serializer[dict[str, Any]]):
    """Validate registration input (shape only; uniqueness enforced in service)."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class LoginSerializer(serializers.Serializer[dict[str, Any]]):
    """Validate login input (email + password)."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class LogoutSerializer(serializers.Serializer[dict[str, Any]]):
    """Validate logout input (the refresh token to invalidate)."""

    refresh = serializers.CharField()
