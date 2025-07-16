#!/bin/bash
# Remote Development Sync Setup

echo "=== Setting up code synchronization Mac ↔ Ubuntu ==="

# Create project directory on remote if not exists
echo "📁 Creating remote project directory..."
ssh nebula "mkdir -p ~/detektor"

# Initial sync of project files
echo "🔄 Initial project sync..."
rsync -avz --exclude='.git' --exclude='__pycache__' --exclude='.env.decrypted' \
    --exclude='node_modules' --exclude='.pytest_cache' \
    ./ nebula:~/detektor/

echo "✅ Initial sync complete"

# Create .gitignore if not exists
if [ ! -f .gitignore ]; then
    echo "📝 Creating .gitignore..."
    cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
.venv/

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Docker
.env.decrypted
docker-compose.override.yml

# OS
.DS_Store
Thumbs.db

# Project specific
/data/
/logs/
/tmp/
*.log
EOF
fi

# Setup file watcher for continuous sync (optional)
echo "📝 Creating file watcher script..."
cat > scripts/dev-setup/watch-sync.sh << 'EOF'
#!/bin/bash
# Continuous file sync using fswatch (macOS) or inotify (Linux)

if command -v fswatch &> /dev/null; then
    echo "🔄 Starting file watcher with fswatch..."
    fswatch -o . -e ".git" -e "__pycache__" -e ".pytest_cache" | while read f; do
        rsync -avz --delete \
            --exclude='.git' \
            --exclude='__pycache__' \
            --exclude='.env.decrypted' \
            --exclude='node_modules' \
            --exclude='.pytest_cache' \
            ./ nebula:~/detektor/
        echo "✅ Synced at $(date '+%H:%M:%S')"
    done
else
    echo "❌ fswatch not found. Install with: brew install fswatch"
    exit 1
fi
EOF

chmod +x scripts/dev-setup/watch-sync.sh

echo "✅ Sync setup complete"
echo ""
echo "💡 Usage:"
echo "- Run './scripts/dev-setup/watch-sync.sh' for continuous sync"
echo "- Or use VS Code Remote-SSH for automatic sync"