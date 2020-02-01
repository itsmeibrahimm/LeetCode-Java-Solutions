import uuid
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
from app.payin.core.types import PayerReferenceIdType
from app.payin.tests.utils import (
    generate_pgp_payment_method,
    generate_stripe_card,
    FunctionMock,
    generate_payer_entity,
    generate_raw_payer,
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
        raw_payer = generate_raw_payer()
        payment_method_processor.payer_client.get_raw_payer = FunctionMock(
            return_value=raw_payer
        )
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
        raw_payer = generate_raw_payer()
        payment_method_processor.payer_client.get_raw_payer = FunctionMock(
            return_value=raw_payer
        )
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

    @pytest.mark.asyncio
    async def test_list_payment_methods_by_payer_id(self, payment_method_processor):
        payment_method = RawPaymentMethod(
            pgp_payment_method_entity=generate_pgp_payment_method(),
            stripe_card_entity=generate_stripe_card(),
        ).to_payment_method()
        payment_method_list: List[PaymentMethod] = [payment_method]
        payment_method_processor.payer_client.get_payer_entity = FunctionMock(
            return_value=generate_payer_entity()
        )
        payment_method_processor.payment_method_client.get_payment_method_list_by_stripe_customer_id = FunctionMock(
            return_value=payment_method_list
        )
        result = await payment_method_processor.list_payment_methods(
            payer_lookup_id=str(uuid.uuid4()),
            payer_reference_id_type=PayerReferenceIdType.PAYER_ID,
            active_only=False,
            sort_by=PaymentMethodSortKey.CREATED_AT,
            force_update=False,
        )
        assert isinstance(result, PaymentMethodList)
        assert result.count == 1
        assert result.data[0] == payment_method
        assert result.has_more is False

    @pytest.mark.asyncio
    async def test_list_active_payment_methods_by_payer_id(
        self, payment_method_processor
    ):
        payment_method_processor.payer_client.get_payer_entity = FunctionMock(
            return_value=generate_payer_entity()
        )
        payment_method_processor.payment_method_client.get_payment_method_list_by_stripe_customer_id = FunctionMock(
            return_value=[]
        )
        result = await payment_method_processor.list_payment_methods(
            payer_lookup_id=str(uuid.uuid4()),
            payer_reference_id_type=PayerReferenceIdType.PAYER_ID,
            active_only=True,
            sort_by=PaymentMethodSortKey.CREATED_AT,
            force_update=False,
        )
        assert isinstance(result, PaymentMethodList)
        assert result.count == 0
        assert len(result.data) == 0
        assert result.has_more is False
