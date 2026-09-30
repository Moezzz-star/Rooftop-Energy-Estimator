"""Integration tests for :class:`apps.audit.services.AuditService` (DB-backed)."""

from __future__ import annotations

from typing import Any

import pytest

from apps.audit.models import AuditEvent
from apps.audit.services import AuditService
from apps.projects.models import Project

pytestmark = pytest.mark.django_db


def test_record_denormalizes_actor_email(user: Any) -> None:
    project = Project.objects.create(owner=user, name="Audited")

    event = AuditService().record(
        action="project.created",
        actor=user,
        target=project,
        metadata={"name": project.name},
    )

    assert event.actor_email == user.email
    assert event.target_type == "Project"
    assert event.target_id == str(project.id)
    assert event.metadata == {"name": "Audited"}


def test_event_survives_actor_deletion_via_set_null(user_factory: Any) -> None:
    actor = user_factory(email="temp-actor@example.com")
    event = AuditService().record(action="user.login", actor=actor)
    event_id = event.id

    actor.delete()

    persisted = AuditEvent.objects.get(id=event_id)
    assert persisted.actor is None
    assert persisted.actor_email == "temp-actor@example.com"


def test_record_handles_missing_actor_and_target() -> None:
    event = AuditService().record(action="system.startup")

    assert event.actor is None
    assert event.actor_email == ""
    assert event.target_type == ""
    assert event.target_id == ""
    assert event.metadata == {}


def test_audit_event_has_no_cascade_fk_to_domain() -> None:
    """AuditEvent is retained independently (DEC-03): only a SET_NULL actor FK.

    Guards against a regression where a CASCADE FK to Project/Analysis would
    cause audit events to be deleted alongside the data they describe.
    """
    from django.db import models as dj_models

    fk_names = {
        f.name
        for f in AuditEvent._meta.get_fields()
        if isinstance(f, dj_models.ForeignKey)
    }
    assert fk_names == {"actor"}

    actor_field = AuditEvent._meta.get_field("actor")
    on_delete = getattr(actor_field.remote_field, "on_delete", None)
    assert on_delete is dj_models.SET_NULL
