import pytest
from starlette.testclient import TestClient

from app.main import app


# Temporary solution to only init test client in single session.
# Can scope this fixture to below session level since the main app object
# is a global singleton it's state is mutated and shared within a session.
# re create a new client will cause set_app_context complain on already set
# TODO actually fix this
@pytest.fixture(scope="session")
def client():
    with TestClient(app) as client:
        yield client
