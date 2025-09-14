#!/bin/bash
# Local test runner with multiple test levels
# Run this before pushing to production

set -e  # Exit on error

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test level from argument (default: quick)
TEST_LEVEL=${1:-quick}

echo -e "${BLUE}═══════════════════════════════════════════════${NC}"
echo -e "${BLUE}     LOCAL TEST RUNNER - Level: $TEST_LEVEL${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════${NC}"
echo ""

# Set up test environment
export FLASK_ENV=testing
export DATABASE_URL=sqlite:///test.db
export SECRET_KEY=test-secret-key
export MODAL_ML_BASE_URL=https://theresaanna--sentiment-ml-service-fastapi-app.modal.run
export SKIP_MODEL_PRELOAD=true

case $TEST_LEVEL in
    quick)
        echo -e "${YELLOW}Running QUICK tests (unit tests only)...${NC}"
        echo "This takes ~30 seconds"
        echo ""
        
        python -m pytest tests/ \
            -v \
            --tb=short \
            --maxfail=5 \
            --disable-warnings \
            -k "not integration and not slow and not redis" \
            --ignore=tests/test_enhanced_integration.py \
            --ignore=tests/test_redis_cloud.py \
            --ignore=tests/test_youtube_services.py
        ;;
    
    standard)
        echo -e "${YELLOW}Running STANDARD tests (unit + integration)...${NC}"
        echo "This takes ~2 minutes"
        echo ""
        
        python -m pytest tests/ \
            -v \
            --tb=short \
            --maxfail=10 \
            --disable-warnings \
            -k "not slow" \
            --ignore=tests/test_redis_cloud.py
        ;;
    
    full)
        echo -e "${YELLOW}Running FULL test suite...${NC}"
        echo "This takes ~5 minutes"
        echo ""
        
        python -m pytest tests/ \
            -v \
            --tb=short \
            --disable-warnings
        ;;
    
    modal)
        echo -e "${YELLOW}Testing Modal ML service integration...${NC}"
        echo ""
        python test_modal_integration.py
        ;;
    
    coverage)
        echo -e "${YELLOW}Running tests with coverage report...${NC}"
        echo ""
        
        python -m pytest tests/ \
            --cov=app \
            --cov-report=term-missing \
            --cov-report=html \
            --disable-warnings \
            -k "not slow and not redis"
        
        echo ""
        echo -e "${GREEN}Coverage report generated in htmlcov/index.html${NC}"
        ;;
    
    *)
        echo -e "${RED}Invalid test level: $TEST_LEVEL${NC}"
        echo "Usage: ./run_local_tests.sh [quick|standard|full|modal|coverage]"
        echo ""
        echo "  quick    - Fast unit tests only (~30s)"
        echo "  standard - Unit + integration tests (~2min)"
        echo "  full     - Complete test suite (~5min)"
        echo "  modal    - Test Modal ML service integration"
        echo "  coverage - Run with coverage report"
        exit 1
        ;;
esac

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════${NC}"
    echo -e "${GREEN}     ✅ All tests passed successfully!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════${NC}"
else
    echo ""
    echo -e "${RED}═══════════════════════════════════════════════${NC}"
    echo -e "${RED}     ❌ Some tests failed${NC}"
    echo -e "${RED}═══════════════════════════════════════════════${NC}"
    exit 1
fi