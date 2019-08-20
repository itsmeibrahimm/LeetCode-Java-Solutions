import os
from enum import Enum

import pytest
from _pytest.fixtures import FixtureRequest


class TestEnv(str, Enum):
    """
    defines environment of targeted service
    """

    prod = "prod"
    staging = "staging"
    local = "local"


def current_test_env() -> TestEnv:
    env_str = os.getenv("TEST_ENV")
    assert env_str, "TEST_ENV is not set in ./infra/{prod|staging|local}/data.yaml"
    return TestEnv(env_str.lower())


@pytest.fixture(
    scope="function", autouse=True
)  # !!DO NOT!! remove autouse or change scope
def skip_tests_per_env(request: FixtureRequest):
    """
    Intentionally skip any test case which is not marked with
    "pytest.mark.run_in_prod" or "pytest.mark.run_in_prod_only".
    Any test cases running against prod need to be explicitly specified to avoid accidentally write.
    """

    test_case_markers = request.node.own_markers
    current_env = current_test_env()

    if (
        pytest.mark.run_in_prod.mark not in test_case_markers
        and pytest.mark.run_in_prod_only.mark not in test_case_markers
        and current_env == TestEnv.prod
    ):
        pytest.skip("skipping prod excluded tests")

    if (
        pytest.mark.run_in_prod_only.mark in test_case_markers
        and current_env != TestEnv.prod
    ):
        pytest.skip("skipping prod only tests")
