import random
from typing import Any, Dict

from starlette.testclient import TestClient

from app.commons.providers.stripe.stripe_client import StripeTestClient
from app.commons.types import CountryCode
from app.payin.core.payment_method.types import PaymentMethodSortKey
from app.payin.test_integration.integration_utils import (
    create_payer_v1,
    CreatePayerV1Request,
    CreatePaymentMethodV0Request,
    create_payment_method_v0,
    delete_payment_methods_v0,
    list_payment_method_v0,
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
    def test_create_get_delete_payment_method(
        self, client: TestClient, stripe_client: StripeTestClient
    ):
        random_payer_reference_id: str = str(random.randint(1, 100000))

        # create payer
        payer = create_payer_v1(
            client=client,
            request=CreatePayerV1Request(
                payer_reference_id=random_payer_reference_id,
                country="US",
                description="Integration Test test_create_get_delete_payment_method()",
                payer_reference_id_type="dd_drive_store_id",
                email=(random_payer_reference_id + "@dd.com"),
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
                legacy_dd_stripe_customer_id=payer["legacy_dd_stripe_customer_id"],
            ),
        )

        assert (
            payment_method["payer_reference_id"]
            == payer["payer_correlation_ids"]["payer_reference_id"]
        )
        assert (
            payment_method["payer_reference_id_type"]
            == payer["payer_correlation_ids"]["payer_reference_id_type"]
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

        assert (
            get_payment_method_by_card_id["payer_reference_id"]
            == payer["payer_correlation_ids"]["payer_reference_id"]
        )
        assert (
            get_payment_method_by_card_id["payer_reference_id_type"]
            == payer["payer_correlation_ids"]["payer_reference_id_type"]
        )

        # delete payment_method
        delete_payment_methods_v0(
            client=client,
            payment_method_id_type="dd_stripe_card_id",
            payment_method_id=payment_method["dd_stripe_card_id"],
        )

    def test_list_payment_method_by_stripe_customer_id(
        self, client: TestClient, stripe_client: StripeTestClient
    ):
        # create payer
        random_payer_reference_id: str = str(random.randint(1, 100000))
        payer = create_payer_v1(
            client=client,
            request=CreatePayerV1Request(
                payer_reference_id=random_payer_reference_id,
                country="US",
                description="Integration Test test_list_payment_method_by_stripe_customer_id()",
                payer_reference_id_type="dd_drive_store_id",
                email=(random_payer_reference_id + "@dd.com"),
            ),
        )

        # create two payment_methods
        payment_method_one = create_payment_method_v0(
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
                legacy_dd_stripe_customer_id=payer["legacy_dd_stripe_customer_id"],
            ),
        )
        assert (
            payment_method_one["payer_reference_id"]
            == payer["payer_correlation_ids"]["payer_reference_id"]
        )
        assert (
            payment_method_one["payer_reference_id_type"]
            == payer["payer_correlation_ids"]["payer_reference_id_type"]
        )
        payment_method_two = create_payment_method_v0(
            client=client,
            request=CreatePaymentMethodV0Request(
                stripe_customer_id=payer["payment_gateway_provider_customers"][0][
                    "payment_provider_customer_id"
                ],
                country="US",
                token="tok_mastercard",
                set_default=False,
                is_scanned=False,
                is_active=False,
                legacy_dd_stripe_customer_id=payer["legacy_dd_stripe_customer_id"],
            ),
        )
        assert (
            payment_method_two["payer_reference_id"]
            == payer["payer_correlation_ids"]["payer_reference_id"]
        )
        assert (
            payment_method_two["payer_reference_id_type"]
            == payer["payer_correlation_ids"]["payer_reference_id_type"]
        )

        # Get all payment methods
        payment_method_list = list_payment_method_v0(
            client=client,
            dd_consumer_id=None,
            stripe_customer_id=payer["payment_gateway_provider_customers"][0][
                "payment_provider_customer_id"
            ],
            country=CountryCode.US,
            active_only=False,
            sort_by=PaymentMethodSortKey.CREATED_AT,
            force_update=False,
        )
        assert payment_method_list["count"] == 2
        assert payment_method_list["has_more"] is False
        assert payment_method_one in payment_method_list["data"]
        assert payment_method_two in payment_method_list["data"]
        assert (
            payment_method_list["data"][0]["payer_reference_id"]
            == payer["payer_correlation_ids"]["payer_reference_id"]
        )
        assert (
            payment_method_list["data"][0]["payer_reference_id_type"]
            == payer["payer_correlation_ids"]["payer_reference_id_type"]
        )
        assert (
            payment_method_list["data"][1]["payer_reference_id"]
            == payer["payer_correlation_ids"]["payer_reference_id"]
        )
        assert (
            payment_method_list["data"][1]["payer_reference_id_type"]
            == payer["payer_correlation_ids"]["payer_reference_id_type"]
        )

        # Get active payment methods
        payment_method_list = list_payment_method_v0(
            client=client,
            dd_consumer_id=None,
            stripe_customer_id=payer["payment_gateway_provider_customers"][0][
                "payment_provider_customer_id"
            ],
            country=CountryCode.US,
            active_only=True,
            sort_by=PaymentMethodSortKey.CREATED_AT,
            force_update=False,
        )
        assert payment_method_list["count"] == 1
        assert payment_method_list["has_more"] is False
        assert payment_method_one in payment_method_list["data"]
        assert payment_method_two not in payment_method_list["data"]
        assert (
            payment_method_list["data"][0]["payer_reference_id"]
            == payer["payer_correlation_ids"]["payer_reference_id"]
        )
        assert (
            payment_method_list["data"][0]["payer_reference_id_type"]
            == payer["payer_correlation_ids"]["payer_reference_id_type"]
        )
