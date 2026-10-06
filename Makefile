# Developer shortcuts. Run `make help` for the list.

BACKEND := backend
VENV := .venv/bin
COMPOSE := docker compose

.DEFAULT_GOAL := help
.PHONY: help up down logs infra install run worker test cov lint format typecheck check migrate revision seed jobs

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

# --- Docker ---------------------------------------------------------------------
up: ## Build and start the whole stack (API, worker, PostgreSQL, Redis)
	$(COMPOSE) up --build -d

down: ## Stop the stack
	$(COMPOSE) down

logs: ## Follow API and worker logs
	$(COMPOSE) logs -f api worker

infra: ## Start only PostgreSQL and Redis (run the API locally)
	$(COMPOSE) up -d db redis

# --- Local development ------------------------------------------------------------
install: ## Create the virtualenv and install dependencies
	cd $(BACKEND) && python3 -m venv .venv && $(VENV)/pip install -e ".[dev]"

run: ## Run the API with auto-reload on http://localhost:8000
	cd $(BACKEND) && $(VENV)/uvicorn app.main:create_app --factory --reload

worker: ## Run the background job scheduler
	cd $(BACKEND) && $(VENV)/python -m app.worker

migrate: ## Apply database migrations
	cd $(BACKEND) && $(VENV)/alembic upgrade head

revision: ## Create a migration: make revision m="add something"
	cd $(BACKEND) && $(VENV)/alembic revision --autogenerate -m "$(m)"

seed: ## Upsert reference data
	cd $(BACKEND) && $(VENV)/python -m app.cli seed

jobs: ## List background jobs
	cd $(BACKEND) && $(VENV)/python -m app.cli list-jobs

# --- Quality ----------------------------------------------------------------------
test: ## Run the test suite (needs `make infra`)
	cd $(BACKEND) && $(VENV)/pytest

cov: ## Run the tests with a coverage report
	cd $(BACKEND) && $(VENV)/pytest --cov=app --cov-report=term-missing

lint: ## Check style and lint rules
	cd $(BACKEND) && $(VENV)/ruff check app tests migrations && $(VENV)/ruff format --check app tests

format: ## Format and auto-fix
	cd $(BACKEND) && $(VENV)/ruff format app tests && $(VENV)/ruff check --fix app tests

typecheck: ## Static type checking (strict mypy)
	cd $(BACKEND) && $(VENV)/mypy app

check: lint typecheck test ## Lint, type check and test
