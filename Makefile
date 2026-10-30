# ==================================================================
# NOCTRA - developer commands
#
# Usage:
#   make                     list available commands
#   make run                 start the development server
#
# GNU Make is required. On Windows, run these from Git Bash.
# ==================================================================

.DEFAULT_GOAL := help
SHELL := /bin/bash

ifeq ($(OS),Windows_NT)
PYTHON ?= venv/Scripts/python.exe
PYTHON_BOOTSTRAP ?= python
else
PYTHON ?= venv/bin/python
PYTHON_BOOTSTRAP ?= python3
endif

HOST ?= 127.0.0.1
PORT ?= 8000
DB_NAME ?= NOCTRADB
TEST_DB_NAME ?= NOCTRADB_test
message ?=

COMPOSE ?= docker compose
COMPOSE_ENV ?= .env.docker
COMPOSE_CMD = $(COMPOSE) --env-file $(COMPOSE_ENV)


.PHONY: help venv install run migrate migrate-check migrate-sql revision \
        downgrade seed seed-settings superuser db-create test-db wait-db \
        test test-unit test-integration test-cov check clean \
        docker-env docker-config docker-build docker-up docker-down \
        docker-logs docker-ps docker-migrate docker-seed docker-superuser \
        docker-shell


help: ## Show this help
	@awk 'BEGIN {FS = ":.*## "; printf "\nNOCTRA - available commands\n\n"} \
		/^[a-zA-Z0-9_.-]+:.*## / {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' \
		$(MAKEFILE_LIST)
	@echo ""


# -- Setup ---------------------------------------------------------

venv:
	$(PYTHON_BOOTSTRAP) -m venv venv

install: venv ## Install dependencies into venv/
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt


# -- Application ---------------------------------------------------

run: ## Start the dev server with autoreload
	$(PYTHON) -m uvicorn app.main:app --reload --host $(HOST) --port $(PORT)


# -- Database & migrations -----------------------------------------

db-create: ## Create the development database
	psql -U postgres -c 'CREATE DATABASE "$(DB_NAME)" OWNER postgres;'

test-db: ## Create the test database used by pytest
	psql -U postgres -c 'CREATE DATABASE "$(TEST_DB_NAME)" OWNER postgres;'

wait-db: ## Block until PostgreSQL accepts connections
	$(PYTHON) -m scripts.wait_for_db

migrate: ## Apply every pending migration
	$(PYTHON) -m alembic upgrade head

migrate-check: ## Build the whole chain on a scratch schema and check drift
	$(PYTHON) -m scripts.migrate_check

migrate-sql: ## Print pending migration SQL without applying it
	$(PYTHON) -m alembic upgrade head --sql

revision: ## Autogenerate a migration: make revision message="..."
	@if [ -z "$(message)" ]; then \
		echo 'usage: make revision message="describe the change"'; \
		exit 1; \
	fi
	$(PYTHON) -m alembic revision --autogenerate -m "$(message)"

downgrade: ## Roll back the most recent migration
	$(PYTHON) -m alembic downgrade -1


# -- Seed data -----------------------------------------------------

seed: ## Seed roles, settings, catalog, employees and pricing
	$(PYTHON) -m scripts.seed_all

seed-settings: ## Seed application settings only
	$(PYTHON) -m scripts.seed_settings

superuser: ## Create a superuser interactively
	$(PYTHON) -m scripts.create_superuser


# -- Tests & checks ------------------------------------------------

test: ## Run the full test suite
	$(PYTHON) -m pytest tests/ -v

test-unit: ## Run unit tests only
	$(PYTHON) -m pytest tests/unit -v

test-integration: ## Run integration tests only
	$(PYTHON) -m pytest tests/integration -v

test-cov: ## Run tests with a coverage report
	$(PYTHON) -m pytest tests/ --cov=app --cov-report=term-missing

check: ## Validate .env and byte-compile app, scripts and tests
	$(PYTHON) -c "from app.core.config import settings; print(f'config OK: {settings.APP_NAME} ({settings.APP_ENV})')"
	$(PYTHON) -m compileall -q app scripts tests

clean: ## Remove Python and test caches
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov .coverage


# -- Containers ----------------------------------------------------

docker-env: ## Create .env.docker with generated secrets (if missing)
	$(PYTHON) -m scripts.gen_docker_env

docker-config: docker-env ## Validate the Compose file
	$(COMPOSE_CMD) config --quiet
	@echo "compose config OK"

docker-build: docker-env ## Build the application image
	$(COMPOSE_CMD) build

docker-up: docker-env ## Build and start db + app + nginx in the background
	$(COMPOSE_CMD) up -d --build --remove-orphans
	@port=$$(grep -E '^HTTP_PORT=' $(COMPOSE_ENV) | cut -d= -f2 | tail -1); \
	 echo "NOCTRA is starting — http://localhost:$${port:-8080}"

docker-down: ## Stop the stack (keeps the database/media volumes)
	$(COMPOSE_CMD) down

docker-ps: ## Show container status and health
	$(COMPOSE_CMD) ps

docker-logs: ## Follow logs from all services
	$(COMPOSE_CMD) logs -f --tail=200

docker-migrate: ## Apply migrations inside the running app container
	$(COMPOSE_CMD) exec app alembic -c /app/alembic.ini upgrade head

docker-seed: ## Seed reference data inside the running app container
	$(COMPOSE_CMD) exec app python -m scripts.seed_all

docker-superuser: ## Create a superuser inside the running app container
	$(COMPOSE_CMD) exec app python -m scripts.create_superuser

docker-shell: ## Open a shell in the app container
	$(COMPOSE_CMD) exec app sh
