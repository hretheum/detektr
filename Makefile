# Makefile for Detektor project
# Simplifies common operations, especially with SOPS encryption

.PHONY: help up down logs test clean secrets-edit secrets-decrypt lint format pre-commit

# Default target
help:
	@echo "Detektor Project Commands:"
	@echo "  make up              - Start all services (decrypts secrets automatically)"
	@echo "  make down            - Stop all services"
	@echo "  make logs [service=] - Show logs (service optional)"
	@echo "  make test            - Run all tests"
	@echo "  make lint            - Run linters"
	@echo "  make format          - Format code"
	@echo "  make pre-commit      - Run pre-commit hooks"
	@echo "  make clean           - Clean up temporary files"
	@echo "  make secrets-edit    - Edit encrypted .env file"
	@echo "  make secrets-decrypt - Decrypt .env to .env.decrypted (temporary)"

# Start services with decrypted secrets
up:
	@echo "🔓 Decrypting secrets..."
	@SOPS_AGE_KEY_FILE=~/.config/sops/age/keys.txt sops -d .env > .env.decrypted 2>/dev/null || (echo "❌ Failed to decrypt .env. Do you have SOPS configured?" && exit 1)
	@echo "🚀 Starting services..."
	@docker-compose --env-file .env.decrypted up -d
	@rm -f .env.decrypted
	@echo "✅ Services started"

# Stop services
down:
	@echo "🛑 Stopping services..."
	@docker-compose down
	@echo "✅ Services stopped"

# Show logs
logs:
ifdef service
	@docker-compose logs -f $(service)
else
	@docker-compose logs -f
endif

# Run tests
test:
	@echo "🧪 Running tests..."
	@docker-compose -f docker-compose.test.yml up --abort-on-container-exit
	@echo "✅ Tests completed"

# Clean temporary files
clean:
	@echo "🧹 Cleaning up..."
	@rm -f .env.decrypted .env.*.decrypted
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Cleanup completed"

# Edit encrypted secrets
secrets-edit:
	@echo "🔐 Opening encrypted .env for editing..."
	@SOPS_AGE_KEY_FILE=~/.config/sops/age/keys.txt sops .env || (echo "❌ Failed to edit .env. Do you have SOPS configured?" && exit 1)

# Decrypt secrets (for debugging)
secrets-decrypt:
	@echo "🔓 Decrypting .env to .env.decrypted..."
	@SOPS_AGE_KEY_FILE=~/.config/sops/age/keys.txt sops -d .env > .env.decrypted || (echo "❌ Failed to decrypt .env" && exit 1)
	@echo "⚠️  Remember to delete .env.decrypted when done!"
	@echo "✅ Decrypted to .env.decrypted"

# Development tools
lint:
	@echo "🔍 Running linters..."
	@ruff check src/ tests/ || true
	@black --check src/ tests/ || true
	@echo "✅ Linting completed"

format:
	@echo "🎨 Formatting code..."
	@isort src/ tests/ || true
	@black src/ tests/ || true
	@ruff check --fix src/ tests/ || true
	@echo "✅ Formatting completed"

pre-commit:
	@echo "🤖 Running pre-commit hooks..."
	@pre-commit run --all-files
	@echo "✅ Pre-commit completed"

install-hooks:
	@echo "🔧 Installing git hooks..."
	@pre-commit install
	@pre-commit install --hook-type commit-msg
	@echo "✅ Hooks installed"

# Initialize SOPS for new developer
secrets-init:
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
