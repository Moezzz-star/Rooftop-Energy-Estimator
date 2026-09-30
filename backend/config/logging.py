"""Structured JSON logging configuration for the Rooftop Energy Estimator.

Emits one JSON object per log record with the fields required by the
observability contract (§6): ``timestamp``, ``level``, ``logger``, ``message``
plus optional correlation fields (``trace_id``, ``analysis_id``, ``job_id``,
``stage``) injected via ``extra=`` on the logging call.

The module is import-safe with no Django dependency so it can be consumed by
``config.settings.*`` at import time.
"""

from __future__ import annotations

import datetime as _dt
import json
import logging
from typing import Any

# Correlation fields that, when supplied via ``extra=``, are promoted to
# top-level keys in the JSON payload.
_CONTEXT_FIELDS: tuple[str, ...] = ("trace_id", "analysis_id", "job_id", "stage")

# Standard ``LogRecord`` attributes that must never be treated as user extras.
_RESERVED_ATTRS: frozenset[str] = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "taskName",
        "thread",
        "threadName",
    }
)


class JSONFormatter(logging.Formatter):
    """Format log records as single-line JSON objects.

    Any non-reserved attribute attached to the record (typically via
    ``logger.info("msg", extra={...})``) is included in the payload, so callers
    may attach arbitrary structured context.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Return the record serialized as a JSON string."""
        payload: dict[str, Any] = {
            "timestamp": _dt.datetime.fromtimestamp(record.created, tz=_dt.UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for field in _CONTEXT_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value

        # Promote any additional user-supplied extras.
        for key, value in record.__dict__.items():
            if key in _RESERVED_ATTRS or key in payload or key.startswith("_"):
                continue
            payload[key] = value

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack_info"] = self.formatStack(record.stack_info)

        return json.dumps(payload, default=str)


def get_logging_config(debug: bool) -> dict[str, Any]:
    """Build a ``logging.config.dictConfig`` dictionary.

    Args:
        debug: When ``True`` the root/console level is ``DEBUG`` and a
            human-readable console formatter is preferred for local work while
            JSON remains available; when ``False`` only JSON is emitted at
            ``INFO``.

    Returns:
        A dictConfig-compatible dictionary.
    """
    level = "DEBUG" if debug else "INFO"
    default_formatter = "console" if debug else "json"

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {"()": "config.logging.JSONFormatter"},
            "console": {
                "format": "%(asctime)s %(levelname)-8s %(name)s: %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": default_formatter,
                "level": level,
            },
        },
        "root": {"handlers": ["console"], "level": level},
        "loggers": {
            "django": {"handlers": ["console"], "level": level, "propagate": False},
            "django.db.backends": {
                "handlers": ["console"],
                "level": "WARNING",
                "propagate": False,
            },
            "celery": {"handlers": ["console"], "level": level, "propagate": False},
            "rooftop": {"handlers": ["console"], "level": level, "propagate": False},
        },
    }
