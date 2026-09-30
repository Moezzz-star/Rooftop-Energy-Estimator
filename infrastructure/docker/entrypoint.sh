#!/usr/bin/env bash
# =============================================================================
# entrypoint.sh — shared entrypoint for api / worker / beat containers.
# Idempotent: safe to run repeatedly. Optional migrations/collectstatic are
# gated behind env flags so only ONE service (the api) performs them.
# All real work is delegated to the container CMD via `exec "$@"`.
# =============================================================================
set -euo pipefail

MANAGE_PY="/app/backend/manage.py"

# Optionally apply DB migrations before starting (set RUN_MIGRATIONS=1).
if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
    echo "[entrypoint] applying database migrations..."
    python "${MANAGE_PY}" migrate --noinput
fi

# Optionally collect static assets (set RUN_COLLECTSTATIC=1).
if [ "${RUN_COLLECTSTATIC:-0}" = "1" ]; then
    echo "[entrypoint] collecting static files..."
    python "${MANAGE_PY}" collectstatic --noinput
fi

echo "[entrypoint] starting: $*"
exec "$@"
