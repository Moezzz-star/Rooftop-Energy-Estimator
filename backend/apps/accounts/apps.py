"""App configuration for the accounts app."""

from __future__ import annotations

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Django application config for :mod:`apps.accounts`."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    label = "accounts"
    verbose_name = "Accounts"
