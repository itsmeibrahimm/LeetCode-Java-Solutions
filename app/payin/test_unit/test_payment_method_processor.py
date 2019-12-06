from typing import List

import pytest

from app.commons.types import CountryCode
from app.payin.core.exceptions import PaymentMethodListError
from app.payin.core.payment_method.model import (
    RawPaymentMethod,
    PaymentMethod,
    PaymentMethodList,
)
from app.payin.core.payment_method.processor import PaymentMethodProcessor
from app.payin.core.payment_method.types import PaymentMethodSortKey
from app.payin.tests.utils import (
    generate_pgp_payment_method,
    generate_stripe_card,
    FunctionMock,
)


class TestPaymentMethodProcessor:
    """
    Test external facing functions exposed by app/payin/core/payment_method/processor.py.
    """

    @pytest.mark.asyncio
    async def test_list_payment_methods_legacy_by_dd_consumer_id(
        self, payment_method_processor: PaymentMethodProcessor
    ):
        payment_method = RawPaymentMethod(
            pgp_payment_method_entity=generate_pgp_payment_method(),
            stripe_card_entity=generate_stripe_card(),
        ).to_payment_method()
        payment_method_list: List[PaymentMethod] = [payment_method]
        payment_method_processor.payment_method_client.get_payment_method_list_by_dd_consumer_id = FunctionMock(
            return_value=payment_method_list
        )
        result = await payment_method_processor.list_payment_methods_legacy(
            dd_consumer_id="1",
            active_only=False,
            country=CountryCode.US,
            sort_by=PaymentMethodSortKey.CREATED_AT,
            force_update=False,
        )
        assert isinstance(result, PaymentMethodList)
        assert result.count == 1
        assert result.data[0] == payment_method
        assert result.has_more is False

    @pytest.mark.asyncio
    async def test_list_payment_methods_legacy_by_stripe_customer_id(
        self, payment_method_processor: PaymentMethodProcessor
    ):
        payment_method = RawPaymentMethod(
            pgp_payment_method_entity=generate_pgp_payment_method(),
            stripe_card_entity=generate_stripe_card(),
        ).to_payment_method()
        payment_method_list: List[PaymentMethod] = [payment_method]
        payment_method_processor.payment_method_client.get_payment_method_list_by_stripe_customer_id = FunctionMock(
            return_value=payment_method_list
        )
        result = await payment_method_processor.list_payment_methods_legacy(
            stripe_customer_id="VALID_STRIPE_CUSTOMER_ID",
            active_only=False,
            country=CountryCode.US,
            sort_by=PaymentMethodSortKey.CREATED_AT,
            force_update=False,
        )
        assert isinstance(result, PaymentMethodList)
        assert result.count == 1
        assert result.data[0] == payment_method
        assert result.has_more is False

    @pytest.mark.asyncio
    async def test_list_payment_methods_legacy_invalid_payer_type_exception(
        self, payment_method_processor: PaymentMethodProcessor
    ):
        error_code = ""
        error_message = ""
        try:
            await payment_method_processor.list_payment_methods_legacy(
                active_only=False,
                country=CountryCode.US,
                sort_by=PaymentMethodSortKey.CREATED_AT,
                force_update=False,
            )
        except PaymentMethodListError as e:
            error_code = e.error_code
            error_message = e.error_message
        assert error_code == "payin_32"
        assert error_message == "Invalid payer type for list payment method"
