#!/usr/bin/env python3
"""
Test runner script for the sentiment analyzer project.
Provides comprehensive testing with coverage reporting.
"""

import sys
import os
import argparse
import subprocess
from pathlib import Path


def run_command(cmd, cwd=None):
    """Run a command and return the result."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode


def install_test_dependencies():
    """Install test dependencies if needed."""
    deps = [
        'pytest>=7.4.2',
        'pytest-cov>=4.1.0',
        'pytest-flask>=1.2.0',
        'pytest-asyncio>=0.21.1',
        'fakeredis>=2.20.0',
        'coverage[toml]>=7.3.0'
    ]
    
    print("Installing test dependencies...")
    cmd = [sys.executable, '-m', 'pip', 'install'] + deps
    return run_command(cmd)


def run_tests(args):
    """Run the test suite with specified options."""
    project_root = Path(__file__).parent
    tests_dir = project_root / 'tests'
    
    # Base pytest command
    cmd = [sys.executable, '-m', 'pytest']
    
    # Add verbosity
    if args.verbose:
        cmd.append('-vv')
    else:
        cmd.append('-v')
    
    # Add coverage options
    if args.coverage:
        cmd.extend([
            '--cov=app',
            '--cov-report=term-missing',
            '--cov-report=html:htmlcov',
            f'--cov-report=xml:{project_root}/coverage.xml'
        ])
        
        if args.coverage_min:
            cmd.append(f'--cov-fail-under={args.coverage_min}')
    
    # Add specific test file or directory
    if args.test_path:
        test_path = Path(args.test_path)
        if not test_path.is_absolute():
            test_path = project_root / test_path
        cmd.append(str(test_path))
    else:
        cmd.append(str(tests_dir))
    
    # Add test filter
    if args.filter:
        cmd.extend(['-k', args.filter])
    
    # Add markers
    if args.markers:
        cmd.extend(['-m', args.markers])
    
    # Fail fast
    if args.fail_fast:
        cmd.append('-x')
    
    # Show local variables in tracebacks
    if args.show_locals:
        cmd.append('-l')
    
    # Capture output
    if args.capture == 'no':
        cmd.append('-s')
    elif args.capture == 'sys':
        cmd.append('--capture=sys')
    
    # Number of parallel workers
    if args.parallel:
        cmd.extend(['-n', str(args.parallel)])
    
    # Run tests
    return run_command(cmd, cwd=project_root)


def run_specific_test_suite(suite_name):
    """Run a specific test suite."""
    suites = {
        'models': 'tests/test_models.py',
        'auth': 'tests/test_auth.py',
        'sentiment': 'tests/test_sentiment_analyzers.py',
        'youtube': 'tests/test_youtube_services.py',
        'ml': 'tests/test_ml_components.py',
        'utils': 'tests/test_utilities.py',
        'routes': 'tests/test_routes.py',
        'integration': 'tests/test_*integration*.py',
        'unit': 'tests/test_*.py -m "not integration"',
    }
    
    if suite_name not in suites:
        print(f"Unknown test suite: {suite_name}")
        print(f"Available suites: {', '.join(suites.keys())}")
        return 1
    
    project_root = Path(__file__).parent
    cmd = [
        sys.executable, '-m', 'pytest', '-v',
        '--cov=app', '--cov-report=term-missing'
    ]
    
    test_path = suites[suite_name]
    if ' -m ' in test_path:
        parts = test_path.split(' -m ')
        cmd.append(parts[0])
        cmd.extend(['-m', parts[1].strip('"')])
    else:
        cmd.append(test_path)
    
    return run_command(cmd, cwd=project_root)


def generate_coverage_report():
    """Generate detailed coverage report."""
    project_root = Path(__file__).parent
    
    print("\nGenerating coverage reports...")
    
    # Generate HTML report
    cmd = [sys.executable, '-m', 'coverage', 'html']
    run_command(cmd, cwd=project_root)
    
    # Generate XML report for CI/CD
    cmd = [sys.executable, '-m', 'coverage', 'xml']
    run_command(cmd, cwd=project_root)
    
    # Display report in terminal
    cmd = [sys.executable, '-m', 'coverage', 'report']
    run_command(cmd, cwd=project_root)
    
    print(f"\nHTML coverage report generated at: {project_root}/htmlcov/index.html")
    return 0


def run_linting():
    """Run code linting checks."""
    project_root = Path(__file__).parent
    
    print("\nRunning linting checks...")
    
    # Run flake8
    cmd = [sys.executable, '-m', 'flake8', 'app', 'tests', '--max-line-length=120']
    result = run_command(cmd, cwd=project_root)
    
    if result != 0:
        print("Linting failed!")
        return result
    
    print("Linting passed!")
    return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Run tests for the sentiment analyzer project'
    )
    
    parser.add_argument(
        'command',
        nargs='?',
        default='test',
        choices=['test', 'coverage', 'lint', 'install', 'all', 'suite'],
        help='Command to run (default: test)'
    )
    
    parser.add_argument(
        '--suite',
        help='Run specific test suite (models, auth, sentiment, youtube, ml, utils, routes)'
    )
    
    parser.add_argument(
        '--test-path',
        help='Path to specific test file or directory'
    )
    
    parser.add_argument(
        '-k', '--filter',
        help='Only run tests matching the given substring expression'
    )
    
    parser.add_argument(
        '-m', '--markers',
        help='Only run tests matching given mark expression'
    )
    
    parser.add_argument(
        '--coverage',
        action='store_true',
        help='Generate coverage report'
    )
    
    parser.add_argument(
        '--coverage-min',
        type=int,
        help='Minimum coverage percentage required'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose output'
    )
    
    parser.add_argument(
        '-x', '--fail-fast',
        action='store_true',
        help='Stop on first failure'
    )
    
    parser.add_argument(
        '-l', '--show-locals',
        action='store_true',
        help='Show local variables in tracebacks'
    )
    
    parser.add_argument(
        '--capture',
        choices=['yes', 'no', 'sys'],
        default='yes',
        help='Per-test capturing method'
    )
    
    parser.add_argument(
        '-n', '--parallel',
        type=int,
        help='Number of parallel test workers'
    )
    
    args = parser.parse_args()
    
    # Handle commands
    if args.command == 'install':
        return install_test_dependencies()
    
    elif args.command == 'lint':
        return run_linting()
    
    elif args.command == 'coverage':
        args.coverage = True
        result = run_tests(args)
        if result == 0:
            generate_coverage_report()
        return result
    
    elif args.command == 'suite':
        if not args.suite:
            print("Please specify a test suite with --suite")
            return 1
        return run_specific_test_suite(args.suite)
    
    elif args.command == 'all':
        # Run linting
        result = run_linting()
        if result != 0:
            return result
        
        # Run tests with coverage
        args.coverage = True
        result = run_tests(args)
        if result == 0:
            generate_coverage_report()
        return result
    
    else:  # test command
        return run_tests(args)


if __name__ == '__main__':
    sys.exit(main())