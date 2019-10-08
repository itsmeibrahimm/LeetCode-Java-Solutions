import random
from typing import Optional, Any, Dict

from pydantic import BaseModel
from starlette.testclient import TestClient

from app.commons.providers.stripe.stripe_client import StripeTestClient
from app.commons.providers.stripe.stripe_models import CustomerId, Customer
from app.payin.test_integration.integration_utils import (
    create_payer_v1,
    CreatePayerV1Request,
    PayinError,
    create_payment_method_v0,
    CreatePaymentMethodV0Request,
    delete_payment_methods_v0,
)

V0_PAYERS_ENDPOINT = "/payin/api/v0/payers"
V1_PAYERS_ENDPOINT = "/payin/api/v1/payers"


def _create_payer_url():
    return V1_PAYERS_ENDPOINT


def _get_payer_url(payer_id_type: str, payer_id: str):
    return f"{V0_PAYERS_ENDPOINT}/{payer_id_type}/{payer_id}"


def _update_payer_default_payment_method_url(payer_id_type: str, payer_id: str):
    return f"{V0_PAYERS_ENDPOINT}/{payer_id_type}/{payer_id}/default_payment_method"


class UpdatePayerV0Request(BaseModel):
    dd_stripe_card_id: Optional[Any]
    country: Optional[str]
    payer_type: Optional[str]


def _update_payer_v0(
    client: TestClient, payer_id_type: str, payer_id: Any, request: UpdatePayerV0Request
) -> Dict[str, Any]:
    update_payer_request = {
        "country": request.country,
        "default_payment_method": {"dd_stripe_card_id": request.dd_stripe_card_id},
    }
    response = client.post(
        _update_payer_default_payment_method_url(
            payer_id_type=payer_id_type, payer_id=payer_id
        ),
        json=update_payer_request,
    )
    assert response.status_code == 200
    return response.json()


def _update_payer_failure_v1(
    client: TestClient,
    payer_id_type: str,
    payer_id: Any,
    request: UpdatePayerV0Request,
    error: PayinError,
):
    update_payer_request: Dict[str, Any] = {
        "default_payment_method": {"dd_stripe_card_id": request.dd_stripe_card_id}
    }
    if request.payer_type:
        update_payer_request.update({"payer_type": str(request.payer_type)})
    response = client.post(
        _update_payer_default_payment_method_url(
            payer_id_type=payer_id_type, payer_id=payer_id
        ),
        json=update_payer_request,
    )
    assert response.status_code == error.http_status_code
    error_response: dict = response.json()
    assert error_response["error_code"] == error.error_code
    assert error_response["retryable"] == error.retryable


def _get_payer_failure_v1(
    client: TestClient, payer_id_type: Any, payer_id: Any, error: PayinError
):
    response = client.get(
        _get_payer_url(payer_id_type=payer_id_type, payer_id=payer_id)
    )
    assert response.status_code == error.http_status_code
    error_response: dict = response.json()
    assert error_response["error_code"] == error.error_code
    assert error_response["retryable"] == error.retryable


class TestPayersV0:
    def test_create_and_get_payer_by_stripe_customer_id(
        self, client: TestClient, stripe_client: StripeTestClient
    ):
        random_dd_payer_id: str = str(random.randint(1, 100000))
        payer_type: str = "marketplace"
        # create payer
        payer = create_payer_v1(
            client=client,
            request=CreatePayerV1Request(
                dd_payer_id=random_dd_payer_id,
                country="US",
                description="test_create_and_get_payer_by_stripe_customer_id",
                payer_type=payer_type,
                email=(random_dd_payer_id + "@dd.com"),
            ),
        )

        # get payer by stripe_customer_id
        response = client.get(
            _get_payer_url(
                payer_id_type="stripe_customer_id",
                payer_id=payer["payment_gateway_provider_customers"][0][
                    "payment_provider_customer_id"
                ],
            )
            + "?payer_type="
            + payer_type
        )
        assert response.status_code == 200
        get_payer: dict = response.json()
        assert payer == get_payer

        # get payer by stripe_customer_id with force_update
        response = client.get(
            _get_payer_url(
                payer_id_type="stripe_customer_id",
                payer_id=payer["payment_gateway_provider_customers"][0][
                    "payment_provider_customer_id"
                ],
            )
            + "?force_update=True"
            + "&payer_type="
            + payer_type
        )
        assert response.status_code == 200
        force_get_payer: dict = response.json()
        assert payer == force_get_payer

    def test_create_and_get_payer_by_dd_stripe_customer_id(
        self, client: TestClient, stripe_client: StripeTestClient
    ):
        random_dd_payer_id: str = str(random.randint(1, 100000))
        payer_type: str = "store"
        # create payer
        payer = create_payer_v1(
            client=client,
            request=CreatePayerV1Request(
                dd_payer_id=random_dd_payer_id,
                country="US",
                description="test_create_and_get_payer_by_dd_stripe_customer_id",
                payer_type=payer_type,
                email=(random_dd_payer_id + "@dd.com"),
            ),
        )

        # get payer by stripe_customer_id
        response = client.get(
            _get_payer_url(
                payer_id_type="dd_stripe_customer_serial_id",
                payer_id=payer["dd_stripe_customer_id"],
            )
        )
        assert response.status_code == 200
        get_payer: dict = response.json()
        assert payer == get_payer

        # get payer by stripe_customer_id with force_update
        response = client.get(
            _get_payer_url(
                payer_id_type="dd_stripe_customer_serial_id",
                payer_id=payer["dd_stripe_customer_id"],
            )
            + "?force_update=True"
        )
        assert response.status_code == 200
        force_get_payer: dict = response.json()
        assert payer == force_get_payer

    def test_force_get_payer_by_stripe_customer_id(
        self,
        client: TestClient,
        stripe_client: StripeTestClient,
        stripe_customer: Customer,
    ):
        # get payer by stripe_customer_id with force_update
        response = client.get(
            _get_payer_url(
                payer_id_type="stripe_customer_id", payer_id=stripe_customer.id
            )
            + "?force_update=True"
        )
        assert response.status_code == 200
        force_get_payer: dict = response.json()
        assert (
            force_get_payer["payment_gateway_provider_customers"][0][
                "payment_provider_customer_id"
            ]
            == stripe_customer.id
        )

    def test_not_found_without_force_update(
        self,
        client: TestClient,
        stripe_client: StripeTestClient,
        stripe_customer: CustomerId,
    ):
        # get payer by stripe_customer_id without force_update
        response = client.get(
            _get_payer_url(payer_id_type="stripe_customer_id", payer_id=stripe_customer)
        )
        assert response.status_code == 404

    def test_update_cx_default_payment_method(
        self,
        client: TestClient,
        stripe_client: StripeTestClient,
        stripe_customer: Customer,
    ):
        # create payment_method
        payment_method = create_payment_method_v0(
            client=client,
            request=CreatePaymentMethodV0Request(
                stripe_customer_id=stripe_customer.id,
                country="US",
                token="tok_visa",
                set_default=False,
                is_scanned=False,
                is_active=True,
                payer_type="marketplace",
                dd_consumer_id="5",  # pre seeded consumer in maindb.consumer table
            ),
        )

        # set default_payment_method
        update_payer = _update_payer_v0(
            client=client,
            payer_id=stripe_customer.id,
            payer_id_type="stripe_customer_id",
            request=UpdatePayerV0Request(
                dd_stripe_card_id=payment_method["dd_stripe_card_id"],
                country="US",
                payer_type="marketplace",
            ),
        )
        assert (
            update_payer["payment_gateway_provider_customers"][0][
                "default_payment_method_id"
            ]
            == payment_method["payment_gateway_provider_details"]["payment_method_id"]
        )

        # delete payment_method
        delete_payment_methods_v0(
            client=client,
            payment_method_id_type="dd_stripe_card_id",
            payment_method_id=payment_method["dd_stripe_card_id"],
        )

    def test_update_drive_default_payment_method(
        self, client: TestClient, stripe_client: StripeTestClient
    ):
        random_dd_payer_id: str = str(random.randint(1, 100000))
        payer_type: str = "store"

        # create payer
        payer = create_payer_v1(
            client=client,
            request=CreatePayerV1Request(
                dd_payer_id=random_dd_payer_id,
                country="US",
                description="test_update_drive_default_payment_method",
                payer_type=payer_type,
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

        # set default_payment_method
        update_payer = _update_payer_v0(
            client=client,
            payer_id=payer["dd_stripe_customer_id"],
            payer_id_type="dd_stripe_customer_serial_id",
            request=UpdatePayerV0Request(
                dd_stripe_card_id=payment_method["dd_stripe_card_id"], country="US"
            ),
        )
        assert (
            update_payer["payment_gateway_provider_customers"][0][
                "default_payment_method_id"
            ]
            == payment_method["payment_gateway_provider_details"]["payment_method_id"]
        )

        # delete payment_method
        delete_payment_methods_v0(
            client=client,
            payment_method_id_type="dd_stripe_card_id",
            payment_method_id=payment_method["dd_stripe_card_id"],
        )

        # get payer, and verify default_payment_method is gone
        response = client.get(
            _get_payer_url(
                payer_id_type="dd_stripe_customer_serial_id",
                payer_id=payer["dd_stripe_customer_id"],
            )
        )
        assert response.status_code == 200
        get_payer: dict = response.json()
        assert (
            get_payer["payment_gateway_provider_customers"][0][
                "default_payment_method_id"
            ]
            is None
        )
