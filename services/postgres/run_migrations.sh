#!/bin/bash
# run_migrations.sh - Execute PostgreSQL migrations for Detektor

set -euo pipefail

# Configuration
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-detektor}"
DB_USER="${DB_USER:-detektor}"
MIGRATIONS_DIR="$(dirname "$0")/migrations"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Starting PostgreSQL migrations...${NC}"

# Create migrations tracking table if not exists
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" <<EOF
CREATE TABLE IF NOT EXISTS detektor.schema_migrations (
    migration_id VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMPTZ DEFAULT NOW(),
    checksum VARCHAR(64)
);
EOF

# Function to calculate file checksum
calculate_checksum() {
    local file="$1"
    sha256sum "$file" | cut -d' ' -f1
}

# Function to check if migration was applied
is_migration_applied() {
    local migration_id="$1"
    local result
    result=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -tAc "SELECT 1 FROM detektor.schema_migrations WHERE migration_id = '$migration_id'")
    [[ "$result" == "1" ]]
}

# Function to apply migration
apply_migration() {
    local file="$1"
    local migration_id
    migration_id=$(basename "$file")
    local checksum
    checksum=$(calculate_checksum "$file")

    echo -e "${YELLOW}Applying migration: $migration_id${NC}"

    # Start transaction
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" <<EOF
BEGIN;
-- Apply migration
\i $file

-- Record migration
INSERT INTO detektor.schema_migrations (migration_id, checksum)
VALUES ('$migration_id', '$checksum');

COMMIT;
EOF

    echo -e "${GREEN}✓ Applied: $migration_id${NC}"
}

# Main migration loop
applied_count=0
skipped_count=0

for migration_file in "$MIGRATIONS_DIR"/*.sql; do
    if [[ -f "$migration_file" ]]; then
        migration_id=$(basename "$migration_file")

        if is_migration_applied "$migration_id"; then
            echo -e "⏭️  Skipping (already applied): $migration_id"
            ((skipped_count++))
        else
            apply_migration "$migration_file"
            ((applied_count++))
        fi
    fi
done

echo -e "\n${GREEN}Migration summary:${NC}"
echo -e "  Applied: $applied_count"
echo -e "  Skipped: $skipped_count"
echo -e "  Total:   $((applied_count + skipped_count))"

# Show current migration status
echo -e "\n${GREEN}Current migration status:${NC}"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" <<EOF
SELECT
    migration_id,
    applied_at
FROM detektor.schema_migrations
ORDER BY applied_at DESC
LIMIT 10;
EOF

echo -e "\n${GREEN}Migrations complete!${NC}"
