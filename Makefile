.PHONY: help install dev-install format lint type-check test test-coverage run migrate docker-up docker-down docker-build docker-logs clean

# Variables
PYTHON := python3
POETRY := poetry
UVICORN := uvicorn
APP_MODULE := app.main:app
HOST := 0.0.0.0
PORT := 8000

# Colors for output
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "SlideGenie Backend - Available Commands"
	@echo "======================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

install: ## Install production dependencies
	@echo "$(YELLOW)Installing production dependencies...$(NC)"
	$(POETRY) install --only main

dev-install: ## Install all dependencies including dev
	@echo "$(YELLOW)Installing all dependencies...$(NC)"
	$(POETRY) install
	pre-commit install

format: ## Format code with black and isort
	@echo "$(YELLOW)Formatting code...$(NC)"
	$(POETRY) run isort app tests
	$(POETRY) run black app tests

lint: ## Run flake8 linter
	@echo "$(YELLOW)Running linter...$(NC)"
	$(POETRY) run flake8 app tests

type-check: ## Run mypy type checker
	@echo "$(YELLOW)Running type checker...$(NC)"
	$(POETRY) run mypy app

test: ## Run tests
	@echo "$(YELLOW)Running tests...$(NC)"
	$(POETRY) run pytest tests/ -v

test-coverage: ## Run tests with coverage
	@echo "$(YELLOW)Running tests with coverage...$(NC)"
	$(POETRY) run pytest tests/ --cov=app --cov-report=html --cov-report=term-missing

run: ## Run the application locally
	@echo "$(GREEN)Starting SlideGenie API...$(NC)"
	$(POETRY) run $(UVICORN) $(APP_MODULE) --host $(HOST) --port $(PORT) --reload

run-prod: ## Run the application in production mode
	@echo "$(GREEN)Starting SlideGenie API in production mode...$(NC)"
	$(POETRY) run gunicorn $(APP_MODULE) -w 4 -k uvicorn.workers.UvicornWorker --bind $(HOST):$(PORT)

migrate: ## Run database migrations
	@echo "$(YELLOW)Running database migrations...$(NC)"
	$(POETRY) run alembic upgrade head

migrate-create: ## Create a new migration
	@echo "$(YELLOW)Creating new migration...$(NC)"
	@read -p "Enter migration message: " msg; \
	$(POETRY) run alembic revision --autogenerate -m "$$msg"

migrate-rollback: ## Rollback last migration
	@echo "$(YELLOW)Rolling back last migration...$(NC)"
	$(POETRY) run alembic downgrade -1

docker-up: ## Start all services with docker-compose
	@echo "$(GREEN)Starting Docker services...$(NC)"
	docker-compose up -d

docker-down: ## Stop all services
	@echo "$(YELLOW)Stopping Docker services...$(NC)"
	docker-compose down

docker-build: ## Build docker images
	@echo "$(YELLOW)Building Docker images...$(NC)"
	docker-compose build

docker-logs: ## Show docker logs
	docker-compose logs -f

docker-clean: ## Clean docker volumes
	@echo "$(RED)Cleaning Docker volumes...$(NC)"
	docker-compose down -v

db-shell: ## Access PostgreSQL shell
	@echo "$(YELLOW)Connecting to PostgreSQL...$(NC)"
	docker-compose exec postgres psql -U slidegenie -d slidegenie

redis-cli: ## Access Redis CLI
	@echo "$(YELLOW)Connecting to Redis...$(NC)"
	docker-compose exec redis redis-cli

clean: ## Clean up cache and temporary files
	@echo "$(YELLOW)Cleaning up...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type f -name ".coverage" -delete

setup: docker-up migrate ## Complete setup: start services and run migrations
	@echo "$(GREEN)Setup complete! API running at http://localhost:8000$(NC)"

check: format lint type-check test ## Run all checks

pre-commit: ## Run pre-commit hooks
	@echo "$(YELLOW)Running pre-commit hooks...$(NC)"
	pre-commit run --all-files