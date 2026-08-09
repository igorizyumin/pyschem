"""Run the project's test suite.

Usage examples::

    python run_tests.py
    python run_tests.py -v
    python run_tests.py tests.test_regressions.TestNetRegression

The repository root is added to ``sys.path`` so this command behaves the same
when launched from the project directory or from another working directory.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
TESTS_DIR = PROJECT_ROOT / "tests"


def main() -> int:
    """Discover and run all tests, or run explicitly named tests."""
    sys.path.insert(0, str(PROJECT_ROOT))

    args = sys.argv[1:]
    verbosity = 2
    if "-q" in args or "--quiet" in args:
        verbosity = 0
        args = [arg for arg in args if arg not in {"-q", "--quiet"}]
    if "-v" in args or "--verbose" in args:
        verbosity = 2
        args = [arg for arg in args if arg not in {"-v", "--verbose"}]

    # If test names are supplied, run them directly; otherwise discover the
    # complete suite. This supports commands such as ``-v tests.test_net...``.
    if args:
        if any(arg.startswith("-") for arg in args):
            raise SystemExit(f"Unsupported option: {next(arg for arg in args if arg.startswith('-'))}")
        suite = unittest.defaultTestLoader.loadTestsFromNames(args)
    else:
        suite = unittest.defaultTestLoader.discover(
            start_dir=str(TESTS_DIR),
            pattern="test*.py",
            top_level_dir=str(PROJECT_ROOT),
        )

    result = unittest.TextTestRunner(verbosity=verbosity).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
