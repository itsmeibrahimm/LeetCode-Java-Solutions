import time
from typing import Any, Dict

import pytest
from starlette.testclient import TestClient

from app.commons.config.app_config import AppConfig
from app.commons.providers.stripe import stripe_models as models
from app.commons.providers.stripe.stripe_client import StripeTestClient
from app.payin.test_integration.integration_utils import (
    create_payer_v1,
    CreatePayerV1Request,
    create_payment_method_v1,
    CreatePaymentMethodV1Request,
    delete_payment_methods_v1,
)

V1_PAYMENT_METHODS_ENDPOINT = "/payin/api/v1/payment_methods"


def _get_payment_methods_url(payment_method_id: str):
    return f"{V1_PAYMENT_METHODS_ENDPOINT}/{payment_method_id}"


def _get_payment_methods_v1(
    client: TestClient, payment_method_id: Any
) -> Dict[str, Any]:
    response = client.get(_get_payment_methods_url(payment_method_id=payment_method_id))
    assert response.status_code == 200
    return response.json()


class TestPaymentMethodsV1:
    @pytest.fixture
    def stripe_client(self, stripe_api, app_config: AppConfig):
        stripe_api.enable_outbound()

        return StripeTestClient(
            [
                models.StripeClientSettings(
                    api_key=app_config.STRIPE_US_SECRET_KEY.value, country="US"
                )
            ]
        )

    def test_create_get_delete_payment_method(
        self, client: TestClient, stripe_client: StripeTestClient
    ):
        random_dd_payer_id: str = str(int(time.time() * 1e6))

        # create payer
        payer = create_payer_v1(
            client=client,
            request=CreatePayerV1Request(
                dd_payer_id=random_dd_payer_id,
                country="US",
                description="Integration Test test_create_payer()",
                payer_type="marketplace",
                email=(random_dd_payer_id + "@dd.com"),
            ),
        )

        # create payment_method
        payment_method = create_payment_method_v1(
            client=client,
            request=CreatePaymentMethodV1Request(
                payer_id=payer["id"], payment_gateway="stripe", token="tok_visa"
            ),
        )

        # get payment_method
        get_payment_method = _get_payment_methods_v1(
            client=client, payment_method_id=payment_method["id"]
        )
        assert payment_method == get_payment_method

        # delete payment_method
        delete_payment_methods_v1(client=client, payment_method_id=payment_method["id"])
