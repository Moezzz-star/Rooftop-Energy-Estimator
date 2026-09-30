"""Integration tests for the projects API (DB-backed, pytest-django).

Covers ownership scoping, creation (owner = request.user), retrieve/patch/
delete, cross-user isolation (404), filtering and pagination envelope.
"""

from __future__ import annotations

from typing import Any

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.projects.models import Project

pytestmark = pytest.mark.django_db

PROJECTS_URL = "/api/v1/projects/"


def _client_for(user: Any) -> APIClient:
    client = APIClient()
    token = RefreshToken.for_user(user)
    access = token.access_token  # type: ignore[attr-defined]  # simplejwt dynamic attr
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client


def test_create_sets_owner_to_request_user(auth_client: APIClient, user: Any) -> None:
    resp = auth_client.post(PROJECTS_URL, {"name": "Rooftop A", "description": "d"}, format="json")
    assert resp.status_code == 201
    assert resp.data["name"] == "Rooftop A"

    project = Project.objects.get(id=resp.data["id"])
    assert project.owner_id == user.id


def test_create_rejects_blank_name(auth_client: APIClient) -> None:
    resp = auth_client.post(PROJECTS_URL, {"name": "   "}, format="json")
    assert resp.status_code == 400


def test_list_shows_only_own_projects(user_factory: Any) -> None:
    owner = user_factory()
    other = user_factory()
    Project.objects.create(owner=owner, name="Mine")
    Project.objects.create(owner=other, name="Theirs")

    resp = _client_for(owner).get(PROJECTS_URL)
    assert resp.status_code == 200
    names = [row["name"] for row in resp.data["results"]]
    assert names == ["Mine"]


def test_list_is_paginated(auth_client: APIClient) -> None:
    resp = auth_client.get(PROJECTS_URL)
    assert resp.status_code == 200
    for key in ("count", "next", "previous", "results"):
        assert key in resp.data


def test_filter_by_name_and_archived(user_factory: Any) -> None:
    owner = user_factory()
    Project.objects.create(owner=owner, name="Solar North", is_archived=False)
    Project.objects.create(owner=owner, name="Solar South", is_archived=True)
    client = _client_for(owner)

    resp = client.get(PROJECTS_URL, {"name": "north"})
    assert [r["name"] for r in resp.data["results"]] == ["Solar North"]

    resp = client.get(PROJECTS_URL, {"is_archived": "true"})
    assert [r["name"] for r in resp.data["results"]] == ["Solar South"]


def test_retrieve_patch_delete_own_project(user_factory: Any) -> None:
    owner = user_factory()
    project = Project.objects.create(owner=owner, name="Editable")
    client = _client_for(owner)
    detail = f"{PROJECTS_URL}{project.id}/"

    assert client.get(detail).status_code == 200

    resp = client.patch(detail, {"name": "Renamed"}, format="json")
    assert resp.status_code == 200
    assert resp.data["name"] == "Renamed"

    assert client.delete(detail).status_code == 204
    assert not Project.objects.filter(id=project.id).exists()


def test_cross_user_access_is_denied(user_factory: Any) -> None:
    owner = user_factory()
    other = user_factory()
    project = Project.objects.create(owner=owner, name="Private")

    resp = _client_for(other).get(f"{PROJECTS_URL}{project.id}/")
    assert resp.status_code == 404


def test_anonymous_is_rejected(api_client: APIClient) -> None:
    assert api_client.get(PROJECTS_URL).status_code == 401
