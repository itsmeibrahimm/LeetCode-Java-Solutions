#!/usr/bin/env python

"""
Quick/dirty wrapper script to run py.test tests
"""
import sys
import argparse
import pytest


DEFAULT_ARGS = ["--junitxml", "pytest-report.xml", "application/"]


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
    main()
