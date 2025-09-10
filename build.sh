#!/usr/bin/env bash
# Exit on error
set -o errexit

# Upgrade pip and install build tools first
pip install --upgrade pip setuptools wheel

# Install the requirements
pip install -r requirements.txt
