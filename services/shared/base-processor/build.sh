#!/bin/bash
# Build script for base-processor package

set -e

echo "Building base-processor package..."

# Clean previous builds
rm -rf dist/ build/ ./*.egg-info src/*.egg-info

# Create dist directory
mkdir -p dist

# Build wheel using setuptools directly
python3 -m pip wheel . --no-deps -w dist 2>/dev/null || {
    echo "Note: pip wheel failed, trying alternative method..."
    # Alternative: create a simple setup.py for compatibility
    cat > setup.py << 'EOF'
from setuptools import setup
setup()
EOF
    python3 setup.py bdist_wheel
    rm setup.py
}

# Build source distribution
python3 -m tarfile -c dist/base_processor-1.0.0.tar.gz \
    pyproject.toml MANIFEST.in README.md LICENSE \
    src/

echo "Build complete. Packages in dist/"
ls -la dist/
