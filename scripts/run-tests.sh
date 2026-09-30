#!/usr/bin/env bash
# =============================================================================
# run-tests.sh — convenience wrapper to run all quality gates locally via the
# Docker stack, in fail-fast order (fast checks first). Mirrors CI (arch §6).
# Usage: ./scripts/run-tests.sh
# =============================================================================
set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> Ruff lint"
docker compose run --rm -w /app api ruff check backend ml

echo "==> Ruff format check"
docker compose run --rm -w /app api ruff format --check backend ml

echo "==> mypy typecheck"
docker compose run --rm -w /app api mypy backend ml

echo "==> Backend tests (pytest)"
docker compose run --rm -e DJANGO_SETTINGS_MODULE=config.settings.test api pytest

echo "==> Frontend tests (Vitest)"
docker compose run --rm frontend npm run test

echo "All checks passed."
