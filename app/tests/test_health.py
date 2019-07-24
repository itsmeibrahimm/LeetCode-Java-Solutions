import pytest

from starlette.testclient import TestClient
from app.main import app


@pytest.fixture(autouse=True)
def client():
    return TestClient(app)


def test_health(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
