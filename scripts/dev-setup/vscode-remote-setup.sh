#!/bin/bash
# VS Code Remote Development Setup for Detektor Project

echo "=== VS Code Remote Development Setup ==="

# Check if VS Code CLI is available
if ! command -v code &> /dev/null; then
    echo "❌ VS Code CLI not found. Please install VS Code and ensure 'code' command is in PATH"
    echo "   On macOS: Open VS Code, press Cmd+Shift+P, run 'Shell Command: Install code command in PATH'"
    exit 1
fi

echo "✅ VS Code CLI found"

# Install required extensions
echo "📦 Installing VS Code extensions..."
code --install-extension ms-vscode-remote.remote-ssh
code --install-extension ms-vscode-remote.remote-ssh-edit
code --install-extension ms-vscode.remote-explorer
code --install-extension ms-vscode-remote.remote-containers
code --install-extension ms-python.python
code --install-extension ms-python.vscode-pylance
code --install-extension ms-azuretools.vscode-docker

echo "✅ Extensions installed"

# Create VS Code workspace settings
echo "📝 Creating workspace settings..."
mkdir -p .vscode

cat > .vscode/settings.json << 'EOF'
{
    "remote.SSH.defaultHost": "nebula",
    "remote.SSH.configFile": "~/.ssh/config",
    "docker.host": "ssh://nebula",
    "docker.context": "nebula",
    "python.defaultInterpreterPath": "/usr/bin/python3",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.formatting.provider": "black",
    "editor.formatOnSave": true,
    "editor.rulers": [80, 120],
    "files.exclude": {
        "**/__pycache__": true,
        "**/.pytest_cache": true,
        "**/*.pyc": true
    }
}
EOF

echo "✅ Workspace settings created"

# Create remote settings for the server
echo "📝 Creating remote settings..."
cat > .vscode/remote-settings.json << 'EOF'
{
    "terminal.integrated.defaultProfile.linux": "bash",
    "terminal.integrated.profiles.linux": {
        "bash": {
            "path": "/bin/bash",
            "icon": "terminal-bash"
        }
    },
    "python.terminal.activateEnvironment": true,
    "docker.environment": {
        "DOCKER_HOST": "unix:///var/run/docker.sock"
    }
}
EOF

echo "✅ Remote settings created"

echo ""
echo "🚀 Setup complete! Next steps:"
echo "1. Open VS Code"
echo "2. Press Cmd+Shift+P and run 'Remote-SSH: Connect to Host'"
echo "3. Select 'nebula' from the list"
echo "4. Open the project folder: /home/hretheum/detektor"
echo ""
echo "💡 Tips:"
echo "- Use 'code --remote ssh-remote+nebula /home/hretheum/detektor' to open directly"
echo "- Docker commands will automatically use the remote server"
echo "- Python debugging will work over SSH"