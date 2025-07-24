# Makefile for Detektor project
# Unified commands for development, testing, deployment, and maintenance

.PHONY: help
help: ## Show this help message
	@echo "Detektor - Available commands:"
	@echo ""
	@echo "QUICK START:"
	@echo "  make setup              - Initial project setup"
	@echo "  make up                 - Start local development"
	@echo "  make deploy             - Deploy to production"
	@echo ""
	@echo "DEVELOPMENT:"
	@echo "  make dev-up             - Start development stack"
	@echo "  make dev-down           - Stop development stack"
	@echo "  make dev-logs           - Show development logs"
	@echo "  make dev-shell SVC=name - Shell into development service"
	@echo ""
	@echo "PRODUCTION:"
	@echo "  make prod-deploy        - Deploy to production"
	@echo "  make prod-status        - Check production status"
	@echo "  make prod-logs          - Show production logs"
	@echo "  make prod-verify        - Verify production health"
	@echo ""
	@echo "TESTING:"
	@echo "  make test               - Run all tests"
	@echo "  make test-unit          - Run unit tests"
	@echo "  make test-integration   - Run integration tests"
	@echo "  make test-coverage      - Generate coverage report"
	@echo ""
	@echo "CODE QUALITY:"
	@echo "  make lint               - Run linters"
	@echo "  make format             - Format code"
	@echo "  make security           - Security scan"
	@echo "  make pre-commit         - Run pre-commit hooks"
	@echo ""
	@echo "UTILITIES:"
	@echo "  make clean              - Clean temporary files"
	@echo "  make clean-docker       - Clean Docker resources"
	@echo "  make secrets-edit       - Edit encrypted secrets"
	@echo "  make db-shell           - PostgreSQL shell"
	@echo "  make redis-cli          - Redis CLI"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Variables
SHELL := /bin/bash
.DEFAULT_GOAL := help

# Environment detection
ENV ?= development
SERVICE ?= all
COMPOSE_PROJECT_NAME ?= detektor

# Compose files based on environment
ifeq ($(ENV),production)
    COMPOSE_FILES := -f docker/base/docker-compose.yml \
                     -f docker/base/docker-compose.storage.yml \
                     -f docker/base/docker-compose.observability.yml \
                     -f docker/environments/production/docker-compose.yml
else ifeq ($(ENV),staging)
    COMPOSE_FILES := -f docker/base/docker-compose.yml \
                     -f docker/base/docker-compose.storage.yml \
                     -f docker/environments/staging/docker-compose.yml
else
    COMPOSE_FILES := -f docker/base/docker-compose.yml \
                     -f docker/base/docker-compose.storage.yml \
                     -f docker/base/docker-compose.observability.yml \
                     -f docker/environments/development/docker-compose.yml
endif

# Docker compose command
DC := docker compose $(COMPOSE_FILES)

# =============================================================================
# QUICK START
# =============================================================================

.PHONY: setup
setup: ## Initial project setup
	@echo "🔧 Setting up Detektor project..."
	@echo "1. Installing Python dependencies..."
	@command -v python3.11 >/dev/null || (echo "❌ Python 3.11+ required" && exit 1)
	@python3.11 -m venv venv
	@./venv/bin/pip install --upgrade pip
	@./venv/bin/pip install pre-commit black isort ruff mypy
	@echo "2. Installing pre-commit hooks..."
	@./venv/bin/pre-commit install
	@echo "3. Checking Docker..."
	@docker --version || (echo "❌ Docker not installed" && exit 1)
	@docker compose version || (echo "❌ Docker Compose v2 required" && exit 1)
	@echo "4. Setting up secrets..."
	@make secrets-init
	@echo "5. Creating directories..."
	@mkdir -p logs data backups
	@echo "✅ Setup complete! Run 'make dev-up' to start development"

.PHONY: up
up: dev-up ## Start local development (alias for dev-up)

.PHONY: down
down: dev-down ## Stop all services (alias for dev-down)

.PHONY: deploy
deploy: prod-deploy ## Deploy to production (alias for prod-deploy)

# =============================================================================
# DEVELOPMENT
# =============================================================================

.PHONY: dev-up
dev-up: ## Start development environment
	@echo "🚀 Starting development environment..."
	@./docker/dev.sh up -d || $(DC) up -d
	@echo "✅ Development stack started"
	@echo "   Grafana: http://localhost:3000 (admin/admin)"
	@echo "   Prometheus: http://localhost:9090"
	@echo "   Jaeger: http://localhost:16686"

.PHONY: dev-down
dev-down: ## Stop development environment
	@echo "🛑 Stopping development environment..."
	@./docker/dev.sh down || $(DC) down
	@echo "✅ Development stack stopped"

.PHONY: dev-restart
dev-restart: ## Restart development environment
	@make dev-down
	@make dev-up

.PHONY: dev-logs
dev-logs: ## Show development logs
	@./docker/dev.sh logs -f $(SERVICE) || $(DC) logs -f $(SERVICE)

.PHONY: dev-shell
dev-shell: ## Shell into development service (use SVC=service-name)
ifndef SVC
	@echo "❌ Please specify SVC=service-name"
	@exit 1
else
	@docker exec -it detektor-$(SVC)-1 /bin/bash || \
	 docker exec -it detektor-$(SVC)-1 /bin/sh
endif

.PHONY: dev-build
dev-build: ## Build development images
	@echo "🔨 Building development images..."
	@$(DC) build
	@echo "✅ Build complete"

# =============================================================================
# PRODUCTION
# =============================================================================

.PHONY: prod-deploy
prod-deploy: ## Deploy to production
	@echo "🚀 Deploying to production..."
	@./scripts/deploy.sh production deploy
	@echo "✅ Production deployment complete"

.PHONY: prod-status
prod-status: ## Check production status
	@./scripts/deploy.sh production status

.PHONY: prod-logs
prod-logs: ## Show production logs
	@./scripts/deploy.sh production logs $(SERVICE)

.PHONY: prod-verify
prod-verify: ## Verify production health
	@./scripts/deploy.sh production verify

.PHONY: prod-rollback
prod-rollback: ## Rollback production deployment
	@echo "⚠️  Rolling back production..."
	@./scripts/deploy.sh production rollback
	@echo "✅ Rollback complete"

# =============================================================================
# TESTING
# =============================================================================

.PHONY: test
test: ## Run all tests
	@echo "🧪 Running all tests..."
	@make test-unit
	@make test-integration
	@echo "✅ All tests passed"

.PHONY: test-unit
test-unit: ## Run unit tests
	@echo "🧪 Running unit tests..."
	@docker compose -f docker-compose.test.yml run --rm test-runner pytest tests/unit -v

.PHONY: test-integration
test-integration: ## Run integration tests
	@echo "🧪 Running integration tests..."
	@docker compose -f docker-compose.test.yml run --rm test-runner pytest tests/integration -v

.PHONY: test-e2e
test-e2e: ## Run end-to-end tests
	@echo "🧪 Running e2e tests..."
	@docker compose -f docker-compose.test.yml run --rm test-runner pytest tests/e2e -v

.PHONY: test-coverage
test-coverage: ## Generate test coverage report
	@echo "📊 Generating coverage report..."
	@docker compose -f docker-compose.test.yml run --rm test-runner \
		pytest --cov=services --cov-report=html --cov-report=term
	@echo "✅ Coverage report generated in htmlcov/"

.PHONY: test-watch
test-watch: ## Run tests in watch mode
	@docker compose -f docker-compose.test.yml run --rm test-runner \
		ptw -- --testmon

# =============================================================================
# CODE QUALITY
# =============================================================================

.PHONY: lint
lint: ## Run all linters
	@echo "🔍 Running linters..."
	@echo "Running ruff..."
	@ruff check services/ || true
	@echo "Running mypy..."
	@mypy services/ || true
	@echo "Running flake8..."
	@flake8 services/ || true
	@echo "✅ Linting complete"

.PHONY: format
format: ## Format code
	@echo "🎨 Formatting code..."
	@black services/ tests/
	@isort services/ tests/
	@ruff check --fix services/ tests/
	@echo "✅ Formatting complete"

.PHONY: security
security: ## Run security checks
	@echo "🔐 Running security checks..."
	@bandit -r services/ || true
	@safety check || true
	@echo "✅ Security check complete"

.PHONY: pre-commit
pre-commit: ## Run pre-commit hooks
	@echo "🤖 Running pre-commit hooks..."
	@pre-commit run --all-files
	@echo "✅ Pre-commit complete"

# =============================================================================
# DATABASE & STORAGE
# =============================================================================

.PHONY: db-shell
db-shell: ## PostgreSQL shell
	@docker exec -it detektor-postgres-1 psql -U postgres detektor

.PHONY: db-backup
db-backup: ## Backup PostgreSQL
	@echo "💾 Backing up database..."
	@mkdir -p backups
	@docker exec detektor-postgres-1 pg_dump -U postgres detektor > \
		backups/postgres-backup-$$(date +%Y%m%d-%H%M%S).sql
	@echo "✅ Database backed up"

.PHONY: db-restore
db-restore: ## Restore PostgreSQL (use FILE=path/to/backup.sql)
ifndef FILE
	@echo "❌ Please specify FILE=path/to/backup.sql"
	@exit 1
else
	@echo "📥 Restoring database from $(FILE)..."
	@docker exec -i detektor-postgres-1 psql -U postgres detektor < $(FILE)
	@echo "✅ Database restored"
endif

.PHONY: redis-cli
redis-cli: ## Redis CLI
	@docker exec -it detektor-redis-1 redis-cli

.PHONY: redis-monitor
redis-monitor: ## Monitor Redis in real-time
	@docker exec -it detektor-redis-1 redis-cli monitor

# =============================================================================
# SECRETS MANAGEMENT
# =============================================================================

.PHONY: secrets-init
secrets-init: ## Initialize SOPS for new developer
	@echo "🔑 Initializing SOPS..."
	@which sops >/dev/null || (echo "❌ SOPS not installed. Run: brew install sops" && exit 1)
	@which age >/dev/null || (echo "❌ age not installed. Run: brew install age" && exit 1)
	@if [ ! -f ~/.config/sops/age/keys.txt ]; then \
		echo "📝 Generating age keypair..."; \
		mkdir -p ~/.config/sops/age; \
		age-keygen -o ~/.config/sops/age/keys.txt; \
	fi
	@echo "🔑 Your public key:"
	@age-keygen -y ~/.config/sops/age/keys.txt
	@echo ""
	@echo "📋 Add this public key to .sops.yaml to encrypt/decrypt secrets"
	@echo "✅ SOPS initialized"

.PHONY: secrets-edit
secrets-edit: ## Edit encrypted secrets
	@echo "🔐 Opening encrypted .env for editing..."
	@SOPS_AGE_KEY_FILE=~/.config/sops/age/keys.txt sops .env.sops || \
		(echo "❌ Failed to edit .env.sops. Do you have SOPS configured?" && exit 1)

.PHONY: secrets-decrypt
secrets-decrypt: ## Decrypt secrets to .env
	@echo "🔓 Decrypting .env.sops to .env..."
	@SOPS_AGE_KEY_FILE=~/.config/sops/age/keys.txt sops -d .env.sops > .env || \
		(echo "❌ Failed to decrypt .env.sops" && exit 1)
	@echo "✅ Decrypted to .env"

.PHONY: secrets-encrypt
secrets-encrypt: ## Encrypt .env to .env.sops
	@echo "🔒 Encrypting .env to .env.sops..."
	@SOPS_AGE_KEY_FILE=~/.config/sops/age/keys.txt sops -e .env > .env.sops || \
		(echo "❌ Failed to encrypt .env" && exit 1)
	@echo "✅ Encrypted to .env.sops"

.PHONY: secrets-status
secrets-status: ## Check secrets status
	@echo "🔐 Secrets status:"
	@ls -la .env* 2>/dev/null || echo "No .env files found"
	@echo ""
	@if [ -f .env.sops ]; then \
		echo "✅ Encrypted secrets found (.env.sops)"; \
	else \
		echo "❌ No encrypted secrets found"; \
	fi

# =============================================================================
# UTILITIES & CLEANUP
# =============================================================================

.PHONY: clean
clean: ## Clean temporary files
	@echo "🧹 Cleaning temporary files..."
	@rm -f .env.decrypted .env.*.decrypted
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleanup complete"

.PHONY: clean-docker
clean-docker: ## Clean Docker resources
	@echo "🧹 Cleaning Docker resources..."
	@docker compose down -v --remove-orphans
	@docker system prune -af --volumes
	@echo "✅ Docker cleanup complete"

.PHONY: clean-all
clean-all: clean clean-docker ## Clean everything
	@echo "✅ Full cleanup complete"

.PHONY: logs
logs: ## Show logs (use SERVICE=name for specific service)
	@$(DC) logs -f $(SERVICE)

.PHONY: ps
ps: ## Show running containers
	@$(DC) ps

.PHONY: stats
stats: ## Show container resource usage
	@docker stats --no-stream

.PHONY: info
info: ## Show project information
	@echo "📋 Detektor Project Information"
	@echo "================================"
	@echo "Environment: $(ENV)"
	@echo "Project: $(COMPOSE_PROJECT_NAME)"
	@echo ""
	@echo "Services:"
	@$(DC) ps --services
	@echo ""
	@echo "Images:"
	@docker images | grep detektr || echo "No images built yet"

# =============================================================================
# MONITORING & OBSERVABILITY
# =============================================================================

.PHONY: metrics
metrics: ## Show Prometheus metrics
	@echo "📊 Opening Prometheus metrics..."
	@open http://localhost:9090 || xdg-open http://localhost:9090

.PHONY: traces
traces: ## Show Jaeger traces
	@echo "🔍 Opening Jaeger traces..."
	@open http://localhost:16686 || xdg-open http://localhost:16686

.PHONY: dashboards
dashboards: ## Open Grafana dashboards
	@echo "📈 Opening Grafana dashboards..."
	@open http://localhost:3000 || xdg-open http://localhost:3000
	@echo "Default credentials: admin/admin"

# =============================================================================
# ADVANCED OPERATIONS
# =============================================================================

.PHONY: profile
profile: ## Profile service performance (use SERVICE=name)
ifndef SERVICE
	@echo "❌ Please specify SERVICE=name"
	@exit 1
else
	@echo "📊 Profiling $(SERVICE)..."
	@docker exec -it detektor-$(SERVICE)-1 py-spy top --pid 1
endif

.PHONY: debug
debug: ## Enable debug mode for service (use SERVICE=name)
ifndef SERVICE
	@echo "❌ Please specify SERVICE=name"
	@exit 1
else
	@echo "🐛 Enabling debug mode for $(SERVICE)..."
	@docker compose stop $(SERVICE)
	@LOG_LEVEL=DEBUG $(DC) up -d $(SERVICE)
	@docker compose logs -f $(SERVICE)
endif

.PHONY: benchmark
benchmark: ## Run performance benchmarks
	@echo "⚡ Running benchmarks..."
	@docker compose -f docker-compose.benchmark.yml up --abort-on-container-exit

# =============================================================================
# DEVELOPMENT WORKFLOW HELPERS
# =============================================================================

.PHONY: new-service
new-service: ## Create new service from template (use NAME=service-name)
ifndef NAME
	@echo "❌ Please specify NAME=service-name"
	@exit 1
else
	@echo "🆕 Creating new service: $(NAME)..."
	@cp -r services/base-template services/$(NAME)
	@find services/$(NAME) -type f -exec sed -i '' 's/base-template/$(NAME)/g' {} \;
	@echo "✅ Service created at services/$(NAME)"
	@echo "Next steps:"
	@echo "1. Edit services/$(NAME)/src/main.py"
	@echo "2. Add to docker-compose.yml"
	@echo "3. Run 'make dev-build'"
endif

.PHONY: update-deps
update-deps: ## Update Python dependencies
	@echo "📦 Updating dependencies..."
	@for service in services/*/; do \
		if [ -f "$$service/pyproject.toml" ]; then \
			echo "Updating $$service..."; \
			cd "$$service" && poetry update; \
		fi \
	done
	@echo "✅ Dependencies updated"

# Default target
.DEFAULT_GOAL := help
