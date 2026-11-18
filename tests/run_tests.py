"""Test runner script for Griductive Solver."""

import sys
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def run_all_tests():
    print("=" * 70)
    print("Running Griductive Logic Core Test Suites")
    print("=" * 70)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Discover and add test files
    suite.addTests(loader.discover(start_dir=str(PROJECT_ROOT / "tests"), pattern="test_*.py"))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("=" * 70)
    if result.wasSuccessful():
        print(f"SUCCESS: All {result.testsRun} tests passed successfully!")
        return 0
    else:
        print(f"FAILURE: {len(result.failures)} failures, {len(result.errors)} errors out of {result.testsRun} tests.")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
