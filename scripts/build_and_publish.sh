#!/usr/bin/env bash
set -e

echo "Building TLCM Engine for PyPI..."

# Clean old dists
rm -rf dist/ build/ *.egg-info

# Install build dependencies
python -m pip install --upgrade pip build twine

# Build Wheel and Source Distribution
python -m build

echo "Build complete. Running basic checks..."
twine check dist/*

echo "Publishing to PyPI..."
# This requires TWINE_USERNAME and TWINE_PASSWORD env vars,
# or a .pypirc file.
twine upload dist/*

echo "TLCM Engine successfully published!"
