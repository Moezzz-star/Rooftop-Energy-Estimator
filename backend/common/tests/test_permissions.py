"""Tests for :func:`common.permissions.resolve_owner` and ``IsOwner``.

Uses lightweight stand-in objects (no ORM) to exercise the ownership-chain
walk: ``obj.owner`` / ``obj.project.owner`` / ``obj.analysis.project.owner``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from common.permissions import IsOwner, resolve_owner


@dataclass
class FakeUser:
    pk: int
    is_authenticated: bool = True


@dataclass
class Project:
    owner: FakeUser


@dataclass
class Analysis:
    project: Project


@dataclass
class Building:
    analysis: Analysis
    owner: Any = None  # no direct owner; resolved via analysis.project.owner


@dataclass
class Request:
    user: Any


@dataclass
class View:
    name: str = field(default="view")


def test_resolve_owner_direct() -> None:
    user = FakeUser(pk=1)
    assert resolve_owner(Project(owner=user)) is user


def test_resolve_owner_via_project() -> None:
    user = FakeUser(pk=2)
    analysis = Analysis(project=Project(owner=user))
    assert resolve_owner(analysis) is user


def test_resolve_owner_via_analysis_project() -> None:
    user = FakeUser(pk=3)
    building = Building(analysis=Analysis(project=Project(owner=user)))
    assert resolve_owner(building) is user


def test_resolve_owner_user_is_self() -> None:
    user = FakeUser(pk=4)
    assert resolve_owner(user) is user


def test_resolve_owner_unresolvable_returns_none() -> None:
    assert resolve_owner(object()) is None


def test_is_owner_grants_matching_user() -> None:
    user = FakeUser(pk=5)
    building = Building(analysis=Analysis(project=Project(owner=user)))
    perm = IsOwner()
    request = Request(user=user)
    assert perm.has_object_permission(request, View(), building) is True  # type: ignore[arg-type]


def test_is_owner_denies_other_user() -> None:
    owner = FakeUser(pk=6)
    other = FakeUser(pk=7)
    building = Building(analysis=Analysis(project=Project(owner=owner)))
    perm = IsOwner()
    request = Request(user=other)
    assert perm.has_object_permission(request, View(), building) is False  # type: ignore[arg-type]


def test_is_owner_denies_anonymous() -> None:
    anon = FakeUser(pk=8, is_authenticated=False)
    project = Project(owner=FakeUser(pk=9))
    perm = IsOwner()
    request = Request(user=anon)
    assert perm.has_permission(request, View()) is False  # type: ignore[arg-type]
    assert perm.has_object_permission(request, View(), project) is False  # type: ignore[arg-type]
