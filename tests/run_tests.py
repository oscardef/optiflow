#!/usr/bin/env python3
"""
Run all OptiFlow tests with a single command
============================================

Usage:
    python tests/run_tests.py              # Run all tests
    python tests/run_tests.py --unit       # Run only unit tests
    python tests/run_tests.py --integration # Run only integration tests
    python tests/run_tests.py --verbose    # Verbose output
    python tests/run_tests.py --coverage   # Run with coverage report

Examples:
    python tests/run_tests.py --unit --verbose
    python tests/run_tests.py --integration --coverage
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import pytest
except ImportError:
    print("❌ pytest not installed. Install with: pip install -r tests/requirements.txt")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Run OptiFlow tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Test selection
    parser.add_argument(
        "--unit", "-u",
        action="store_true",
        help="Run only unit tests (fast, no dependencies)"
    )
    parser.add_argument(
        "--integration", "-i",
        action="store_true",
        help="Run only integration tests (requires services)"
    )
    parser.add_argument(
        "--hardware", "-hw",
        action="store_true",
        help="Run only hardware tests (requires physical devices)"
    )
    
    # Output options
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Minimal output"
    )
    parser.add_argument(
        "--coverage", "-c",
        action="store_true",
        help="Run with coverage report"
    )
    parser.add_argument(
        "--html-report",
        action="store_true",
        help="Generate HTML coverage report"
    )
    
    # Test filtering
    parser.add_argument(
        "--failed", "-f",
        action="store_true",
        help="Re-run only failed tests from last run"
    )
    parser.add_argument(
        "--keyword", "-k",
        type=str,
        help="Run tests matching keyword expression"
    )
    
    args = parser.parse_args()
    
    # Build pytest arguments
    pytest_args = []
    
    # Test selection based on markers or paths
    if args.unit:
        pytest_args.extend(["-m", "unit"])
        print("🧪 Running unit tests...\n")
    elif args.integration:
        pytest_args.extend(["-m", "integration"])
        print("🔗 Running integration tests...\n")
    elif args.hardware:
        pytest_args.extend(["-m", "hardware"])
        print("🔌 Running hardware tests...\n")
    else:
        pytest_args.append("tests/")
        print("🚀 Running all tests...\n")
    
    # Verbosity
    if args.verbose:
        pytest_args.append("-v")
    elif args.quiet:
        pytest_args.append("-q")
    else:
        pytest_args.append("-v")  # Default to verbose
    
    # Show test summary
    pytest_args.append("-ra")
    
    # Coverage
    if args.coverage:
        pytest_args.extend([
            "--cov=backend/app",
            "--cov-report=term-missing"
        ])
        if args.html_report:
            pytest_args.append("--cov-report=html")
    
    # Failed tests only
    if args.failed:
        pytest_args.append("--lf")
    
    # Keyword filtering
    if args.keyword:
        pytest_args.extend(["-k", args.keyword])
    
    # Show locals on failure
    pytest_args.append("--showlocals")
    
    # Run pytest
    print(f"📋 Command: pytest {' '.join(pytest_args)}\n")
    print("=" * 70)
    
    exit_code = pytest.main(pytest_args)
    
    print("\n" + "=" * 70)
    if exit_code == 0:
        print("✅ All tests passed!")
    else:
        print(f"❌ Tests failed with exit code {exit_code}")
    
    if args.coverage and args.html_report:
        print("\n📊 Coverage report generated: htmlcov/index.html")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
