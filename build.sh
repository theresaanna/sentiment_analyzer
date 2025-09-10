#!/usr/bin/env bash
# Exit on error
set -o errexit

# Print Python version for debugging
echo "Python version:"
python --version
echo "Pip version:"
pip --version

# Favor wheels and avoid isolated build envs that miss setuptools
export PIP_PREFER_BINARY=1
export PIP_NO_BUILD_ISOLATION=1

# Ensure we have the latest build tools
echo "Installing build tools..."
python -m pip install --upgrade pip==25.2
python -m pip install --upgrade setuptools>=70.0.0 wheel>=0.41.0

# Check which requirements file to use
if [ -f "requirements-render.txt" ]; then
    echo "Using requirements-render.txt for installation..."
    REQUIREMENTS_FILE="requirements-render.txt"
else
    echo "Using requirements.txt for installation..."
    REQUIREMENTS_FILE="requirements.txt"
fi

# Install PyTorch CPU version first to avoid memory issues
echo "Installing PyTorch CPU version..."
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu

# Install the rest of the requirements
echo "Installing remaining requirements from $REQUIREMENTS_FILE..."
python -m pip install -r $REQUIREMENTS_FILE

# Download NLTK data if needed
echo "Downloading NLTK data if needed..."
python -c "import nltk; nltk.download('vader_lexicon', quiet=True)" 2>/dev/null || true

echo "Build completed successfully!"
