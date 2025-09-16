#!/bin/bash

echo "🚀 Deploying both services to Railway..."
echo ""

# Deploy web service
echo "📦 Deploying web service..."
railway link 7cfed323-856d-48bc-9135-4040df5d83ef web
railway up -d

echo ""
echo "📦 Deploying worker service..."
# Deploy worker service
railway link 7cfed323-856d-48bc-9135-4040df5d83ef triumphant-peace
railway up -d

echo ""
echo "✅ Both services deployed successfully!"
echo ""
echo "Check deployment status at:"
echo "https://railway.app/project/7cfed323-856d-48bc-9135-4040df5d83ef"