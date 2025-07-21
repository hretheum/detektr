#!/bin/bash
# Setup script for self-hosted runner deployment (no SSH needed)
# Usage: ./scripts/setup-github-secrets.sh

set -e

echo "🔧 Setting up GitHub secrets for self-hosted runner deployment..."
echo ""

# Repository name
REPO="hretheum/bezrobocie-detektor"

echo "📋 For self-hosted runner deployment, only GHCR login is needed:"
echo "   - GITHUB_TOKEN (auto-provided by GitHub Actions)"
echo "   - No SSH secrets required - runner runs on Nebula"
echo ""

echo "✅ Self-hosted runner deployment is ready!"
echo ""
echo "🚀 Next steps:"
echo "   1. Push changes to main branch"
echo "   2. Monitor deployment in GitHub Actions"
echo "   3. Check deployment status on Nebula"
echo ""
echo "🔗 GitHub Actions URL: https://github.com/$REPO/actions"
