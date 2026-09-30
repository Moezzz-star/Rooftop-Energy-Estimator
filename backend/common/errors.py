"""Domain error hierarchy for the Rooftop Energy Estimator.

Services raise these framework-agnostic errors; the DRF exception handler
(``common.exception_handler``) maps each to the consistent API envelope
``{"error": {"code", "message", "details"}}`` with the correct HTTP status.

Infrastructure/library failures (rasterio, pvlib, storage, boto3) MUST be
caught at the boundary and re-raised as ``InfrastructureError`` so raw
third-party exceptions never leak to the API surface.
"""

from __future__ import annotations

from typing import Any


class DomainError(Exception):
    """Base class for all domain errors.

    Attributes:
        code: Stable machine-readable error code (screaming snake case).
        message: Human-readable, user-safe description (no PII/secrets).
        details: Optional structured context (e.g. field-level errors).
        http_status: HTTP status the API layer should return.
    """

    code: str = "domain_error"
    http_status: int = 400

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        details: dict[str, Any] | None = None,
        http_status: int | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        self.details: dict[str, Any] = details or {}
        if http_status is not None:
            self.http_status = http_status

    def to_envelope(self) -> dict[str, Any]:
        """Return the error serialized as the standard API envelope body."""
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            }
        }


class ValidationError(DomainError):
    """Input failed a domain validation rule."""

    code = "validation_error"
    http_status = 400


class NotFoundError(DomainError):
    """A requested resource does not exist or is not visible to the caller."""

    code = "not_found"
    http_status = 404


class ConflictError(DomainError):
    """The request conflicts with current resource state (e.g. duplicate key)."""

    code = "conflict"
    http_status = 409


class PermissionDeniedError(DomainError):
    """The caller is authenticated but not allowed to perform the action."""

    code = "permission_denied"
    http_status = 403


class InfrastructureError(DomainError):
    """An external dependency (storage, DB, library) failed.

    Used to wrap third-party exceptions at the boundary so callers see a
    stable domain error instead of an implementation-specific one.
    """

    code = "infrastructure_error"
    http_status = 503
