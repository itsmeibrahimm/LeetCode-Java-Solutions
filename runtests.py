#!/usr/bin/env python

"""
Quick/dirty wrapper script to run py.test tests
"""
import argparse
import os
import sys

import pytest

DEFAULT_ARGS = ["--junitxml", "pytest-report.xml", "app/"]


def main():
    parser = argparse.ArgumentParser(add_help=False)
    args, pytest_args = parser.parse_known_args()

    if sys.argv[1:]:
        pytest_args = sys.argv[1:]
    else:
        pytest_args += DEFAULT_ARGS

    status = pytest.main(pytest_args)
    sys.exit(status)


if __name__ == "__main__":
    if os.getenv("DEBUGGER", "disabled").lower() == "enabled":
        from development import debug

        debug.bootstrap_debugger()

    main()
