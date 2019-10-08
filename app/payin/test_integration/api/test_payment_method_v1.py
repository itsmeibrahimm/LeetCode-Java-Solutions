import random
from typing import Any, Dict

from starlette.testclient import TestClient

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
        payment_method = create_payment_method_v1(
            client=client,
            request=CreatePaymentMethodV1Request(
                payer_id=payer["id"],
                payment_gateway="stripe",
                token="tok_visa",
                set_default=False,
                is_scanned=False,
                is_active=True,
            ),
        )

        # get payment_method
        get_payment_method = _get_payment_methods_v1(
            client=client, payment_method_id=payment_method["id"]
        )
        assert payment_method == get_payment_method

        # delete payment_method
        delete_payment_methods_v1(client=client, payment_method_id=payment_method["id"])

    def test_create_duplicate_card(
        self, client: TestClient, stripe_client: StripeTestClient
    ):
        random_dd_payer_id: str = str(random.randint(1, 100000))

        # create payer
        payer = create_payer_v1(
            client=client,
            request=CreatePayerV1Request(
                dd_payer_id=random_dd_payer_id,
                country="US",
                description="Integration Test test_create_duplicate_card()",
                payer_type="store",
                email=(random_dd_payer_id + "@dd.com"),
            ),
        )

        # create payment_method
        payment_method = create_payment_method_v1(
            client=client,
            request=CreatePaymentMethodV1Request(
                payer_id=payer["id"],
                payment_gateway="stripe",
                token="tok_visa",
                set_default=False,
                is_scanned=False,
                is_active=True,
            ),
        )

        # create same payment_method again
        duplicate_payment_method = create_payment_method_v1(
            client=client,
            request=CreatePaymentMethodV1Request(
                payer_id=payer["id"],
                payment_gateway="stripe",
                token="tok_visa",
                set_default=False,
                is_scanned=False,
                is_active=True,
            ),
            # http_status=200,  # FIXME: PS should return 200 in duplication case
        )
        assert payment_method == duplicate_payment_method
