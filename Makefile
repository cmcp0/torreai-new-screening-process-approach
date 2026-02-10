# Screening stack – Docker Compose helpers
# Run `make` or `make help` for targets.

.DEFAULT_GOAL := help

.PHONY: help up up-d down build logs logs-backend logs-frontend ps restart clean up-ollama down-ollama ollama-pull-embed ollama-list-models test test-backend test-backend-unit test-backend-integration test-frontend

DOCKER_COMPOSE = docker compose
PYTHON ?= python
PYTEST ?= $(PYTHON) -m pytest
NPM ?= npm
FRONTEND_DIR ?= apps/frontend

help:
	@echo "Screening stack (Docker Compose)"
	@echo ""
	@echo "  make up          Start all services (foreground)"
	@echo "  make up-d        Start all services (detached)"
	@echo "  make down        Stop and remove containers"
	@echo "  make build       Build backend image"
	@echo "  make ps          List running services"
	@echo "  make logs        Tail logs (all services)"
	@echo "  make logs-backend   Tail backend logs"
	@echo "  make logs-frontend Tail frontend logs"
	@echo "  make restart     Restart all services"
	@echo "  make clean       Down and remove volumes"
	@echo "  make up-ollama   Start stack + Ollama (profile: ollama)"
	@echo "  make ollama-pull-embed Pull required embedding model (nomic-embed-text)"
	@echo "  make ollama-list-models List models available in Ollama container"
	@echo ""
	@echo "Tests"
	@echo "  make test             Run backend + frontend tests"
	@echo "  make test-backend     Run all backend tests"
	@echo "  make test-backend-unit Run backend unit tests"
	@echo "  make test-backend-integration Run backend integration tests"
	@echo "  make test-frontend    Run frontend tests (vitest run)"
	@echo ""
	@echo "URLs (after make up-d): Frontend http://localhost:5173  Backend http://localhost:8000"

up:
	$(DOCKER_COMPOSE) up

up-d:
	$(DOCKER_COMPOSE) up -d

down:
	$(DOCKER_COMPOSE) down

build:
	$(DOCKER_COMPOSE) build

ps:
	$(DOCKER_COMPOSE) ps

logs:
	$(DOCKER_COMPOSE) logs -f

logs-backend:
	$(DOCKER_COMPOSE) logs -f backend

logs-frontend:
	$(DOCKER_COMPOSE) logs -f frontend

restart:
	$(DOCKER_COMPOSE) restart

clean:
	$(DOCKER_COMPOSE) down -v

up-ollama:
	$(DOCKER_COMPOSE) --profile ollama up -d

down-ollama:
	$(DOCKER_COMPOSE) --profile ollama down

ollama-pull-embed:
	$(DOCKER_COMPOSE) --profile ollama exec -T ollama ollama pull nomic-embed-text

ollama-list-models:
	$(DOCKER_COMPOSE) --profile ollama exec -T ollama ollama list

test: test-backend test-frontend

test-backend:
	$(PYTEST) -q

test-backend-unit:
	$(PYTEST) -q tests/unit

test-backend-integration:
	$(PYTEST) -q tests/integration

test-frontend:
	$(NPM) --prefix $(FRONTEND_DIR) run test:run
