# =============================================================================
# Makefile — developer entrypoints for the Rooftop Energy Estimator.
# Run from the repo root. Docker Compose drives the BASE stack (arch §2).
# Application commands (manage.py subcommands, scripts/*.py) are owned by other
# engineers; targets here wire them together.
# =============================================================================

COMPOSE      := docker compose
# Run one-off backend commands with the repo root as workdir (ruff/mypy see
# both `backend` and `ml`); DB/Redis get started via depends_on health gates.
RUN_ROOT     := $(COMPOSE) run --rm -w /app api
RUN_API      := $(COMPOSE) run --rm api
PYTHON       ?= python

.DEFAULT_GOAL := help

.PHONY: help setup dev stop test test-backend test-frontend lint typecheck \
        migrate seed infer-sample build clean

help: ## List available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "} {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

setup: ## Build images, create .env, generate CI model + sample data
	$(COMPOSE) build
	@if [ ! -f .env ]; then cp .env.example .env && echo "created .env from .env.example"; \
		else echo ".env already exists — leaving as-is"; fi
	$(PYTHON) scripts/generate_ci_model.py
	$(PYTHON) scripts/generate_sample_data.py

dev: ## Start the full BASE stack (foreground)
	$(COMPOSE) up

stop: ## Stop and remove the stack containers/network
	$(COMPOSE) down

test: test-backend test-frontend ## Run backend + frontend test suites

test-backend: ## Run backend pytest suite (test settings)
	$(COMPOSE) run --rm -e DJANGO_SETTINGS_MODULE=config.settings.test api pytest

test-frontend: ## Run frontend unit tests (Vitest)
	$(COMPOSE) run --rm frontend npm run test

lint: ## Ruff lint over backend + ml
	$(RUN_ROOT) ruff check backend ml

typecheck: ## mypy static type check over backend + ml
	$(RUN_ROOT) mypy backend ml

migrate: ## Apply database migrations
	$(RUN_API) python manage.py migrate

seed: ## Seed baseline/demo data (management command owned by backend eng)
	$(RUN_API) python manage.py seed

infer-sample: ## Run the deterministic sample analysis end-to-end.
	## Requires the stack to be up (`make dev`) so db/redis/worker are healthy.
	$(RUN_API) python manage.py infer_sample

build: ## Build all images + the frontend production bundle
	$(COMPOSE) build
	$(COMPOSE) run --rm frontend npm run build

clean: ## Remove Python/JS caches, build output and coverage
	find . -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '.pytest_cache' -prune -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '.mypy_cache' -prune -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '.ruff_cache' -prune -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.py[co]' -delete 2>/dev/null || true
	rm -rf dist build htmlcov .coverage coverage.xml frontend/dist 2>/dev/null || true
	@echo "clean complete"
