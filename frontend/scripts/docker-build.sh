#!/bin/bash
# Docker build helper script
# This script ensures proper installation of dependencies for Docker builds

set -e

echo "Starting Docker-compatible build process..."

# Clean any existing installations
echo "Cleaning existing node_modules and package-lock..."
rm -rf node_modules package-lock.json

# Install dependencies with --force to ensure optional deps are installed
echo "Installing dependencies..."
npm install --force --verbose

# Run the build
echo "Building application..."
npm run build

echo "Build completed successfully!"