"""Django admin registration for the audit app (read-only)."""

from __future__ import annotations

from typing import Any

from django.contrib import admin
from django.http import HttpRequest

from .models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """Read-only admin view of the immutable audit log."""

    list_display = ["at", "action", "actor_email", "target_type", "target_id"]
    list_filter = ["action", "target_type", "at"]
    search_fields = ["actor_email", "target_id", "action"]
    readonly_fields = [
        "id",
        "action",
        "actor",
        "actor_email",
        "target_type",
        "target_id",
        "metadata",
        "at",
        "created_at",
        "updated_at",
    ]

    def has_add_permission(self, request: HttpRequest) -> bool:
        """Audit events are never created via the admin."""
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any | None = None) -> bool:
        """Audit events are immutable."""
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any | None = None) -> bool:
        """Audit events are retained independently and not deletable here."""
        return False
