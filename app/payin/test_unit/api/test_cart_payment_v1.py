from typing import Optional, Dict, Any
from unittest.mock import MagicMock
from uuid import uuid4, UUID

import pytest

from app.payin.api.cart_payment.v1.converter import validate_cart_payment_request_v1
from app.payin.api.cart_payment.v1.request import (
    CreateCartPaymentRequestV1,
    PaymentMethodToken,
)


@pytest.mark.parametrize(
    "payment_method_id, payment_method_token, dd_stripe_card_id",
    [
        (uuid4(), {"token": "tok", "payment_gateway": "stripe"}, 123),
        (None, {"token": "tok", "payment_gateway": "stripe"}, 123),
        (uuid4(), None, 123),
        (uuid4(), {"token": "tok", "payment_gateway": "stripe"}, None),
        (None, None, None),
    ],
)
def test_create_cart_payment_v1_request_validation_payment_method(
    payment_method_id: Optional[UUID],
    payment_method_token: Optional[Dict[str, Any]],
    dd_stripe_card_id: Optional[int],
):
    invalid_request: CreateCartPaymentRequestV1 = MagicMock(CreateCartPaymentRequestV1)
    invalid_request.payment_method_id = payment_method_id
    invalid_request.payment_method_token = (
        PaymentMethodToken(**payment_method_token) if payment_method_token else None
    )
    invalid_request.dd_stripe_card_id = dd_stripe_card_id

    with pytest.raises(ValueError):
        validate_cart_payment_request_v1(invalid_request)
