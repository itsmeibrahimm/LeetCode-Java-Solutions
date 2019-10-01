import random
from typing import Any, Dict

import pytest
from starlette.testclient import TestClient

from app.commons.config.app_config import AppConfig
from app.commons.providers.stripe import stripe_models as models
from app.commons.providers.stripe.stripe_client import StripeTestClient
from app.payin.test_integration.integration_utils import (
    create_payer_v1,
    CreatePayerV1Request,
    CreatePaymentMethodV0Request,
    create_payment_method_v0,
    delete_payment_methods_v0,
)

V0_PAYMENT_METHODS_ENDPOINT = "/payin/api/v0/payment_methods"


def _get_payment_methods_url_v0(payment_method_id_type: str, payment_method_id: str):
    return f"{V0_PAYMENT_METHODS_ENDPOINT}/{payment_method_id_type}/{payment_method_id}"


def _get_payment_methods_v0(
    client: TestClient, payment_method_id_type: Any, payment_method_id: Any
) -> Dict[str, Any]:
    response = client.get(
        _get_payment_methods_url_v0(
            payment_method_id_type=payment_method_id_type,
            payment_method_id=payment_method_id,
        )
    )
    assert response.status_code == 200
    return response.json()


class TestPaymentMethodsV0:
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
        random_dd_payer_id: str = str(random.randint(1, 100000))

        # create payer
        payer = create_payer_v1(
            client=client,
            request=CreatePayerV1Request(
                dd_payer_id=random_dd_payer_id,
                country="US",
                description="Integration Test test_create_get_delete_payment_method()",
                payer_type="store",
                email=(random_dd_payer_id + "@dd.com"),
            ),
        )

        # create payment_method
        payment_method = create_payment_method_v0(
            client=client,
            request=CreatePaymentMethodV0Request(
                stripe_customer_id=payer["payment_gateway_provider_customers"][0][
                    "payment_provider_customer_id"
                ],
                country="US",
                token="tok_visa",
                set_default=False,
                is_scanned=False,
                is_active=True,
                dd_stripe_customer_id=payer["dd_stripe_customer_id"],
            ),
        )

        # get payment_method by dd_stripe_card_id
        get_payment_method_by_card_id = _get_payment_methods_v0(
            client=client,
            payment_method_id_type="dd_stripe_card_id",
            payment_method_id=payment_method["dd_stripe_card_id"],
        )
        assert payment_method == get_payment_method_by_card_id

        # get payment_method by stripe_payment_method_id
        get_payment_method_by_stripe_id = _get_payment_methods_v0(
            client=client,
            payment_method_id_type="stripe_payment_method_id",
            payment_method_id=payment_method["payment_gateway_provider_details"][
                "payment_method_id"
            ],
        )
        assert get_payment_method_by_card_id == get_payment_method_by_stripe_id

        # delete payment_method
        delete_payment_methods_v0(
            client=client,
            payment_method_id_type="dd_stripe_card_id",
            payment_method_id=payment_method["dd_stripe_card_id"],
        )
