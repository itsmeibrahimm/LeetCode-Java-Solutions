from uuid import uuid4

import pytest
from asynctest import create_autospec
from structlog.stdlib import BoundLogger

from app.commons.api.models import PaymentException
from app.payin.core.exceptions import (
    CartPaymentCreateError,
    CartPaymentUpdateError,
    PayinErrorCode,
)
from app.payin.api.cart_payment.v0 import api as v0_api
from app.payin.api.cart_payment.v0.request import (
    CreateCartPaymentLegacyRequest,
    UpdateCartPaymentLegacyRequest,
)
from app.payin.api.cart_payment.v1 import api as v1_api
from app.payin.api.cart_payment.v1.request import (
    CorrelationIds,
    CreateCartPaymentRequest,
    UpdateCartPaymentRequest,
)
from app.payin.core.types import LegacyPaymentInfo
from app.payin.tests.utils import FunctionMock


class TestCartPaymentApi:
    """
    Test v0 api class functions.  Assumes processor and other dependencies are mocked and verifies any
    logic in api.py modules.
    """

    create_error_states = [
        (PayinErrorCode.PAYMENT_INTENT_CREATE_CARD_DECLINED_ERROR, 400),
        (PayinErrorCode.PAYMENT_INTENT_CREATE_CARD_EXPIRED_ERROR, 400),
        (PayinErrorCode.PAYMENT_INTENT_CREATE_CARD_PROCESSING_ERROR, 400),
        (PayinErrorCode.PAYMENT_INTENT_CREATE_CARD_INCORRECT_NUMBER_ERROR, 400),
        (PayinErrorCode.PAYMENT_INTENT_CREATE_CARD_INCORRECT_CVC_ERROR, 400),
        (PayinErrorCode.PAYMENT_INTENT_CREATE_INVALID_SPLIT_PAYMENT_ACCOUNT, 400),
        (PayinErrorCode.PAYMENT_METHOD_GET_NOT_FOUND, 400),
        (PayinErrorCode.PAYMENT_METHOD_GET_PAYER_PAYMENT_METHOD_MISMATCH, 403),
        (PayinErrorCode.PAYMENT_METHOD_CREATE_STRIPE_ERROR, 500),
    ]

    @pytest.mark.parametrize(
        "expected_error_state",
        create_error_states,
        ids=[error_state[0] for error_state in create_error_states],
    )
    @pytest.mark.asyncio
    async def test_v0_creation_errors(
        self, cart_payment_processor, expected_error_state
    ):
        request = CreateCartPaymentLegacyRequest(
            amount=500,
            payment_country="US",
            currency="usd",
            delay_capture=False,
            idempotency_key=str(uuid4()),
            payer_country="US",
            client_description="test",
            legacy_payment=LegacyPaymentInfo(
                dd_consumer_id=1,
                dd_stripe_card_id=1,
                dd_country_id=1,
                dd_additional_payment_info=None,
                stripe_customer_id="1",
                stripe_card_id="1",
            ),
            legacy_correlation_ids=CorrelationIds(
                reference_id="100", reference_type="12"
            ),
        )

        payin_error_code = expected_error_state[0]
        http_status_code = expected_error_state[1]
        cart_payment_processor.legacy_create_payment = FunctionMock(
            side_effect=CartPaymentCreateError(
                error_code=payin_error_code,
                retryable=False,
                provider_charge_id="test_charge",
                provider_decline_code="test_decline_code",
                provider_error_code="test_error_code",
                has_provider_error_details=True,
            )
        )

        with pytest.raises(PaymentException) as e:
            await v0_api.create_cart_payment_for_legacy_client(
                cart_payment_request=request,
                log=create_autospec(BoundLogger),
                cart_payment_processor=cart_payment_processor,
            )
        assert e.value.status_code == http_status_code

    @pytest.mark.parametrize(
        "expected_error_state",
        create_error_states,
        ids=[error_state[0] for error_state in create_error_states],
    )
    async def test_v1_creation_errors(
        self, cart_payment_processor, expected_error_state
    ):
        request = CreateCartPaymentRequest(
            amount=500,
            payer_id=str(uuid4()),
            payment_method_id=str(uuid4()),
            payment_country="US",
            currency="usd",
            delay_capture=False,
            idempotency_key=str(uuid4()),
            payer_country="US",
            client_description="test",
            correlation_ids=CorrelationIds(reference_id="1", reference_type="1"),
        )

        payin_error_code = expected_error_state[0]
        http_status_code = expected_error_state[1]
        cart_payment_processor.create_payment = FunctionMock(
            side_effect=CartPaymentCreateError(
                error_code=payin_error_code,
                retryable=False,
                provider_charge_id="test_charge",
                provider_decline_code="test_decline_code",
                provider_error_code="test_error_code",
                has_provider_error_details=True,
            )
        )

        with pytest.raises(PaymentException) as e:
            await v1_api.create_cart_payment(
                cart_payment_request=request,
                log=create_autospec(BoundLogger),
                cart_payment_processor=cart_payment_processor,
            )
        assert e.value.status_code == http_status_code

    update_error_states = [
        (PayinErrorCode.PAYMENT_INTENT_CREATE_CARD_DECLINED_ERROR, 400),
        (PayinErrorCode.PAYMENT_INTENT_CREATE_CARD_EXPIRED_ERROR, 400),
        (PayinErrorCode.PAYMENT_INTENT_CREATE_CARD_PROCESSING_ERROR, 400),
        (PayinErrorCode.PAYMENT_INTENT_CREATE_CARD_INCORRECT_NUMBER_ERROR, 400),
        (PayinErrorCode.PAYMENT_INTENT_CREATE_CARD_INCORRECT_CVC_ERROR, 400),
        (PayinErrorCode.PAYMENT_INTENT_CREATE_INVALID_SPLIT_PAYMENT_ACCOUNT, 400),
        (PayinErrorCode.CART_PAYMENT_NOT_FOUND, 404),
        (PayinErrorCode.CART_PAYMENT_OWNER_MISMATCH, 403),
        (PayinErrorCode.PAYMENT_METHOD_GET_PAYER_PAYMENT_METHOD_MISMATCH, 403),
    ]

    @pytest.mark.parametrize(
        "expected_error_state",
        update_error_states,
        ids=[error_state[0] for error_state in update_error_states],
    )
    @pytest.mark.asyncio
    async def test_v0_update_errors(self, cart_payment_processor, expected_error_state):
        request = UpdateCartPaymentLegacyRequest(
            amount=500, dd_additional_payment_info=None, idempotency_key=str(uuid4())
        )

        payin_error_code = expected_error_state[0]
        http_status_code = expected_error_state[1]
        cart_payment_processor.update_payment_for_legacy_charge = FunctionMock(
            side_effect=CartPaymentUpdateError(
                error_code=payin_error_code, retryable=False
            )
        )

        with pytest.raises(PaymentException) as e:
            await v0_api.update_cart_payment(
                dd_charge_id=1,
                cart_payment_request=request,
                log=create_autospec(BoundLogger),
                cart_payment_processor=cart_payment_processor,
            )
        assert e.value.status_code == http_status_code

    @pytest.mark.parametrize(
        "expected_error_state",
        update_error_states,
        ids=[error_state[0] for error_state in update_error_states],
    )
    @pytest.mark.asyncio
    async def test_v1_update_errors(self, cart_payment_processor, expected_error_state):
        request = UpdateCartPaymentRequest(
            amount=500, payer_id=uuid4(), idempotency_key=str(uuid4())
        )

        payin_error_code = expected_error_state[0]
        http_status_code = expected_error_state[1]
        cart_payment_processor.update_payment = FunctionMock(
            side_effect=CartPaymentUpdateError(
                error_code=payin_error_code, retryable=False
            )
        )

        with pytest.raises(PaymentException) as e:
            await v1_api.update_cart_payment(
                cart_payment_id=uuid4(),
                cart_payment_request=request,
                log=create_autospec(BoundLogger),
                cart_payment_processor=cart_payment_processor,
            )
        assert e.value.status_code == http_status_code
