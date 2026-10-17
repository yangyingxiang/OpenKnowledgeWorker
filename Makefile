# Common developer tasks. Run `make help` for a list.
PY ?= python3
VENV := backend/.venv
BIN := $(VENV)/bin

.PHONY: help up down install db seed backend frontend test lint format diagrams

help:  ## Show this help
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  %-10s %s\n", $$1, $$2}'

up:  ## Start everything with Docker (db, backend, frontend)
	docker compose up --build

down:  ## Stop the Docker stack
	docker compose down

install:  ## Install backend (virtualenv) and frontend dependencies
	$(PY) -m venv $(VENV)
	$(BIN)/pip install -r backend/requirements-dev.txt
	cd frontend && pnpm install
	$(BIN)/pre-commit install

db:  ## Apply database migrations
	cd backend && ../$(BIN)/alembic upgrade head

seed:  ## Load the bundled domain packs (examples/)
	cd backend && ../$(BIN)/python seed.py

backend:  ## Run the API on http://localhost:5003
	cd backend && ../$(BIN)/python run.py

frontend:  ## Run the web app on http://localhost:3000
	cd frontend && pnpm dev

test:  ## Run all tests
	cd backend && ../$(BIN)/pytest
	cd examples/mortgage-income-verification/reference_engine && ../../../$(BIN)/pytest
	cd frontend && pnpm test

lint:  ## Lint and check formatting
	$(BIN)/ruff check .
	$(BIN)/ruff format --check .
	cd frontend && pnpm lint && pnpm format:check

format:  ## Auto-format Python and TypeScript
	$(BIN)/ruff check --fix .
	$(BIN)/ruff format .
	cd frontend && pnpm format

diagrams:  ## Re-render docs/diagrams/*.mmd to PNG (needs Node.js)
	for f in docs/diagrams/*.mmd; do npx -y @mermaid-js/mermaid-cli@11.4.2 -i $$f -o $${f%.mmd}.png -s 2 -b white; done
