import time
import uuid
from typing import Optional, Any

import pytest
from pydantic import BaseModel
from starlette.testclient import TestClient

from app.commons.config.app_config import AppConfig
from app.commons.providers.stripe import stripe_models as models
from app.commons.providers.stripe.stripe_client import StripeTestClient
from app.payin.test_integration.integration_utils import (
    create_payer_v1,
    CreatePayerV1Request,
    create_payer_failure_v1,
    PayinError,
)

V1_PAYERS_ENDPOINT = "/payin/api/v1/payers"


def _create_payer_url():
    return V1_PAYERS_ENDPOINT


def _get_payer_url(payer_id: str):
    return f"{V1_PAYERS_ENDPOINT}/{payer_id}"


def _update_payer_default_payment_method_url(payer_id: str):
    return f"{V1_PAYERS_ENDPOINT}/{payer_id}"


class UpdatePayerV1Request(BaseModel):
    payment_method_id: Optional[Any]
    dd_stripe_card_id: Optional[Any]


def _update_payer_failure_v1(
    client: TestClient, payer_id: Any, request: UpdatePayerV1Request, error: PayinError
):
    update_payer_request = {
        "default_payment_method": {
            "payment_method_id": request.payment_method_id,
            "dd_stripe_card_id": request.dd_stripe_card_id,
        }
    }
    response = client.patch(
        _update_payer_default_payment_method_url(payer_id=payer_id),
        json=update_payer_request,
    )
    assert response.status_code == error.http_status_code
    error_response: dict = response.json()
    assert error_response["error_code"] == error.error_code
    assert error_response["retryable"] == error.retryable


class TestPayersV1:
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

    def test_create_and_get_payer(
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

    def test_invalid_input(self, client: TestClient, stripe_client: StripeTestClient):
        random_dd_payer_id: str = str(int(time.time() * 1e6))

        # test non-numeric dd_payer_id
        create_payer_failure_v1(
            client=client,
            request=CreatePayerV1Request(
                dd_payer_id="i am invalid dd_payer_id",
                country="US",
                description="Integration Test test_create_payer()",
                payer_type="store",
                email=(random_dd_payer_id + "@dd.com"),
            ),
            error=PayinError(
                http_status_code=422, error_code="payin_1", retryable=False
            ),
        )

        # test invalid country
        create_payer_failure_v1(
            client=client,
            request=CreatePayerV1Request(
                dd_payer_id=random_dd_payer_id,
                country="Clement is human being, not a country",
                description="Integration Test test_invalid_input()",
                payer_type="store",
                email=(random_dd_payer_id + "@dd.com"),
            ),
            error=PayinError(
                http_status_code=422,
                error_code="request_validation_error",
                retryable=False,
            ),
        )

        # test invalid payer_type
        create_payer_failure_v1(
            client=client,
            request=CreatePayerV1Request(
                dd_payer_id=random_dd_payer_id,
                country="US",
                description="Integration Test test_invalid_input()",
                payer_type="fake payer type",
                email=(random_dd_payer_id + "@dd.com"),
            ),
            error=PayinError(
                http_status_code=422,
                error_code="request_validation_error",
                retryable=False,
            ),
        )

    def test_missing_input(self, client: TestClient, stripe_client: StripeTestClient):
        random_dd_payer_id: str = str(int(time.time() * 1e6))

        # test missing dd_payer_id
        create_payer_failure_v1(
            client=client,
            request=CreatePayerV1Request(
                country="US",
                description="Integration Test test_missing_input()",
                payer_type="fake payer type",
                email=(random_dd_payer_id + "@dd.com"),
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
                dd_payer_id=random_dd_payer_id,
                description="Integration Test test_missing_input()",
                payer_type="fake payer type",
                email=(random_dd_payer_id + "@dd.com"),
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
                dd_payer_id=random_dd_payer_id,
                country="US",
                payer_type="fake payer type",
                email=(random_dd_payer_id + "@dd.com"),
            ),
            error=PayinError(
                http_status_code=422,
                error_code="request_validation_error",
                retryable=False,
            ),
        )

        # test missing payer_type
        create_payer_failure_v1(
            client=client,
            request=CreatePayerV1Request(
                dd_payer_id=random_dd_payer_id,
                country="US",
                description="Integration Test test_missing_input()",
                email=(random_dd_payer_id + "@dd.com"),
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
                dd_payer_id=random_dd_payer_id,
                country="US",
                description="Integration Test test_missing_input()",
                payer_type="fake payer type",
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
                payment_method_id="test", dd_stripe_card_id="1234"
            ),
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
