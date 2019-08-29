import pytest
from unittest.mock import MagicMock
from app.payin.core.exceptions import (
    CartPaymentReadError,
    PayinErrorCode,
    PaymentMethodReadError,
)
from app.payin.core.payer.processor import PayerClient
from app.payin.core.payment_method.processor import PaymentMethodClient
import app.payin.core.cart_payment.processor as processor
from app.payin.tests.utils import (
    generate_payment_intent,
    generate_pgp_payment_intent,
    generate_cart_payment,
    FunctionMock,
)
import uuid


@pytest.mark.asyncio
class TestCartPaymentProcessor:
    """
    Test external facing functions exposed by app/payin/core/cart_payment/processor.py.
    """

    @pytest.fixture
    def request_cart_payment(self):
        return generate_cart_payment()

    @pytest.fixture
    def payment_method_client(self):
        return PaymentMethodClient(
            payment_method_repo=MagicMock(), log=MagicMock(), app_ctxt=MagicMock()
        )

    @pytest.fixture
    def payer_client(self):
        return PayerClient(
            payer_repo=MagicMock(), log=MagicMock(), app_ctxt=MagicMock()
        )

    @pytest.fixture
    def cart_payment_processor(self, cart_payment_interface):
        return processor.CartPaymentProcessor(cart_payment_interface)

    async def test_submit_with_no_payment_method(
        self, request_cart_payment, payer_client, payment_method_client
    ):
        mocked_method_fetch = FunctionMock()
        mocked_method_fetch.side_effect = PaymentMethodReadError(
            error_code=PayinErrorCode.PAYMENT_METHOD_GET_NOT_FOUND, retryable=False
        )
        payment_method_client.get_payment_method = mocked_method_fetch

        cart_payment_interface = processor.CartPaymentInterface(
            app_context=MagicMock(),
            req_context=MagicMock(),
            payer_client=payer_client,
            payment_method_client=payment_method_client,
        )
        cart_payment_processor = processor.CartPaymentProcessor(
            cart_payment_interface=cart_payment_interface
        )

        with pytest.raises(PaymentMethodReadError) as payment_error:
            await cart_payment_processor.submit_payment(
                request_cart_payment=request_cart_payment,
                idempotency_key=str(uuid.uuid4()),
                country="US",
                currency="USD",
                client_description="Client description",
            )
        assert (
            payment_error.value.error_code
            == PayinErrorCode.PAYMENT_METHOD_GET_NOT_FOUND.value
        )

    async def test_submit_with_other_owner(
        self, request_cart_payment, payer_client, payment_method_client
    ):
        mocked_method_fetch = FunctionMock()
        mocked_method_fetch.side_effect = PaymentMethodReadError(
            error_code=PayinErrorCode.PAYMENT_METHOD_GET_PAYER_PAYMENT_METHOD_MISMATCH,
            retryable=False,
        )
        payment_method_client.get_payment_method = mocked_method_fetch

        request_cart_payment.payer_id = f"changed-{request_cart_payment.payer_id}"
        cart_payment_interface = processor.CartPaymentInterface(
            app_context=MagicMock(),
            req_context=MagicMock(),
            payment_repo=MagicMock(),
            payer_client=payer_client,
            payment_method_client=payment_method_client,
        )
        cart_payment_processor = processor.CartPaymentProcessor(
            cart_payment_interface=cart_payment_interface
        )

        with pytest.raises(PaymentMethodReadError) as payment_error:
            await cart_payment_processor.submit_payment(
                request_cart_payment=request_cart_payment,
                idempotency_key=str(uuid.uuid4()),
                country="US",
                currency="USD",
                client_description="Client description",
            )
        assert (
            payment_error.value.error_code
            == PayinErrorCode.PAYMENT_METHOD_GET_PAYER_PAYMENT_METHOD_MISMATCH.value
        )

    @pytest.mark.skip("Not yet implemented")
    async def test_invalid_country(self):
        # TODO Invalid currency/country
        pass

    @pytest.mark.skip("Not yet implemented")
    async def test_legacy_payment(self):
        # TODO legacy payment, including other payer_id_type
        pass

    async def test_submit(self, cart_payment_processor, request_cart_payment):
        result_cart_payment = await cart_payment_processor.submit_payment(
            request_cart_payment=request_cart_payment,
            idempotency_key=str(uuid.uuid4()),
            country="US",
            currency="USD",
            client_description="Client description",
        )
        assert result_cart_payment
        assert result_cart_payment.id
        assert result_cart_payment.amount == request_cart_payment.amount

    @pytest.mark.asyncio
    async def test_resubmit(self, cart_payment_processor, request_cart_payment):

        intent = generate_payment_intent()
        cart_payment_processor.cart_payment_interface.payment_repo.get_payment_intent_for_idempotency_key = FunctionMock(
            return_value=intent
        )
        cart_payment_processor.cart_payment_interface.payment_repo.find_pgp_payment_intents = FunctionMock(
            return_value=[generate_pgp_payment_intent(payment_intent_id=intent.id)]
        )

        cart_payment_processor.cart_payment_interface.payment_repo.get_cart_payment_by_id = FunctionMock(
            return_value=request_cart_payment
        )

        # Submit when lookup functions mocked above return a result, meaning we have existing cart payment/intent
        result = await cart_payment_processor.submit_payment(
            request_cart_payment=request_cart_payment,
            idempotency_key=str(uuid.uuid4()),
            country="US",
            currency="USD",
            client_description="Client description",
        )
        assert result

        cart_payment_processor.cart_payment_interface.payment_repo.get_cart_payment_by_id = FunctionMock(
            return_value=result
        )

        # Second submission attempt
        second_result = await cart_payment_processor.submit_payment(
            request_cart_payment=request_cart_payment,
            idempotency_key=str(uuid.uuid4()),
            country="US",
            currency="USD",
            client_description="Client description",
        )
        assert second_result
        assert result == second_result

    @pytest.mark.asyncio
    async def test_update_fake_cart_payment(self, cart_payment_processor):
        cart_payment_processor.cart_payment_interface.payment_repo.get_cart_payment_by_id = FunctionMock(
            return_value=None
        )

        with pytest.raises(CartPaymentReadError) as payment_error:
            await cart_payment_processor.update_payment(
                idempotency_key=str(uuid.uuid4()),
                cart_payment_id=uuid.uuid4(),
                payer_id="payer_id",
                amount=500,
                legacy_payment=None,
                client_description=None,
            )
        assert (
            payment_error.value.error_code
            == PayinErrorCode.CART_PAYMENT_NOT_FOUND.value
        )

    @pytest.mark.asyncio
    async def test_update_payment_higher(self, cart_payment_processor):
        cart_payment = generate_cart_payment()
        updated_amount = cart_payment.amount + 100
        result = await cart_payment_processor.update_payment(
            idempotency_key=str(uuid.uuid4()),
            cart_payment_id=cart_payment.id,
            payer_id=cart_payment.payer_id,
            amount=updated_amount,
            legacy_payment=None,
            client_description=None,
        )
        assert result
        assert result.id == cart_payment.id
        assert result.amount == updated_amount

    @pytest.mark.asyncio
    async def test_update_payment_higher_after_capture(self, cart_payment_processor):
        # Mock interactions with other layers
        cart_payment = generate_cart_payment()
        updated_amount = cart_payment.amount + 100
        result = await cart_payment_processor.update_payment(
            idempotency_key=str(uuid.uuid4()),
            cart_payment_id=cart_payment.id,
            payer_id=cart_payment.payer_id,
            amount=updated_amount,
            legacy_payment=None,
            client_description=None,
        )
        assert result
        assert result.id == cart_payment.id
        assert result.amount == updated_amount
