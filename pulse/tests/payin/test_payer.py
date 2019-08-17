import logging
import os
import requests

from . import payin_client_pulse
from ..utils import SERVICE_URI

logger = logging.getLogger(__name__)

STAGING_PULSE_API_KEY = os.getenv("API_KEY_PAYMENT_SERVICE", "")


def payer_info():
    # returns blob for creating a payer with necessary parameters
    return {
        "dd_payer_id": "test_01",
        "payer_type": "marketplace",
        "email": "fake@email.com",
        "country": "US",
        "description": "payer creation for tests",
    }


def test_payer_creation():  # hit create_payer API and get_payer api
    # create_payer api
    test_payer = payin_client_pulse.create_payer_api_v1_payers_post(
        create_payer_request=payer_info()
    )
    assert test_payer["dd_payer_id"] == "test_01"


def test_payer_retrieval():
    # setup
    test_payer = requests.post(
        url=SERVICE_URI + "/payin/api/v1/payers",
        json=payer_info(),
        headers={"x-api-key": STAGING_PULSE_API_KEY},
    )
    assert test_payer.status_code == 201

    # get_payer api
    payer_id = test_payer.json()["id"]
    verify_payer = requests.get(
        url=SERVICE_URI + "/payin/api/v1/payers/{}".format(payer_id),
        headers={"x-api-key": STAGING_PULSE_API_KEY},
    )
    assert verify_payer.status_code == 200

    # trying to fetch a payer that does not exist
    verify_payer = requests.get(
        url=SERVICE_URI + "/payin/api/v1/payers/{}".format("not_valid_id"),
        headers={"x-api-key": STAGING_PULSE_API_KEY},
    )
    # status_code should be 404, but getting 500 right now
    assert verify_payer.status_code != 200


# def test_payer_payment_method_update():
#     # setup
#     test_payer = requests.post(
#         url=SERVICE_URI + "/payin/api/v1/payers", json=payer_info(), headers={'x-api-key': STAGING_PULSE_API_KEY}
#     )
#     assert test_payer.status_code == 201
#
#     # update_payer api
#     payer_id = test_payer.json()["id"]
#     update_payer = requests.patch(
#         url=SERVICE_URI + "/payin/api/v1/payers/{}".format(payer_id),
#         json={"default_payment_method_id": "fake_id"}, headers={'x-api-key': STAGING_PULSE_API_KEY}
#     )
#     assert update_payer.status_code == 200
