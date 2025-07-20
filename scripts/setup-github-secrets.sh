#!/bin/bash
# Script to help set up GitHub secrets for CI/CD

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== GitHub Secrets Setup for Detektor CI/CD ===${NC}"
echo ""

# Check if gh CLI is authenticated
if ! gh auth status &>/dev/null; then
    echo -e "${RED}❌ GitHub CLI not authenticated. Run: gh auth login${NC}"
    exit 1
fi

echo -e "${GREEN}✓ GitHub CLI authenticated${NC}"
echo ""

# Function to set a secret
set_secret() {
    local name=$1
    local value=$2

    echo -n "Setting $name... "
    if echo "$value" | gh secret set "$name" 2>/dev/null; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
        return 1
    fi
}

# Get repository info
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
echo -e "Repository: ${YELLOW}$REPO${NC}"
echo ""

# Check for required values
echo "Checking for required values..."
echo ""

# 1. NEBULA_SSH_KEY
echo "1. NEBULA_SSH_KEY - SSH private key for Nebula server"
echo "   Available keys:"
for f in ~/.ssh/id_*; do [[ -f "$f" && ! "$f" =~ \.pub$ ]] && echo "   - $f"; done 2>/dev/null || true
echo ""
read -r -p "Enter the path to SSH private key for Nebula (e.g., ~/.ssh/id_ed25519): " SSH_KEY_PATH

if [[ -f "$SSH_KEY_PATH" ]]; then
    SSH_KEY_VALUE=$(cat "$SSH_KEY_PATH")
    echo -e "${GREEN}✓ SSH key found${NC}"
else
    echo -e "${RED}❌ SSH key not found at $SSH_KEY_PATH${NC}"
    exit 1
fi

# 2. NEBULA_HOST
echo ""
echo "2. NEBULA_HOST - Hostname or IP of Nebula server"
read -r -p "Enter Nebula hostname/IP (e.g., nebula, 192.168.1.100): " NEBULA_HOST_VALUE

# 3. NEBULA_USER
echo ""
echo "3. NEBULA_USER - Username for SSH to Nebula"
read -r -p "Enter SSH username for Nebula (default: $USER): " NEBULA_USER_VALUE
NEBULA_USER_VALUE=${NEBULA_USER_VALUE:-$USER}

# 4. SOPS_AGE_KEY
echo ""
echo "4. SOPS_AGE_KEY - Age private key for SOPS decryption"
echo "   Looking for age key..."

# Try to find age key
if [[ -f "keys.txt" ]]; then
    echo -e "${GREEN}✓ Found keys.txt in current directory${NC}"
    SOPS_AGE_KEY_VALUE=$(cat keys.txt)
elif [[ -f ~/.config/age/keys.txt ]]; then
    echo -e "${GREEN}✓ Found age key in ~/.config/age/keys.txt${NC}"
    SOPS_AGE_KEY_VALUE=$(cat ~/.config/age/keys.txt)
else
    echo -e "${YELLOW}⚠ Age key not found. You need to create one or locate existing.${NC}"
    echo "   To create new: age-keygen -o keys.txt"
    echo "   To use existing: provide the AGE-SECRET-KEY-... value"
    read -r -p "Enter age private key or path to key file: " AGE_INPUT

    if [[ -f "$AGE_INPUT" ]]; then
        SOPS_AGE_KEY_VALUE=$(cat "$AGE_INPUT")
    else
        SOPS_AGE_KEY_VALUE="$AGE_INPUT"
    fi
fi

# Verify age key format
if [[ ! "$SOPS_AGE_KEY_VALUE" =~ ^AGE-SECRET-KEY- ]]; then
    echo -e "${RED}❌ Invalid age key format. Should start with AGE-SECRET-KEY-${NC}"
    exit 1
fi

# Summary
echo ""
echo -e "${YELLOW}=== Summary ===${NC}"
echo "NEBULA_SSH_KEY: $(echo "$SSH_KEY_PATH" | xargs basename)"
echo "NEBULA_HOST: $NEBULA_HOST_VALUE"
echo "NEBULA_USER: $NEBULA_USER_VALUE"
echo "SOPS_AGE_KEY: ${SOPS_AGE_KEY_VALUE:0:20}..."
echo ""

# Confirm
read -p "Do you want to set these secrets in GitHub? (y/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

# Set secrets
echo ""
echo "Setting GitHub secrets..."

set_secret "NEBULA_SSH_KEY" "$SSH_KEY_VALUE"
set_secret "NEBULA_HOST" "$NEBULA_HOST_VALUE"
set_secret "NEBULA_USER" "$NEBULA_USER_VALUE"
set_secret "SOPS_AGE_KEY" "$SOPS_AGE_KEY_VALUE"

# Verify
echo ""
echo "Verifying secrets..."
SECRETS_COUNT=$(gh secret list | wc -l | tr -d ' ')
echo -e "Total secrets: ${GREEN}$SECRETS_COUNT${NC}"

if [[ $SECRETS_COUNT -ge 4 ]]; then
    echo -e "${GREEN}✅ All secrets configured successfully!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Push code to trigger CI/CD: git push origin main"
    echo "2. Check workflow status: gh run list --workflow=deploy.yml"
else
    echo -e "${RED}❌ Some secrets might be missing. Check with: gh secret list${NC}"
    exit 1
fi
