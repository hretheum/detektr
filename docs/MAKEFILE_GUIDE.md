# 📚 Makefile Guide

## Overview

The unified Makefile provides a single interface for all common operations in the Detektor project. It follows the principle of "one command to rule them all" - making development, testing, and deployment consistent and simple.

## Quick Reference

### Most Used Commands

```bash
# Initial setup
make setup

# Daily development
make up              # Start development stack
make down            # Stop everything
make logs            # Show logs
make dev-shell SVC=rtsp-capture  # Shell into service

# Before committing
make format          # Format code
make lint            # Check code quality
make test            # Run tests

# Deployment
make deploy          # Deploy to production
```

## Command Categories

### 🚀 Quick Start

| Command | Description |
|---------|-------------|
| `make setup` | Initial project setup - installs dependencies, configures secrets |
| `make up` | Start local development (alias for dev-up) |
| `make down` | Stop all services (alias for dev-down) |
| `make deploy` | Deploy to production (alias for prod-deploy) |

### 🛠️ Development

| Command | Description |
|---------|-------------|
| `make dev-up` | Start development environment with hot reload |
| `make dev-down` | Stop development environment |
| `make dev-restart` | Restart development environment |
| `make dev-logs` | Show development logs (use SERVICE=name for specific) |
| `make dev-shell SVC=name` | Shell into a specific service |
| `make dev-build` | Build/rebuild development images |

### 🏭 Production

| Command | Description |
|---------|-------------|
| `make prod-deploy` | Deploy to production using unified script |
| `make prod-status` | Check production service status |
| `make prod-logs` | Show production logs |
| `make prod-verify` | Verify all production health checks |
| `make prod-rollback` | Rollback to previous deployment |

### 🧪 Testing

| Command | Description |
|---------|-------------|
| `make test` | Run all tests (unit + integration) |
| `make test-unit` | Run only unit tests |
| `make test-integration` | Run only integration tests |
| `make test-e2e` | Run end-to-end tests |
| `make test-coverage` | Generate test coverage report |
| `make test-watch` | Run tests in watch mode |

### 📊 Code Quality

| Command | Description |
|---------|-------------|
| `make lint` | Run all linters (ruff, mypy, flake8) |
| `make format` | Auto-format code (black, isort) |
| `make security` | Run security scans (bandit, safety) |
| `make pre-commit` | Run all pre-commit hooks |

### 💾 Database & Storage

| Command | Description |
|---------|-------------|
| `make db-shell` | Open PostgreSQL shell |
| `make db-backup` | Backup PostgreSQL to timestamped file |
| `make db-restore FILE=path` | Restore PostgreSQL from backup |
| `make redis-cli` | Open Redis CLI |
| `make redis-monitor` | Monitor Redis commands in real-time |

### 🔐 Secrets Management

| Command | Description |
|---------|-------------|
| `make secrets-init` | Initialize SOPS for new developer |
| `make secrets-edit` | Edit encrypted .env.sops file |
| `make secrets-decrypt` | Decrypt .env.sops to .env |
| `make secrets-encrypt` | Encrypt .env to .env.sops |
| `make secrets-status` | Check secrets configuration |

### 🧹 Utilities & Cleanup

| Command | Description |
|---------|-------------|
| `make clean` | Clean temporary files (__pycache__, .pyc, etc) |
| `make clean-docker` | Clean Docker resources (containers, volumes) |
| `make clean-all` | Clean everything (files + Docker) |
| `make info` | Show project information |
| `make stats` | Show container resource usage |

### 📈 Monitoring

| Command | Description |
|---------|-------------|
| `make metrics` | Open Prometheus (http://localhost:9090) |
| `make traces` | Open Jaeger (http://localhost:16686) |
| `make dashboards` | Open Grafana (http://localhost:3000) |

### 🔧 Advanced

| Command | Description |
|---------|-------------|
| `make profile SERVICE=name` | Profile service performance |
| `make debug SERVICE=name` | Enable debug mode for service |
| `make benchmark` | Run performance benchmarks |
| `make new-service NAME=name` | Create new service from template |
| `make update-deps` | Update all Python dependencies |

## Usage Examples

### Starting Fresh

```bash
# First time setup
git clone https://github.com/hretheum/detektr.git
cd detektr
make setup
make up
```

### Daily Development Workflow

```bash
# Start your day
make up
make logs SERVICE=rtsp-capture

# Make changes, then test
make test
make lint
make format

# Commit and deploy
git add .
git commit -m "feat: awesome feature"
make deploy
```

### Debugging a Service

```bash
# Check status
make ps

# View logs
make logs SERVICE=face-recognition

# Shell into service
make dev-shell SVC=face-recognition

# Enable debug mode
make debug SERVICE=face-recognition
```

### Working with Databases

```bash
# Backup before changes
make db-backup

# Interactive PostgreSQL
make db-shell
\dt  # List tables
\q   # Exit

# Monitor Redis
make redis-monitor
# Press Ctrl+C to stop
```

### Managing Secrets

```bash
# First time
make secrets-init

# Edit secrets
make secrets-edit
# Add: API_KEY=your-key
# Save and exit

# For local development
make secrets-decrypt
```

## Environment Variables

The Makefile respects these environment variables:

- `ENV` - Environment (development/staging/production), default: development
- `SERVICE` - Target service for commands like logs, default: all
- `SVC` - Service name for dev-shell command
- `FILE` - File path for db-restore
- `NAME` - Name for new-service command

Example:
```bash
ENV=production make ps
SERVICE=rtsp-capture make logs
```

## Tips & Tricks

### 1. Tab Completion

Add to your `.bashrc` or `.zshrc`:
```bash
complete -W "\`grep -oE '^[a-zA-Z_-]+:([^=]|$)' Makefile | sed 's/[^a-zA-Z_-]*$//'\`" make
```

### 2. Parallel Services

Start specific services:
```bash
# Edit Makefile or use docker-compose directly
docker compose up -d rtsp-capture redis postgres
```

### 3. Quick Health Check

```bash
# Check all services
make prod-verify

# Local check
for port in 8001 8005 8006; do
  curl -s http://localhost:$port/health | jq .status
done
```

### 4. Aliases

Add to your shell config:
```bash
alias dk="make"
alias dku="make up"
alias dkd="make down"
alias dkl="make logs"
alias dks="make ps"
```

## Troubleshooting

### Make command not found

```bash
# macOS
brew install make

# Ubuntu/Debian
sudo apt-get install build-essential

# Check version
make --version
```

### Permission denied

```bash
# Fix Docker permissions
sudo usermod -aG docker $USER
newgrp docker

# Fix file permissions
sudo chown -R $USER:$USER .
```

### Service-specific commands fail

```bash
# Check service name
make ps  # List all services

# Use exact name
make dev-shell SVC=detektor-rtsp-capture-1  # Wrong
make dev-shell SVC=rtsp-capture             # Correct
```

## Contributing

When adding new Makefile targets:

1. Use `.PHONY` for all targets
2. Add help text with `## Description`
3. Group related commands
4. Use consistent naming (verb-noun)
5. Add error handling

Example:
```makefile
.PHONY: my-command
my-command: ## Short description here
	@echo "🎯 Doing something..."
	@command || (echo "❌ Failed" && exit 1)
	@echo "✅ Success"
```
