#!/bin/bash
#
# Migration script from old docker-compose structure to new hierarchical structure
# This script helps transition from multiple docker-compose files to organized structure

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [[ ! -f "docker-compose.yml" ]]; then
    log_error "This script must be run from the project root directory"
    exit 1
fi

# Function to backup existing files
backup_files() {
    log_info "Creating backup of existing docker-compose files..."

    backup_dir="docker-compose-backup-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$backup_dir"

    # Find all docker-compose files
    find . -maxdepth 3 -name "docker-compose*.yml" -o -name "docker-compose*.yaml" | while read -r file; do
        if [[ ! "$file" =~ "docker/" ]]; then  # Don't backup new structure
            cp -v "$file" "$backup_dir/"
        fi
    done

    log_info "Backup created in $backup_dir"
}

# Function to create new structure directories
create_directories() {
    log_info "Creating new directory structure..."

    mkdir -p docker/{base,environments/{development,staging,production},features/{gpu,redis-ha,ai-services}}
    mkdir -p docker/base/{config,init-scripts}

    log_info "Directory structure created"
}

# Function to migrate configuration files
migrate_configs() {
    log_info "Migrating configuration files..."

    # Prometheus config
    if [[ -f "prometheus.yml" ]]; then
        cp prometheus.yml docker/base/config/
        log_info "Migrated prometheus.yml"
    fi

    # Grafana configs
    if [[ -d "grafana" ]]; then
        cp -r grafana docker/base/config/
        log_info "Migrated Grafana configuration"
    fi

    # Database init scripts
    if [[ -d "scripts/db" ]]; then
        cp -r scripts/db/* docker/base/init-scripts/ 2>/dev/null || true
        log_info "Migrated database init scripts"
    fi
}

# Function to show migration commands
show_migration_commands() {
    log_info "Migration complete! Here are the new commands to use:"
    echo
    echo "# Development environment (with hot reload and debug tools):"
    echo "docker-compose -f docker/base/docker-compose.yml \\"
    echo "              -f docker/base/docker-compose.storage.yml \\"
    echo "              -f docker/base/docker-compose.observability.yml \\"
    echo "              -f docker/environments/development/docker-compose.override.yml up"
    echo
    echo "# Production environment (optimized settings):"
    echo "docker-compose -f docker/base/docker-compose.yml \\"
    echo "              -f docker/base/docker-compose.storage.yml \\"
    echo "              -f docker/base/docker-compose.observability.yml \\"
    echo "              -f docker/environments/production/docker-compose.override.yml up"
    echo
    echo "# With GPU support:"
    echo "docker-compose -f docker/base/docker-compose.yml \\"
    echo "              -f docker/base/docker-compose.storage.yml \\"
    echo "              -f docker/features/gpu/docker-compose.gpu.yml up"
    echo
    echo "# With Redis HA:"
    echo "docker-compose -f docker/base/docker-compose.yml \\"
    echo "              -f docker/features/redis-ha/docker-compose.redis-ha.yml up"
    echo
    echo "# With all AI services:"
    echo "docker-compose -f docker/base/docker-compose.yml \\"
    echo "              -f docker/base/docker-compose.storage.yml \\"
    echo "              -f docker/features/ai-services/docker-compose.ai.yml up"
}

# Function to create convenience scripts
create_convenience_scripts() {
    log_info "Creating convenience scripts..."

    # Development script
    cat > docker/dev.sh << 'EOF'
#!/bin/bash
# Convenience script for development environment

docker-compose \
    -f docker/base/docker-compose.yml \
    -f docker/base/docker-compose.storage.yml \
    -f docker/base/docker-compose.observability.yml \
    -f docker/environments/development/docker-compose.override.yml \
    "$@"
EOF
    chmod +x docker/dev.sh

    # Production script
    cat > docker/prod.sh << 'EOF'
#!/bin/bash
# Convenience script for production environment

docker-compose \
    -f docker/base/docker-compose.yml \
    -f docker/base/docker-compose.storage.yml \
    -f docker/base/docker-compose.observability.yml \
    -f docker/environments/production/docker-compose.override.yml \
    "$@"
EOF
    chmod +x docker/prod.sh

    # Test script
    cat > docker/test.sh << 'EOF'
#!/bin/bash
# Convenience script for running tests

docker-compose \
    -f docker/base/docker-compose.yml \
    -f docker/base/docker-compose.storage.yml \
    -f docker/environments/development/docker-compose.override.yml \
    run --rm "$@"
EOF
    chmod +x docker/test.sh

    log_info "Convenience scripts created: docker/dev.sh, docker/prod.sh, docker/test.sh"
}

# Function to update Makefile
update_makefile() {
    log_info "Updating Makefile with new commands..."

    # Check if Makefile exists
    if [[ ! -f "Makefile" ]]; then
        log_warn "Makefile not found, skipping update"
        return
    fi

    # Create backup
    cp Makefile Makefile.bak

    # Add new targets (append to end of file)
    cat >> Makefile << 'EOF'

# New hierarchical docker-compose commands
.PHONY: dev-up dev-down prod-up prod-down

dev-up: ## Start development environment
	./docker/dev.sh up -d

dev-down: ## Stop development environment
	./docker/dev.sh down

prod-up: ## Start production environment
	./docker/prod.sh up -d

prod-down: ## Stop production environment
	./docker/prod.sh down

dev-logs: ## Show development logs
	./docker/dev.sh logs -f

prod-logs: ## Show production logs
	./docker/prod.sh logs -f

dev-ps: ## Show development container status
	./docker/dev.sh ps

prod-ps: ## Show production container status
	./docker/prod.sh ps
EOF

    log_info "Makefile updated with new targets"
}

# Main migration flow
main() {
    log_info "Starting Docker Compose migration..."

    # Ask for confirmation
    read -p "This will reorganize your Docker Compose files. Continue? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Migration cancelled"
        exit 0
    fi

    # Run migration steps
    backup_files
    create_directories
    migrate_configs
    create_convenience_scripts
    update_makefile

    log_info "Migration completed successfully!"
    echo
    show_migration_commands

    echo
    log_warn "Note: Old docker-compose files have been backed up but not removed."
    log_warn "Test the new structure first, then manually remove old files when ready."
}

# Run main function
main "$@"
