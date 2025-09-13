#!/usr/bin/env python3
"""
Helper script to manage and fix failing tests incrementally.
"""
import subprocess
import sys
from pathlib import Path
import argparse


# Map of test categories and their current status
TEST_STATUS = {
    'models': {'status': '✅', 'passing': 20, 'total': 20, 'file': 'tests/test_models.py'},
    'auth': {'status': '⚠️', 'passing': 15, 'total': 25, 'file': 'tests/test_auth.py'},
    'ml_components': {'status': '⚠️', 'passing': 10, 'total': 20, 'file': 'tests/test_ml_components.py'},
    'sentiment': {'status': '❌', 'passing': 3, 'total': 12, 'file': 'tests/test_sentiment_analyzers.py'},
    'youtube': {'status': '❌', 'passing': 0, 'total': 15, 'file': 'tests/test_youtube_services.py'},
    'utilities': {'status': '❌', 'passing': 5, 'total': 17, 'file': 'tests/test_utilities.py'},
    'routes': {'status': '❌', 'passing': 10, 'total': 37, 'file': 'tests/test_routes.py'},
}


def run_command(cmd):
    """Run a command and return the result."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def show_status():
    """Show current test status."""
    print("\n" + "="*60)
    print("TEST SUITE STATUS")
    print("="*60)
    
    total_passing = sum(t['passing'] for t in TEST_STATUS.values())
    total_tests = sum(t['total'] for t in TEST_STATUS.values())
    percentage = (total_passing / total_tests) * 100 if total_tests > 0 else 0
    
    print(f"\nOverall: {total_passing}/{total_tests} tests passing ({percentage:.1f}%)")
    print("\nBy Module:")
    
    for name, info in TEST_STATUS.items():
        pct = (info['passing'] / info['total']) * 100 if info['total'] > 0 else 0
        print(f"  {info['status']} {name:15} {info['passing']:3}/{info['total']:3} ({pct:5.1f}%) - {info['file']}")
    
    print("\nLegend: ✅ = All passing, ⚠️ = Partially passing, ❌ = Many failures")
    print("="*60 + "\n")


def run_specific_test(category):
    """Run tests for a specific category."""
    if category not in TEST_STATUS:
        print(f"Unknown category: {category}")
        print(f"Available: {', '.join(TEST_STATUS.keys())}")
        return 1
    
    test_file = TEST_STATUS[category]['file']
    print(f"\nRunning tests for {category} ({test_file})...")
    
    cmd = f"python run_tests.py test --test-path {test_file} -v"
    returncode, stdout, stderr = run_command(cmd)
    
    # Parse results
    if "passed" in stdout:
        # Try to extract pass/fail counts
        for line in stdout.split('\n'):
            if 'passed' in line and ('failed' in line or 'error' in line):
                print(f"\nResults: {line}")
                break
    
    return returncode


def mark_failing_tests(category, skip=True):
    """Mark failing tests in a category to skip them temporarily."""
    if category not in TEST_STATUS:
        print(f"Unknown category: {category}")
        return 1
    
    test_file = Path(TEST_STATUS[category]['file'])
    
    if not test_file.exists():
        print(f"Test file not found: {test_file}")
        return 1
    
    print(f"\n{'Marking' if skip else 'Unmarking'} failing tests in {test_file}...")
    
    # This is a placeholder - in practice you'd parse test results
    # and add @pytest.mark.skip decorators to failing tests
    print("This would add/remove @pytest.mark.skip decorators to failing tests")
    print("For now, manually add this decorator to failing tests:")
    print("  @pytest.mark.skip(reason='Needs fixing')")
    
    return 0


def suggest_fixes(category):
    """Suggest fixes for common test failures."""
    suggestions = {
        'youtube': """
Common fixes for YouTube service tests:
1. Mock the 'build' function from googleapiclient.discovery
2. Ensure mock returns have the correct structure
3. Check that service methods actually exist
Example:
    @patch('app.services.youtube_service.build')
    def test_youtube(self, mock_build):
        mock_youtube = MagicMock()
        mock_build.return_value = mock_youtube
        """,
        
        'utilities': """
Common fixes for utility tests:
1. Email tests: Mock Flask-Mail properly
2. Cache tests: Use fakeredis or mock redis client
3. Model manager: Mock the actual model loading
Example:
    @patch('app.email.mail')
    def test_email(self, mock_mail):
        mock_mail.send.return_value = None
        """,
        
        'sentiment': """
Common fixes for sentiment analyzer tests:
1. Mock the model manager properly
2. Ensure tokenizer and model mocks return correct types
3. Check for missing methods like _extract_features
Example:
    @patch('app.science.sentiment_analyzer.get_model_manager')
    def test_sentiment(self, mock_manager):
        mock_manager.return_value.get_roberta_sentiment.return_value = (mock_tokenizer, mock_model)
        """,
        
        'routes': """
Common fixes for route tests:
1. Ensure test client is properly authenticated
2. Mock external services (Stripe, YouTube)
3. Check route URLs match actual implementation
Example:
    def test_route(self, authenticated_client):
        response = authenticated_client.get('/actual/route')
        """
    }
    
    if category in suggestions:
        print(suggestions[category])
    else:
        print(f"No specific suggestions for {category} yet.")


def main():
    parser = argparse.ArgumentParser(description='Helper to fix failing tests')
    parser.add_argument('command', choices=['status', 'run', 'skip', 'unskip', 'suggest', 'next'],
                        help='Command to run')
    parser.add_argument('--category', help='Test category (models, auth, ml_components, etc.)')
    
    args = parser.parse_args()
    
    if args.command == 'status':
        show_status()
    
    elif args.command == 'run':
        if args.category:
            run_specific_test(args.category)
        else:
            print("Please specify --category")
    
    elif args.command == 'skip':
        if args.category:
            mark_failing_tests(args.category, skip=True)
        else:
            print("Please specify --category")
    
    elif args.command == 'unskip':
        if args.category:
            mark_failing_tests(args.category, skip=False)
        else:
            print("Please specify --category")
    
    elif args.command == 'suggest':
        if args.category:
            suggest_fixes(args.category)
        else:
            print("Please specify --category")
    
    elif args.command == 'next':
        # Find next category to fix
        for name, info in TEST_STATUS.items():
            if info['status'] != '✅':
                print(f"\nNext to fix: {name}")
                print(f"Status: {info['passing']}/{info['total']} passing")
                print(f"Run: python fix_tests.py run --category {name}")
                print(f"Get suggestions: python fix_tests.py suggest --category {name}")
                break
        else:
            print("All tests are passing! 🎉")


if __name__ == '__main__':
    main()