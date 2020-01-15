import random
from typing import Any, Dict

import dateutil
from starlette.testclient import TestClient

from app.commons.providers.stripe.stripe_client import StripeTestClient
from app.commons.types import CountryCode
from app.payin.core.payment_method.types import PaymentMethodSortKey
from app.payin.test_integration.integration_utils import (
    create_payer_v1,
    CreatePayerV1Request,
    create_payment_method_v1,
    CreatePaymentMethodV1Request,
    delete_payment_methods_v1,
    list_payment_method_v1,
    list_payment_methods_v1_bad_request,
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

    def test_create_payment_method_by_payer_reference_id(
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
        payment_method = create_payment_method_v1(
            client=client,
            request=CreatePaymentMethodV1Request(
                payer_reference_id=payer["legacy_dd_stripe_customer_id"],
                payer_reference_id_type="legacy_dd_stripe_customer_id",
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
        random_payer_reference_id: str = str(random.randint(1, 100000))

        # create payer
        payer = create_payer_v1(
            client=client,
            request=CreatePayerV1Request(
                payer_reference_id=random_payer_reference_id,
                country="US",
                description="Integration Test test_create_duplicate_card()",
                payer_reference_id_type="dd_drive_store_id",
                email=(random_payer_reference_id + "@dd.com"),
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

    def test_list_payment_methods(
        self, client: TestClient, stripe_client: StripeTestClient
    ):
        random_payer_reference_id: str = str(random.randint(1, 100000))
        # create payer
        payer = create_payer_v1(
            client=client,
            request=CreatePayerV1Request(
                payer_reference_id=random_payer_reference_id,
                country="US",
                description="Integration Test test_create_duplicate_card()",
                payer_reference_id_type="dd_drive_store_id",
                email=(random_payer_reference_id + "@dd.com"),
            ),
        )

        # create two payment_method
        payment_method_one = create_payment_method_v1(
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
        payment_method_two = create_payment_method_v1(
            client=client,
            request=CreatePaymentMethodV1Request(
                payer_id=payer["id"],
                payment_gateway="stripe",
                token="tok_mastercard",
                set_default=False,
                is_scanned=False,
                is_active=False,
            ),
        )

        # List all payment methods
        payment_method_list = list_payment_method_v1(
            client=client,
            payer_id=payer["id"],
            active_only=False,
            sort_by=PaymentMethodSortKey.CREATED_AT,
            force_update=False,
            country=CountryCode.US,
        )
        assert payment_method_list["count"] == 2
        assert payment_method_list["has_more"] is False
        assert payment_method_one in payment_method_list["data"]
        assert payment_method_two in payment_method_list["data"]
        assert dateutil.parser.parse(
            payment_method_list["data"][0]["created_at"]
        ) < dateutil.parser.parse(payment_method_list["data"][1]["created_at"])

        # List only active payment methods for payer
        payment_method_list = list_payment_method_v1(
            client=client,
            payer_id=payer["id"],
            active_only=True,
            sort_by=PaymentMethodSortKey.CREATED_AT,
            force_update=False,
            country=CountryCode.US,
        )
        assert payment_method_list["count"] == 1
        assert payment_method_list["has_more"] is False
        assert payment_method_one in payment_method_list["data"]
        assert payment_method_two not in payment_method_list["data"]

    def test_list_payment_methods_by_payer_reference_id(
        self, client: TestClient, stripe_client: StripeTestClient
    ):
        random_payer_reference_id: str = str(random.randint(1, 100000))
        # create payer
        payer = create_payer_v1(
            client=client,
            request=CreatePayerV1Request(
                payer_reference_id=random_payer_reference_id,
                country="US",
                description="Integration Test test_create_duplicate_card()",
                payer_reference_id_type="dd_drive_store_id",
                email=(random_payer_reference_id + "@dd.com"),
            ),
        )

        # create two payment_method
        payment_method_one = create_payment_method_v1(
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
        payment_method_two = create_payment_method_v1(
            client=client,
            request=CreatePaymentMethodV1Request(
                payer_id=payer["id"],
                payment_gateway="stripe",
                token="tok_mastercard",
                set_default=False,
                is_scanned=False,
                is_active=False,
            ),
        )

        # List all payment methods
        payment_method_list = list_payment_method_v1(
            client=client,
            payer_reference_id=payer["legacy_dd_stripe_customer_id"],
            payer_reference_id_type="legacy_dd_stripe_customer_id",
            active_only=False,
            sort_by=PaymentMethodSortKey.CREATED_AT,
            force_update=False,
            country=CountryCode.US,
        )
        assert payment_method_list["count"] == 2
        assert payment_method_list["has_more"] is False
        assert payment_method_one in payment_method_list["data"]
        assert payment_method_two in payment_method_list["data"]
        assert dateutil.parser.parse(
            payment_method_list["data"][0]["created_at"]
        ) < dateutil.parser.parse(payment_method_list["data"][1]["created_at"])

        # List only active payment methods for payer
        payment_method_list = list_payment_method_v1(
            client=client,
            payer_reference_id=payer["legacy_dd_stripe_customer_id"],
            payer_reference_id_type="legacy_dd_stripe_customer_id",
            active_only=True,
            sort_by=PaymentMethodSortKey.CREATED_AT,
            force_update=False,
            country=CountryCode.US,
        )
        assert payment_method_list["count"] == 1
        assert payment_method_list["has_more"] is False
        assert payment_method_one in payment_method_list["data"]
        assert payment_method_two not in payment_method_list["data"]

    def test_list_payment_methods_invalid_input(
        self, client: TestClient, stripe_client: StripeTestClient
    ):
        random_payer_reference_id: str = str(random.randint(1, 100000))
        # create payer
        payer = create_payer_v1(
            client=client,
            request=CreatePayerV1Request(
                payer_reference_id=random_payer_reference_id,
                country="US",
                description="Integration Test test_create_duplicate_card()",
                payer_reference_id_type="dd_drive_store_id",
                email=(random_payer_reference_id + "@dd.com"),
            ),
        )

        # create two payment_method
        create_payment_method_v1(
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
        create_payment_method_v1(
            client=client,
            request=CreatePaymentMethodV1Request(
                payer_id=payer["id"],
                payment_gateway="stripe",
                token="tok_mastercard",
                set_default=False,
                is_scanned=False,
                is_active=False,
            ),
        )

        # List all payment methods with payer_id and payer_reference_id
        list_payment_methods_v1_bad_request(
            client=client,
            expected_http_code=400,
            expected_error_code="invalid_payer_reference_id",
            payer_id=payer["id"],
            payer_reference_id=payer["legacy_dd_stripe_customer_id"],
            payer_reference_id_type="legacy_dd_stripe_customer_id",
            active_only=False,
            sort_by=PaymentMethodSortKey.CREATED_AT,
            force_update=False,
            country=CountryCode.US,
        )

        # List all payment methods with missing payer_reference_id_type
        list_payment_methods_v1_bad_request(
            client=client,
            expected_http_code=400,
            expected_error_code="invalid_payer_reference_id",
            payer_reference_id=payer["legacy_dd_stripe_customer_id"],
            active_only=False,
            sort_by=PaymentMethodSortKey.CREATED_AT,
            force_update=False,
            country=CountryCode.US,
        )

        # List all payment methods with payer_id and payer_reference_id_type
        list_payment_methods_v1_bad_request(
            client=client,
            expected_http_code=400,
            expected_error_code="invalid_payer_reference_id",
            payer_id=payer["id"],
            payer_reference_id_type="legacy_dd_stripe_customer_id",
            active_only=False,
            sort_by=PaymentMethodSortKey.CREATED_AT,
            force_update=False,
            country=CountryCode.US,
        )
