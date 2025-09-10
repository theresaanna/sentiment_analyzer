#!/bin/bash
# Quick admin creation for Railway
# Usage: railway run bash scripts/quick_admin.sh

echo "Creating admin user on Railway..."
python scripts/create_admin.py --email "${ADMIN_EMAIL:-admin@example.com}" --password "${ADMIN_PASSWORD:-changeme123}" --name "${ADMIN_NAME:-Admin}"
