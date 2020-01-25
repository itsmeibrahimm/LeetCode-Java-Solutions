from typing import Optional
from unittest.mock import MagicMock
from uuid import uuid4, UUID

import pytest

from app.payin.api.cart_payment.v1.converter import validate_cart_payment_request_v1
from app.payin.api.cart_payment.v1.request import CreateCartPaymentRequestV1


@pytest.mark.parametrize(
    "payment_method_id, payment_method_token, dd_stripe_card_id",
    [
        (uuid4(), "token", 123),
        (None, "token", 123),
        (uuid4(), None, 123),
        (uuid4(), "token", None),
        (None, None, None),
    ],
)
def test_create_cart_payment_v1_request_validation_payment_method(
    payment_method_id: Optional[UUID],
    payment_method_token: Optional[str],
    dd_stripe_card_id: Optional[int],
):
    invalid_request: CreateCartPaymentRequestV1 = MagicMock(CreateCartPaymentRequestV1)
    invalid_request.payment_method_id = payment_method_id
    invalid_request.payment_method_token = payment_method_token
    invalid_request.dd_stripe_card_id = dd_stripe_card_id

    with pytest.raises(ValueError):
        validate_cart_payment_request_v1(invalid_request)
