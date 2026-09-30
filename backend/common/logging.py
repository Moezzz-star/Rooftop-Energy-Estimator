"""Structured logging helpers for domain and orchestration code.

Provides :func:`get_logger` (namespaced under ``rooftop``) and
:class:`LogContext`, a ``LoggerAdapter`` that injects correlation fields
(``trace_id``, ``analysis_id``, ``job_id``, ``stage``) into every emitted
record so the JSON formatter can promote them to top-level keys.

Domain logic in ``ml/`` stays pure (no logging); logging happens in services
and Celery tasks that own the correlation context.
"""

from __future__ import annotations

import logging
from collections.abc import MutableMapping
from typing import Any

_ROOT_LOGGER_NAME = "rooftop"

# Fields recognised as correlation context; ``None`` values are dropped.
_CONTEXT_KEYS: tuple[str, ...] = ("trace_id", "analysis_id", "job_id", "stage")


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger.

    Args:
        name: A dotted suffix (e.g. ``"jobs.pipeline"``); it is placed under
            the ``rooftop`` root so logging config applies uniformly.

    Returns:
        A configured :class:`logging.Logger`.
    """
    if name == _ROOT_LOGGER_NAME or name.startswith(f"{_ROOT_LOGGER_NAME}."):
        return logging.getLogger(name)
    return logging.getLogger(f"{_ROOT_LOGGER_NAME}.{name}")


class LogContext(logging.LoggerAdapter):  # type: ignore[type-arg]
    """A logger adapter that attaches correlation fields to every record.

    Example:
        >>> log = LogContext(get_logger("jobs"), analysis_id="abc", job_id="j1")
        >>> log.info("stage started", extra={"stage": "VECTORIZE"})
    """

    def __init__(self, logger: logging.Logger, /, **context: Any) -> None:
        cleaned = {k: v for k, v in context.items() if k in _CONTEXT_KEYS and v is not None}
        super().__init__(logger, cleaned)

    def process(
        self, msg: str, kwargs: MutableMapping[str, Any]
    ) -> tuple[str, MutableMapping[str, Any]]:
        """Merge adapter context into the record's ``extra`` mapping."""
        extra = dict(self.extra or {})
        extra.update(kwargs.get("extra") or {})
        kwargs["extra"] = extra
        return msg, kwargs

    def bind(self, **context: Any) -> LogContext:
        """Return a new adapter with additional correlation fields merged in."""
        merged: dict[str, Any] = dict(self.extra or {})
        merged.update(context)
        return LogContext(self.logger, **merged)
