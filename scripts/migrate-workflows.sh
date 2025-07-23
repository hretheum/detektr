#!/bin/bash
# Migrate from 14 workflows to 5 consolidated workflows
# This script helps transition to the new workflow structure

set -e

echo "🚀 Workflow Migration Script for Detektor"
echo "========================================"
echo "This script will help migrate from 14 workflows to 5 consolidated ones."
echo ""

# Check if we're in the right directory
if [ ! -d ".github/workflows" ]; then
    echo "❌ Error: .github/workflows directory not found"
    echo "Please run this script from the project root"
    exit 1
fi

# Backup existing workflows
echo "📦 Creating backup of existing workflows..."
backup_dir=".github/workflows.backup.$(date +%Y%m%d-%H%M%S)"
cp -r .github/workflows "$backup_dir"
echo "✅ Backup created: $backup_dir"

# Define workflows to deprecate
workflows_to_deprecate=(
    "ci.yml"                    # Merged into pr-checks.yml
    "deploy-self-hosted.yml"    # Replaced by main-pipeline.yml
    "deploy-only.yml"           # Merged into main-pipeline.yml
    "manual-service-build.yml"  # Merged into main-pipeline.yml
    "cleanup-runner.yml"        # Merged into manual-operations.yml
    "test-runner.yml"           # Merged into manual-operations.yml
    "diagnostic.yml"            # Merged into manual-operations.yml
    "db-deploy.yml"             # Merged into main-pipeline.yml
    "build-gpu-base.yml"        # Merged into scheduled-tasks.yml
    "security.yml"              # Merged into scheduled-tasks.yml
    "UNIFIED-deploy.yml"        # Template, no longer needed
)

# Create deprecated directory
deprecated_dir=".github/workflows/deprecated"
mkdir -p "$deprecated_dir"

echo ""
echo "🔄 Migrating workflows..."

# Move deprecated workflows
for workflow in "${workflows_to_deprecate[@]}"; do
    if [ -f ".github/workflows/$workflow" ]; then
        echo "  - Moving $workflow to deprecated/"
        mv ".github/workflows/$workflow" "$deprecated_dir/"
    else
        echo "  - $workflow not found (already moved?)"
    fi
done

# Update any workflow references
echo ""
echo "📝 Updating workflow references..."

# Update README if it references old workflows
if [ -f "README.md" ]; then
    # Update CI badge
    sed -i '' 's|workflows/ci.yml|workflows/pr-checks.yml|g' README.md
    # Update Deploy badge
    sed -i '' 's|workflows/deploy.yml|workflows/main-pipeline.yml|g' README.md
    echo "✅ Updated README.md"
fi

# Create migration guide
cat > "$deprecated_dir/MIGRATION_GUIDE.md" << 'EOF'
# Workflow Migration Guide

## Migration from 14 to 5 Workflows

This directory contains deprecated workflows that have been consolidated into 5 main workflows:

### Workflow Mapping

| Old Workflow | New Workflow | Notes |
|--------------|--------------|-------|
| ci.yml | pr-checks.yml | Tests now run on PRs |
| deploy-self-hosted.yml | main-pipeline.yml | Main CI/CD pipeline |
| deploy-only.yml | main-pipeline.yml | Use action: deploy-only |
| manual-service-build.yml | main-pipeline.yml | Use workflow_dispatch |
| cleanup-runner.yml | manual-operations.yml | operation: cleanup-runner |
| test-runner.yml | manual-operations.yml | operation: test-runner |
| diagnostic.yml | manual-operations.yml | operation: diagnostic |
| db-deploy.yml | main-pipeline.yml | Included in service detection |
| build-gpu-base.yml | scheduled-tasks.yml | Weekly rebuild |
| security.yml | scheduled-tasks.yml | Monthly security scan |

### How to Use New Workflows

#### Main Pipeline (CI/CD)
```yaml
# Trigger build and deploy
gh workflow run main-pipeline.yml

# Build only specific services
gh workflow run main-pipeline.yml -f action=build-only -f services=rtsp-capture,frame-tracking

# Deploy only (no build)
gh workflow run main-pipeline.yml -f action=deploy-only
```

#### PR Checks
Automatically runs on all PRs with:
- Title validation
- Size labeling
- Dependency review
- Python tests
- Docker build tests

#### Manual Operations
```yaml
# Cleanup runner
gh workflow run manual-operations.yml -f operation=cleanup-runner

# Run diagnostics
gh workflow run manual-operations.yml -f operation=diagnostic

# Test runner
gh workflow run manual-operations.yml -f operation=test-runner
```

#### Scheduled Tasks
- Daily: Docker cleanup (2 AM UTC)
- Weekly: Base image rebuild (Sunday 3 AM UTC)
- Monthly: Security scan (1st day 4 AM UTC)

### Rollback Instructions

If you need to rollback to the old workflows:
1. Copy workflows from the backup directory
2. Remove the new consolidated workflows
3. Update any badge references in README

Backup location: ../.backup.*
EOF

echo "✅ Created migration guide"

# Summary
echo ""
echo "📊 Migration Summary"
echo "==================="
echo "✅ Backed up existing workflows to: $backup_dir"
echo "✅ Moved ${#workflows_to_deprecate[@]} workflows to deprecated/"
echo "✅ Created migration guide"
echo ""
echo "📋 New Workflow Structure:"
echo "  - main-pipeline.yml     (CI/CD)"
echo "  - pr-checks.yml         (PR validation)"
echo "  - manual-operations.yml (Manual tasks)"
echo "  - scheduled-tasks.yml   (Cron jobs)"
echo "  - release.yml          (Releases)"
echo ""
echo "⚠️  Next Steps:"
echo "1. Review and commit these changes"
echo "2. Test new workflows in a branch first"
echo "3. Update any documentation referencing old workflows"
echo "4. Update any external tools/scripts using old workflow names"
echo "5. After verification, the deprecated/ folder can be removed"
echo ""
echo "✨ Migration complete!"
