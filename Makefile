# Makefile for Sentiment Analyzer
# Run tests and deploy easily without CI/CD

.PHONY: help test test-quick test-full test-modal deploy check clean

# Default target
help:
	@echo "Sentiment Analyzer - Development Commands"
	@echo "========================================="
	@echo ""
	@echo "Testing:"
	@echo "  make test        - Run standard test suite"
	@echo "  make test-quick  - Run quick unit tests only"
	@echo "  make test-full   - Run complete test suite"
	@echo "  make test-modal  - Test Modal ML integration"
	@echo "  make coverage    - Run tests with coverage report"
	@echo ""
	@echo "Deployment:"
	@echo "  make check       - Pre-deployment checks"
	@echo "  make deploy      - Test and deploy to production"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean       - Clean cache and temp files"
	@echo "  make setup       - Install dependencies"

# Run standard tests
test:
	@./run_local_tests.sh standard

# Run quick tests
test-quick:
	@./run_local_tests.sh quick

# Run full test suite
test-full:
	@./run_local_tests.sh full

# Test Modal integration
test-modal:
	@./run_local_tests.sh modal

# Run tests with coverage
coverage:
	@./run_local_tests.sh coverage

# Pre-deployment checks
check:
	@echo "Running pre-deployment checks..."
	@echo "================================"
	@echo "1. Checking Modal service..."
	@python test_modal_integration.py
	@echo ""
	@echo "2. Running quick tests..."
	@./run_local_tests.sh quick
	@echo ""
	@echo "✅ Pre-deployment checks passed!"

# Deploy to production (with tests)
deploy: check
	@echo ""
	@echo "Deploying to production..."
	@echo "================================"
	@git add .
	@git commit -m "Deploy to production" || true
	@git push origin main
	@echo ""
	@echo "✅ Deployed! Check Railway dashboard for status."
	@echo "   Run 'railway logs' to monitor deployment"

# Clean cache and temporary files
clean:
	@echo "Cleaning cache and temporary files..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name ".coverage" -delete 2>/dev/null || true
	@rm -rf htmlcov/ 2>/dev/null || true
	@rm -f test.db 2>/dev/null || true
	@echo "✅ Cleaned!"

# Setup development environment
setup:
	@echo "Setting up development environment..."
	@pip install -r requirements.txt
	@echo "✅ Setup complete!"