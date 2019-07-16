import requests

from .utils import SERVICE_URI


def test_service_health_code():
    r = requests.get(SERVICE_URI + "/health/")
    assert r.status_code == 200


def test_service_deep_ping():
    r = requests.get(SERVICE_URI + "/health/deep-ping")
    assert r.status_code == 200
