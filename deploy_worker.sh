#!/bin/bash

echo "Deploying worker service to Railway..."

# Create a new Railway service for the worker
echo "Creating worker service..."

# Deploy using the worker configuration
railway up -d --service worker

echo "Worker service deployment initiated!"
echo ""
echo "Next steps:"
echo "1. Go to your Railway dashboard: https://railway.app/dashboard"
echo "2. Find your project 'lavish-renewal'"
echo "3. You should see a new 'worker' service"
echo "4. Make sure it has the same environment variables as your web service"
echo ""
echo "The worker will use the start command from railway.worker.json:"
echo "  python analysis_worker.py"