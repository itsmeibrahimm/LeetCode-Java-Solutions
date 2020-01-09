import random
import uuid
from typing import Optional, Any, Dict

from pydantic import BaseModel
from starlette.testclient import TestClient

from app.commons.providers.stripe.stripe_client import StripeTestClient
from app.payin.test_integration.integration_utils import (
    create_payer_v1,
    CreatePayerV1Request,
    create_payer_failure_v1,
    PayinError,
    create_payment_method_v1,
    CreatePaymentMethodV1Request,
    delete_payment_methods_v1,
)

V1_PAYERS_ENDPOINT = "/payin/api/v1/payers"


def _create_payer_url():
    return V1_PAYERS_ENDPOINT


def _get_payer_url(payer_id: str):
    return f"{V1_PAYERS_ENDPOINT}/{payer_id}"


def _get_payer_by_reference_id_url(
    payer_reference_id_type: str, payer_reference_id: str
):
    return f"{V1_PAYERS_ENDPOINT}/{payer_reference_id_type}/{payer_reference_id}"


def _update_payer_default_payment_method_url(payer_id: str):
    return f"{V1_PAYERS_ENDPOINT}/{payer_id}/default_payment_method"


def _update_payer_default_payment_method_by_reference_id_url(
    payer_reference_id_type: str, payer_reference_id: str
):
    return f"{V1_PAYERS_ENDPOINT}/{payer_reference_id_type}/{payer_reference_id}/default_payment_method"


class UpdatePayerV1Request(BaseModel):
    payment_method_id: Optional[Any] = None
    dd_stripe_card_id: Optional[Any] = None


def _update_payer_v1(
    client: TestClient, request: UpdatePayerV1Request, url: str
) -> Dict[str, Any]:
    update_payer_request = {
        "default_payment_method": {
            "payment_method_id": request.payment_method_id,
            "dd_stripe_card_id": request.dd_stripe_card_id,
        }
    }
    response = client.post(url, json=update_payer_request)
    assert response.status_code == 200
    return response.json()


def _update_payer_failure_v1(
    client: TestClient, payer_id: Any, request: UpdatePayerV1Request, error: PayinError
):
    update_payer_request = {
        "default_payment_method": {
            "payment_method_id": request.payment_method_id,
            "dd_stripe_card_id": request.dd_stripe_card_id,
        }
    }
    response = client.post(
        _update_payer_default_payment_method_url(payer_id=payer_id),
        json=update_payer_request,
    )
    assert response.status_code == error.http_status_code
    error_response: dict = response.json()
    assert error_response["error_code"] == error.error_code
    assert error_response["retryable"] == error.retryable


def _get_payer_failure_v1(client: TestClient, payer_id: Any, error: PayinError):
    response = client.get(_get_payer_url(payer_id=payer_id))
    assert response.status_code == error.http_status_code
    error_response: dict = response.json()
    assert error_response["error_code"] == error.error_code
    assert error_response["retryable"] == error.retryable


class TestPayersV1:
    def test_create_and_get_payer(
        self, client: TestClient, stripe_client: StripeTestClient
    ):
        random_payer_reference_id: str = str(random.randint(1, 100000))

        # create payer
        payer = create_payer_v1(
            client=client,
            request=CreatePayerV1Request(
                payer_reference_id=random_payer_reference_id,
                country="US",
                description="Integration Test test_create_payer()",
                payer_reference_id_type="dd_consumer_id",
                email=(random_payer_reference_id + "@dd.com"),
            ),
        )

        # get payer
        response = client.get(_get_payer_url(payer_id=payer["id"]))
        assert response.status_code == 200
        get_payer: dict = response.json()
        assert payer == get_payer

        # get payer with force_update
        response = client.get(
            _get_payer_url(payer_id=payer["id"]) + "?force_update=True"
        )
        assert response.status_code == 200
        force_get_payer: dict = response.json()
        assert payer == force_get_payer

    def test_payer_not_exist(self, client: TestClient, stripe_client: StripeTestClient):
        _get_payer_failure_v1(
            client=client,
            payer_id=uuid.uuid4(),
            error=PayinError(
                http_status_code=404, error_code="payin_5", retryable=False
            ),
        )

    def test_invalid_input(self, client: TestClient, stripe_client: StripeTestClient):
        random_payer_reference_id: str = str(random.randint(1, 100000))

        # test non-numeric payer_reference_id
        create_payer_failure_v1(
            client=client,
            request=CreatePayerV1Request(
                payer_reference_id="i am invalid payer_reference_id",
                country="US",
                description="Integration Test test_create_payer()",
                payer_reference_id_type="dd_drive_store_id",
                email=(random_payer_reference_id + "@dd.com"),
            ),
            error=PayinError(
                http_status_code=400, error_code="payin_1", retryable=False
            ),
        )

        # test invalid country
        create_payer_failure_v1(
            client=client,
            request=CreatePayerV1Request(
                dd_payer_reference_id=random_payer_reference_id,
                country="Clement is human being, not a country",
                description="Integration Test test_invalid_input()",
                payer_reference_id_type="dd_drive_store_id",
                email=(random_payer_reference_id + "@dd.com"),
            ),
            error=PayinError(
                http_status_code=422,
                error_code="request_validation_error",
                retryable=False,
            ),
        )

        # test invalid payer_reference_id_type
        create_payer_failure_v1(
            client=client,
            request=CreatePayerV1Request(
                payer_reference_id=random_payer_reference_id,
                country="US",
                description="Integration Test test_invalid_input()",
                payer_reference_id_type="fake payer type",
                email=(random_payer_reference_id + "@dd.com"),
            ),
            error=PayinError(
                http_status_code=422,
                error_code="request_validation_error",
                retryable=False,
            ),
        )

    def test_missing_input(self, client: TestClient, stripe_client: StripeTestClient):
        random_payer_reference_id: str = str(random.randint(1, 100000))

        # test missing payer_reference_id
        create_payer_failure_v1(
            client=client,
            request=CreatePayerV1Request(
                country="US",
                description="Integration Test test_missing_input()",
                payer_reference_id_type="fake payer type",
                email=(random_payer_reference_id + "@dd.com"),
            ),
            error=PayinError(
                http_status_code=422,
                error_code="request_validation_error",
                retryable=False,
            ),
        )

        # test missing country
        create_payer_failure_v1(
            client=client,
            request=CreatePayerV1Request(
                payer_reference_id=random_payer_reference_id,
                description="Integration Test test_missing_input()",
                payer_reference_id_type="fake payer type",
                email=(random_payer_reference_id + "@dd.com"),
            ),
            error=PayinError(
                http_status_code=422,
                error_code="request_validation_error",
                retryable=False,
            ),
        )

        # test missing description
        create_payer_failure_v1(
            client=client,
            request=CreatePayerV1Request(
                payer_reference_id=random_payer_reference_id,
                country="US",
                ppayer_reference_id_type="fake payer type",
                email=(random_payer_reference_id + "@dd.com"),
            ),
            error=PayinError(
                http_status_code=422,
                error_code="request_validation_error",
                retryable=False,
            ),
        )

        # test missing payer_reference_id_type
        create_payer_failure_v1(
            client=client,
            request=CreatePayerV1Request(
                payer_reference_id=random_payer_reference_id,
                country="US",
                description="Integration Test test_missing_input()",
                email=(random_payer_reference_id + "@dd.com"),
            ),
            error=PayinError(
                http_status_code=422,
                error_code="request_validation_error",
                retryable=False,
            ),
        )

        # test missing email
        create_payer_failure_v1(
            client=client,
            request=CreatePayerV1Request(
                payer_reference_id=random_payer_reference_id,
                country="US",
                description="Integration Test test_missing_input()",
                payer_reference_id_type="fake payer type",
            ),
            error=PayinError(
                http_status_code=422,
                error_code="request_validation_error",
                retryable=False,
            ),
        )

    def test_get_payer_invalid_payer_id(
        self, client: TestClient, stripe_client: StripeTestClient
    ):
        response = client.get(_get_payer_url(payer_id="i_am_invalid_payer_id"))
        assert response.status_code == 422
        get_payer: dict = response.json()
        assert get_payer["error_code"] == "request_validation_error"
        assert get_payer["retryable"] == False

    def test_update_payer_invalid_input(
        self, client: TestClient, stripe_client: StripeTestClient
    ):
        # None value
        _update_payer_failure_v1(
            client=client,
            request=UpdatePayerV1Request(
                payment_method_id=None, dd_stripe_card_id=None
            ),
            payer_id=uuid.uuid4(),
            error=PayinError(
                http_status_code=400, error_code="payin_22", retryable=False
            ),
        )

        # Both payment_method_id and dd_stripe_card_id are provided
        _update_payer_failure_v1(
            client=client,
            request=UpdatePayerV1Request(
                payment_method_id=str(uuid.uuid4()), dd_stripe_card_id="1234"
            ),
            payer_id=uuid.uuid4(),
            error=PayinError(
                http_status_code=400, error_code="payin_22", retryable=False
            ),
        )

        # invalid datatype of "payment_method_id"
        _update_payer_failure_v1(
            client=client,
            request=UpdatePayerV1Request(payment_method_id="test"),
            payer_id=uuid.uuid4(),
            error=PayinError(
                http_status_code=422,
                error_code="request_validation_error",
                retryable=False,
            ),
        )

    def test_update_payer_invalid_payer_id(
        self, client: TestClient, stripe_client: StripeTestClient
    ):
        _update_payer_failure_v1(
            client=client,
            request=UpdatePayerV1Request(dd_stripe_card_id="1234"),
            payer_id="i_am_fake_uuid",
            error=PayinError(
                http_status_code=422,
                error_code="request_validation_error",
                retryable=False,
            ),
        )

    def test_update_default_payment_method(
        self, client: TestClient, stripe_client: StripeTestClient
    ):
        random_payer_reference_id: str = str(random.randint(1, 100000))

        # create payer
        payer = create_payer_v1(
            client=client,
            request=CreatePayerV1Request(
                payer_reference_id=random_payer_reference_id,
                country="US",
                description="Integration Test test_default_payment_method()",
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

        # set default_payment_method
        update_payer = _update_payer_v1(
            client=client,
            url=_update_payer_default_payment_method_url(payer_id=payer["id"]),
            request=UpdatePayerV1Request(payment_method_id=payment_method["id"]),
        )
        assert (
            update_payer["payment_gateway_provider_customers"][0][
                "default_payment_method_id"
            ]
            == payment_method["payment_gateway_provider_details"]["payment_method_id"]
        )
        assert update_payer["default_payment_method_id"] == payment_method["id"]
        assert (
            update_payer["default_dd_stripe_card_id"]
            == payment_method["dd_stripe_card_id"]
        )

        # delete payment_method
        delete_payment_methods_v1(client=client, payment_method_id=payment_method["id"])

        # get payer, and verify default_payment_method is gone
        response = client.get(_get_payer_url(payer_id=payer["id"]))
        assert response.status_code == 200
        get_payer: dict = response.json()
        assert (
            get_payer["payment_gateway_provider_customers"][0][
                "default_payment_method_id"
            ]
            is None
        )
        assert get_payer["default_payment_method_id"] is None
        assert get_payer["default_dd_stripe_card_id"] is None

    def test_add_default_payment_method(
        self, client: TestClient, stripe_client: StripeTestClient
    ):
        random_payer_reference_id: str = str(random.randint(1, 100000))

        # create payer
        payer = create_payer_v1(
            client=client,
            request=CreatePayerV1Request(
                payer_reference_id=random_payer_reference_id,
                country="US",
                description="Integration Test test_add_default_payment_method()",
                payer_reference_id_type="dd_drive_store_id",
                email=(random_payer_reference_id + "@dd.com"),
            ),
        )

        # create payment_method and set to default
        payment_method = create_payment_method_v1(
            client=client,
            request=CreatePaymentMethodV1Request(
                payer_id=payer["id"],
                payment_gateway="stripe",
                token="tok_visa",
                set_default=True,
                is_scanned=False,
                is_active=True,
            ),
        )

        # get payer, and ensure default is set.
        response = client.get(_get_payer_url(payer_id=payer["id"]))
        assert response.status_code == 200
        get_payer: dict = response.json()
        assert (
            get_payer["payment_gateway_provider_customers"][0][
                "default_payment_method_id"
            ]
            == payment_method["payment_gateway_provider_details"]["payment_method_id"]
        )
        assert get_payer["default_payment_method_id"] == payment_method["id"]
        assert (
            get_payer["default_dd_stripe_card_id"]
            == payment_method["dd_stripe_card_id"]
        )

    def test_get_payer_by_reference_id(
        self, client: TestClient, stripe_client: StripeTestClient
    ):
        random_payer_reference_id: str = str(random.randint(1, 100000))

        # create payer
        payer = create_payer_v1(
            client=client,
            request=CreatePayerV1Request(
                payer_reference_id=random_payer_reference_id,
                country="US",
                description="Integration Test test_get_payer_by_reference_id()",
                payer_reference_id_type="dd_consumer_id",
                email=(random_payer_reference_id + "@dd.com"),
            ),
        )

        # get payer
        response = client.get(
            _get_payer_by_reference_id_url(
                payer_reference_id_type=payer["payer_correlation_ids"][
                    "payer_reference_id_type"
                ],
                payer_reference_id=payer["payer_correlation_ids"]["payer_reference_id"],
            )
        )
        assert response.status_code == 200
        get_payer: dict = response.json()
        assert payer == get_payer

        # get payer with force_update
        response = client.get(
            _get_payer_by_reference_id_url(
                payer_reference_id_type="dd_consumer_id",
                payer_reference_id=payer["payer_correlation_ids"]["payer_reference_id"],
            )
            + "?force_update=True"
        )
        assert response.status_code == 200
        force_get_payer: dict = response.json()
        assert payer == force_get_payer

    def test_get_payer_invalid_reference_id_type(
        self, client: TestClient, stripe_client: StripeTestClient
    ):
        response = client.get(
            _get_payer_by_reference_id_url(
                payer_reference_id_type="i_am_invalid_payer_ref_id_type",
                payer_reference_id="123",
            )
        )
        assert response.status_code == 422
        get_payer: dict = response.json()
        assert get_payer["error_code"] == "request_validation_error"
        assert get_payer["retryable"] == False

    def test_update_default_payment_method_by_reference_id(
        self, client: TestClient, stripe_client: StripeTestClient
    ):
        random_payer_reference_id: str = str(random.randint(1, 100000))

        # create payer
        payer = create_payer_v1(
            client=client,
            request=CreatePayerV1Request(
                payer_reference_id=random_payer_reference_id,
                country="US",
                description="Integration Test test_default_payment_method()",
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

        # set default_payment_method
        update_payer = _update_payer_v1(
            client=client,
            url=_update_payer_default_payment_method_by_reference_id_url(
                payer_reference_id_type="legacy_dd_stripe_customer_id",
                payer_reference_id=payer["legacy_dd_stripe_customer_id"],
            ),
            request=UpdatePayerV1Request(payment_method_id=payment_method["id"]),
        )
        assert (
            update_payer["payment_gateway_provider_customers"][0][
                "default_payment_method_id"
            ]
            == payment_method["payment_gateway_provider_details"]["payment_method_id"]
        )
        assert update_payer["default_payment_method_id"] == payment_method["id"]
        assert (
            update_payer["default_dd_stripe_card_id"]
            == payment_method["dd_stripe_card_id"]
        )

        # delete payment_method
        delete_payment_methods_v1(client=client, payment_method_id=payment_method["id"])

        # get payer, and verify default_payment_method is gone
        response = client.get(
            _get_payer_by_reference_id_url(
                payer_reference_id_type="legacy_dd_stripe_customer_id",
                payer_reference_id=payer["legacy_dd_stripe_customer_id"],
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
        assert get_payer["default_payment_method_id"] is None
        assert get_payer["default_dd_stripe_card_id"] is None
