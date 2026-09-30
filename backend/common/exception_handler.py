"""DRF exception handler mapping errors to the consistent API envelope.

All API errors are returned as ``{"error": {"code", "message", "details"}}``
(code-architecture §6). This handler maps:

* :class:`common.errors.DomainError` subclasses -> their declared code/status;
* DRF/Django exceptions (``ValidationError``, ``NotAuthenticated``,
  ``PermissionDenied``, ``Http404`` etc.) -> the equivalent envelope;
* anything else -> a generic 500 (details suppressed, never leaks internals).

Errors are logged with request context before the response is built.
"""

from __future__ import annotations

from typing import Any

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import exceptions as drf_exceptions
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_default_handler

from common.errors import (
    DomainError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from common.logging import get_logger

logger = get_logger("api.errors")


def _envelope(code: str, message: str, details: Any) -> dict[str, Any]:
    """Build the standard error envelope body."""
    return {"error": {"code": code, "message": message, "details": details or {}}}


def _normalize_domain_error(exc: Exception) -> DomainError | None:
    """Translate framework exceptions into domain errors where applicable."""
    if isinstance(exc, DomainError):
        return exc
    if isinstance(exc, Http404):
        return NotFoundError("The requested resource was not found.")
    if isinstance(exc, DjangoPermissionDenied):
        return PermissionDeniedError("You do not have permission to perform this action.")
    return None


def drf_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """Return an envelope :class:`~rest_framework.response.Response` for ``exc``.

    Args:
        exc: The raised exception.
        context: DRF handler context (contains ``request`` and ``view``).

    Returns:
        A DRF ``Response`` with the error envelope, or ``None`` to defer to
        the default behaviour (should not normally happen).
    """
    request = context.get("request")
    trace_id = _trace_id(request)

    domain_exc = _normalize_domain_error(exc)
    if domain_exc is not None:
        return _handle_domain_error(domain_exc, trace_id)

    if isinstance(exc, drf_exceptions.APIException):
        return _handle_drf_error(exc, trace_id)

    # Fall back to DRF for anything it recognises (rare after the checks above).
    response = drf_default_handler(exc, context)
    if response is not None:
        logger.warning(
            "Unmapped API exception handled by DRF default",
            extra={"trace_id": trace_id, "exc_type": type(exc).__name__},
        )
        response.data = _envelope("error", str(exc), getattr(response, "data", None))
        return response

    # Truly unexpected: log full context, return opaque 500.
    logger.error(
        "Unhandled server error",
        exc_info=exc,
        extra={"trace_id": trace_id, "exc_type": type(exc).__name__},
    )
    return Response(
        _envelope("internal_error", "An unexpected error occurred.", {}),
        status=500,
    )


def _handle_domain_error(exc: DomainError, trace_id: str | None) -> Response:
    """Serialize a domain error to its envelope response."""
    logger.warning(
        "Domain error",
        extra={
            "trace_id": trace_id,
            "code": exc.code,
            "http_status": exc.http_status,
        },
    )
    return Response(exc.to_envelope(), status=exc.http_status)


def _handle_drf_error(exc: drf_exceptions.APIException, trace_id: str | None) -> Response:
    """Map a DRF ``APIException`` to the envelope."""
    code, message, details = _describe_drf_exception(exc)
    logger.warning(
        "DRF API exception",
        extra={"trace_id": trace_id, "code": code, "http_status": exc.status_code},
    )
    return Response(_envelope(code, message, details), status=exc.status_code)


def _describe_drf_exception(
    exc: drf_exceptions.APIException,
) -> tuple[str, str, Any]:
    """Extract (code, message, details) from a DRF exception."""
    mapping: dict[type[drf_exceptions.APIException], str] = {
        drf_exceptions.ValidationError: ValidationError.code,
        drf_exceptions.NotAuthenticated: "not_authenticated",
        drf_exceptions.AuthenticationFailed: "authentication_failed",
        drf_exceptions.PermissionDenied: PermissionDeniedError.code,
        drf_exceptions.NotFound: NotFoundError.code,
        drf_exceptions.MethodNotAllowed: "method_not_allowed",
        drf_exceptions.Throttled: "throttled",
        drf_exceptions.ParseError: ValidationError.code,
    }
    code = mapping.get(type(exc), getattr(exc, "default_code", "error"))

    if isinstance(exc, drf_exceptions.ValidationError):
        # DRF validation detail is a structured dict/list of field errors.
        return code, "Validation failed.", exc.detail
    return code, str(exc.detail), {}


def _trace_id(request: Any) -> str | None:
    """Best-effort extraction of a correlation id from request headers."""
    if request is None:
        return None
    headers = getattr(request, "headers", {})
    return headers.get("X-Trace-Id") or headers.get("X-Request-Id")
