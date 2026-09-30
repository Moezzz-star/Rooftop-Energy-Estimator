"""Health endpoints: liveness and readiness.

* ``/health/`` (liveness) — process is up; no dependency checks.
* ``/health/ready/`` (readiness) — best-effort probe of database, Redis,
  storage, and ML model presence. Returns 200 only when all required checks
  pass, otherwise 503 with a per-check breakdown.

Both endpoints are public (no auth) per the API contract (§4).
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.db import connection
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.logging import get_logger
from common.storage import get_storage

logger = get_logger("health")


class LivenessView(APIView):
    """Liveness probe: returns 200 if the process can serve requests."""

    permission_classes = [AllowAny]
    authentication_classes: list[type] = []

    def get(self, request: Request) -> Response:
        """Return a static liveness payload."""
        return Response({"status": "ok"})


class ReadinessView(APIView):
    """Readiness probe: verifies critical dependencies are reachable."""

    permission_classes = [AllowAny]
    authentication_classes: list[type] = []

    def get(self, request: Request) -> Response:
        """Run all dependency checks and aggregate the result."""
        checks: dict[str, bool] = {
            "database": _check_database(),
            "redis": _check_redis(),
            "storage": _check_storage(),
            "model": _check_model(),
        }
        # Model presence is best-effort and does not fail readiness.
        required_ok = all(v for k, v in checks.items() if k != "model")
        status_code = 200 if required_ok else 503
        if not required_ok:
            logger.warning("Readiness check failed", extra={"checks": checks})
        return Response(
            {"status": "ready" if required_ok else "not_ready", "checks": checks},
            status=status_code,
        )


def _check_database() -> bool:
    """Return whether a trivial DB query succeeds."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return True
    except Exception:
        logger.warning("Database readiness check failed")
        return False


def _check_redis() -> bool:
    """Return whether the Celery/Redis broker responds to a ping."""
    url = getattr(settings, "REDIS_URL", "")
    if not url or url.startswith("memory://"):
        return True
    try:
        import redis  # local import keeps module importable without redis

        client: Any = redis.Redis.from_url(url, socket_connect_timeout=1)
        return bool(client.ping())
    except Exception:
        logger.warning("Redis readiness check failed")
        return False


def _check_storage() -> bool:
    """Return whether the storage backend can be constructed."""
    try:
        get_storage()
        return True
    except Exception:
        logger.warning("Storage readiness check failed")
        return False


def _check_model() -> bool:
    """Return whether the ML model artifact is present (best-effort)."""
    from pathlib import Path

    path = getattr(settings, "ML_MODEL_PATH", "")
    if not path:
        return False
    return Path(path).is_file()
