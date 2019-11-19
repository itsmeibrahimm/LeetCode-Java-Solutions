from uuid import uuid4

import pytest
from asynctest import mock
from starlette.testclient import TestClient

from app.payin.api.exceptions import _error_code_to_status_code, PayinErrorResponse
from app.payin.core.exceptions import PayinError, PayinErrorCode
from app.payin.core.payment_method.processor import PaymentMethodProcessor


class TestExceptionTranslator:
    processor = PaymentMethodProcessor
    processor_interface = "get_payment_method"

    client: TestClient

    @pytest.fixture(autouse=True)
    def setup(self, client: TestClient):
        self.client = client

    testdata = [(code, status) for code, status in _error_code_to_status_code.items()]

    @pytest.mark.parametrize(
        "error_code, status_code", testdata, ids=[data[0].name for data in testdata]
    )
    def test_payin_error_exception_translator_v0_router(
        self, error_code: PayinErrorCode, status_code: int
    ):
        with mock.patch.object(
            self.processor,
            self.processor_interface,
            side_effect=PayinError(error_code=error_code),
        ):
            # endpoint point or method don't really matter here, focus is to testing exception handler middleware
            # which is mounted to all endpoints in a router
            response = self.client.get(
                "/payin/api/v0/payment_methods/dd_stripe_card_id/123"
            )

            assert response.status_code == status_code, response.json()
            assert PayinErrorResponse.validate(response.json()), response.json()

            error_response = PayinErrorResponse.parse_obj(response.json())
            assert error_response.error_code == error_code
            assert error_response.error_message == error_code.message
            assert error_response.retryable == error_code.retryable

    @pytest.mark.parametrize("error_code, status_code", testdata)
    def test_payin_error_exception_translator_v1_router(
        self, error_code: PayinErrorCode, status_code: int
    ):
        with mock.patch.object(
            self.processor,
            self.processor_interface,
            side_effect=PayinError(error_code=error_code),
        ):
            # endpoint point or method don't really matter here, focus is to testing exception handler middleware
            # which is mounted to all endpoints in a router
            response = self.client.get(f"/payin/api/v1/payment_methods/{str(uuid4())}")

            assert response.status_code == status_code, response.json()
            assert PayinErrorResponse.validate(response.json()), response.json()

            error_response = PayinErrorResponse.parse_obj(response.json())
            assert error_response.error_code == error_code
            assert error_response.error_message == error_code.message
            assert error_response.retryable == error_code.retryable
