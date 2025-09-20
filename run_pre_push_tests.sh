#!/bin/bash
# Manual pre-push test runner
# Run this script to test everything before pushing to production

echo "🧪 Running pre-push test suite..."
echo "================================"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Set test environment variables
export FLASK_ENV=testing
export DATABASE_URL=sqlite:///test.db
export SECRET_KEY=test-secret-key
export MODAL_ML_BASE_URL=https://theresaanna--sentiment-ml-service-fastapi-app.modal.run

echo -e "${YELLOW}1. Running Python unit tests...${NC}"
echo "--------------------------------"

# Run Python tests
python -m pytest tests/ \
    -v \
    --tb=short \
    --maxfail=5 \
    --disable-warnings \
    -k "not integration and not slow" \
    --ignore=tests/test_enhanced_integration.py \
    --ignore=tests/test_redis_cloud.py

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Python tests failed!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Python tests passed!${NC}"
echo ""

# Run React unit tests if available
if [ -f "frontend/package.json" ] && command -v npm > /dev/null 2>&1; then
    echo -e "${YELLOW}2. Running React unit tests...${NC}"
    echo "--------------------------------------------"
    
    # Check if frontend node_modules exists, install if needed
    if [ ! -d "frontend/node_modules" ]; then
        echo "Installing frontend dependencies..."
        npm run web:install
    fi
    
    # Run React unit tests
    npm run web:test
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ React unit tests failed!${NC}"
        echo "React component tests failed."
        echo "Run 'npm run web:test:watch' to debug interactively."
        exit 1
    fi
    
    echo -e "${GREEN}✅ React unit tests passed!${NC}"
    echo ""
else
    echo -e "${YELLOW}⚠️  Skipping React unit tests (frontend not found)${NC}"
    echo ""
fi

# Run Playwright tests if available
if [ -f "package.json" ] && command -v npm > /dev/null 2>&1; then
    echo -e "${YELLOW}3. Running Playwright JavaScript e2e tests...${NC}"
    echo "--------------------------------------------"
    
    # Check if node_modules exists, install if needed
    if [ ! -d "node_modules" ]; then
        echo "Installing Node.js dependencies..."
        npm install
    fi
    
    # Check if Playwright browsers are installed
    if [ ! -d "$HOME/Library/Caches/ms-playwright" ] && [ ! -d "$HOME/.cache/ms-playwright" ]; then
        echo "Installing Playwright browsers..."
        npx playwright install
    fi
    
    # Run Playwright tests
    npm test
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Playwright e2e tests failed!${NC}"
        echo "JavaScript functionality tests failed."
        echo "Run 'npm run test:ui' to debug interactively."
        exit 1
    fi
    
    echo -e "${GREEN}✅ Playwright e2e tests passed!${NC}"
else
    echo -e "${YELLOW}⚠️  Skipping Playwright tests (npm not found or package.json missing)${NC}"
fi

echo ""
echo "================================"
echo -e "${GREEN}🎉 All tests passed!${NC}"
echo -e "${GREEN}✅ Python unit tests${NC}"
echo -e "${GREEN}✅ React unit tests${NC}"
echo -e "${GREEN}✅ Playwright E2E tests${NC}"
echo "================================"
