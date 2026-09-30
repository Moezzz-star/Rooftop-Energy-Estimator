"""Tests for the domain error hierarchy and its envelope serialization."""

from __future__ import annotations

import pytest

from common.errors import (
    ConflictError,
    DomainError,
    InfrastructureError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)


def test_domain_error_defaults_to_envelope() -> None:
    err = DomainError("something went wrong")
    envelope = err.to_envelope()
    assert envelope == {
        "error": {
            "code": "domain_error",
            "message": "something went wrong",
            "details": {},
        }
    }
    assert err.http_status == 400


@pytest.mark.parametrize(
    ("cls", "code", "status"),
    [
        (ValidationError, "validation_error", 400),
        (NotFoundError, "not_found", 404),
        (ConflictError, "conflict", 409),
        (PermissionDeniedError, "permission_denied", 403),
        (InfrastructureError, "infrastructure_error", 503),
    ],
)
def test_subclass_codes_and_status(cls: type[DomainError], code: str, status: int) -> None:
    err = cls("boom", details={"field": "x"})
    assert err.code == code
    assert err.http_status == status
    assert err.to_envelope()["error"]["details"] == {"field": "x"}


def test_code_and_status_overridable() -> None:
    err = ValidationError("bad", code="custom_code", http_status=422)
    assert err.code == "custom_code"
    assert err.http_status == 422
    assert err.to_envelope()["error"]["code"] == "custom_code"
