"""Object-level permissions for the analyses app.

Analyses resolve their owner via ``analysis.project.owner`` — the shared
:class:`common.permissions.IsOwner` already walks that chain, so it is
re-exported here for local, explicit use by the views.
"""

from __future__ import annotations

from common.permissions import IsOwner

__all__ = ["IsOwner"]
