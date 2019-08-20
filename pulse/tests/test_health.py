import pytest
import requests

from .utils import SERVICE_URI


@pytest.mark.run_in_prod
def test_service_health_code():
    r = requests.get(SERVICE_URI + "/health")
    assert r.status_code == 200
