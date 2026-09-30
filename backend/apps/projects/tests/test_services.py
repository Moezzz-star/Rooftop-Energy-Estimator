"""Unit tests for :class:`apps.projects.services.ProjectService`.

The ``create`` empty-name guard runs without a database; persistence-dependent
behaviour is covered by the DB-backed API tests.
"""

from __future__ import annotations

import pytest

from apps.projects.services import ProjectService
from common.errors import ValidationError


def test_create_empty_name_raises_validation() -> None:
    service = ProjectService()
    with pytest.raises(ValidationError):
        service.create(owner=object(), name="   ")
