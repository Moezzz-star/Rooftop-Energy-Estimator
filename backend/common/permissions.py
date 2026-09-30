"""Object-level ownership permission.

Enforces the ``User -> Project -> Analysis -> ...`` ownership chain (DEC-08).
Every domain resource ultimately resolves to an owning :class:`User`; this
module walks the chain and compares against ``request.user``.
"""

from __future__ import annotations

from typing import Any

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

# Attribute names checked, in order, when resolving an object's owner.
_OWNER_ATTRS: tuple[str, ...] = ("owner",)
_PARENT_ATTRS: tuple[str, ...] = ("project", "analysis", "building", "job", "user")


def resolve_owner(obj: Any) -> Any | None:
    """Resolve the owning ``User`` for a domain object.

    Walks the ownership chain: an object may expose ``owner`` directly (e.g.
    ``Project``) or reach it through a parent relation such as ``project`` or
    ``analysis`` (e.g. ``obj.analysis.project.owner``). A bounded traversal
    prevents infinite loops on unexpected graphs.

    Args:
        obj: A model instance, or a ``User`` itself.

    Returns:
        The owning ``User`` instance, or ``None`` if it cannot be resolved.
    """
    # A User is its own owner.
    if _looks_like_user(obj):
        return obj

    current = obj
    for _ in range(6):  # ownership chain is at most a few hops deep
        if current is None:
            return None
        owner = _direct_owner(current)
        if owner is not None:
            return owner
        current = _next_parent(current)
    return None


def _direct_owner(obj: Any) -> Any | None:
    """Return ``obj.owner`` if present and non-null."""
    for attr in _OWNER_ATTRS:
        owner = getattr(obj, attr, None)
        if owner is not None:
            return owner
    return None


def _next_parent(obj: Any) -> Any | None:
    """Return the next parent object in the ownership chain, if any."""
    for attr in _PARENT_ATTRS:
        parent = getattr(obj, attr, None)
        if parent is not None:
            return parent
    return None


def _looks_like_user(obj: Any) -> bool:
    """Heuristically detect a User instance without importing the model."""
    return hasattr(obj, "is_authenticated") and hasattr(obj, "pk")


class IsOwner(BasePermission):
    """Grant access only when the request user owns the object.

    View-level access still requires authentication (enforced by the default
    ``IsAuthenticated`` permission); this class adds the object-level check.
    """

    message = "You do not have permission to access this resource."

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Require an authenticated user for any access."""
        user = getattr(request, "user", None)
        return bool(user and user.is_authenticated)

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        """Return ``True`` when ``request.user`` owns ``obj``."""
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        owner = resolve_owner(obj)
        if owner is None:
            return False
        return bool(getattr(owner, "pk", None) == getattr(user, "pk", object()))
