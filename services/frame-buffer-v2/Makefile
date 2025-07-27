.PHONY: help setup test test-env-up test-env-down test-unit test-integration test-performance clean format lint type-check

# Default target
.DEFAULT_GOAL := help

# Python interpreter
PYTHON := python3
VENV := venv
VENV_BIN := $(VENV)/bin

# Colors for output
CYAN := \033[0;36m
GREEN := \033[0;32m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Show this help message
	@echo '$(CYAN)Frame Buffer v2 - Development Commands$(NC)'
	@echo ''
	@echo 'Usage:'
	@echo '  make $(GREEN)<target>$(NC)'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup: ## Set up development environment
	@echo "$(CYAN)Setting up development environment...$(NC)"
	$(PYTHON) -m venv $(VENV)
	$(VENV_BIN)/pip install --upgrade pip setuptools wheel
	$(VENV_BIN)/pip install -r requirements-test.txt
	$(VENV_BIN)/pre-commit install
	@echo "$(GREEN)✓ Development environment ready$(NC)"

test-env-up: ## Start test environment (Redis, Jaeger, PostgreSQL)
	@echo "$(CYAN)Starting test environment...$(NC)"
	docker-compose -f docker-compose.test.yml up -d
	@echo "$(CYAN)Waiting for services to be healthy...$(NC)"
	@sleep 5
	@docker-compose -f docker-compose.test.yml ps
	@echo "$(GREEN)✓ Test environment is running$(NC)"

test-env-down: ## Stop test environment
	@echo "$(CYAN)Stopping test environment...$(NC)"
	docker-compose -f docker-compose.test.yml down -v
	@echo "$(GREEN)✓ Test environment stopped$(NC)"

test-env-logs: ## Show test environment logs
	docker-compose -f docker-compose.test.yml logs -f

test: test-env-up ## Run all tests
	@echo "$(CYAN)Running all tests...$(NC)"
	$(VENV_BIN)/pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html
	@echo "$(GREEN)✓ All tests completed$(NC)"

test-unit: ## Run unit tests only
	@echo "$(CYAN)Running unit tests...$(NC)"
	$(VENV_BIN)/pytest tests/unit/ -v

test-integration: test-env-up ## Run integration tests
	@echo "$(CYAN)Running integration tests...$(NC)"
	$(VENV_BIN)/pytest tests/integration/ -v

test-performance: test-env-up ## Run performance tests
	@echo "$(CYAN)Running performance tests...$(NC)"
	$(VENV_BIN)/pytest tests/performance/ -v -m benchmark

test-watch: ## Run tests in watch mode
	$(VENV_BIN)/pytest-watch tests/ -v

format: ## Format code with black and isort
	@echo "$(CYAN)Formatting code...$(NC)"
	$(VENV_BIN)/black src/ tests/
	$(VENV_BIN)/isort src/ tests/
	@echo "$(GREEN)✓ Code formatted$(NC)"

lint: ## Run linting checks
	@echo "$(CYAN)Running linting checks...$(NC)"
	$(VENV_BIN)/flake8 src/ tests/
	@echo "$(GREEN)✓ Linting passed$(NC)"

type-check: ## Run type checking with mypy
	@echo "$(CYAN)Running type checks...$(NC)"
	$(VENV_BIN)/mypy src/ tests/
	@echo "$(GREEN)✓ Type checking passed$(NC)"

check: format lint type-check ## Run all code quality checks

clean: ## Clean up generated files
	@echo "$(CYAN)Cleaning up...$(NC)"
	rm -rf $(VENV)
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf .mypy_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	@echo "$(GREEN)✓ Cleanup complete$(NC)"

# Development shortcuts
dev: test-env-up ## Start development environment
	@echo "$(GREEN)Development environment ready!$(NC)"
	@echo "Redis: localhost:6379"
	@echo "Jaeger UI: http://localhost:16686"
	@echo "PostgreSQL: localhost:5432"

shell: ## Open Python shell with project context
	$(VENV_BIN)/python
