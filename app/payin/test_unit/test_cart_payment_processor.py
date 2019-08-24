from copy import deepcopy
import pytest
from unittest.mock import MagicMock
from app.payin.core.exceptions import (
    CartPaymentReadError,
    PayinErrorCode,
    PaymentMethodReadError,
)
from app.payin.core.payer.processor import PayerClient
from app.payin.core.payment_method.processor import PaymentMethodClient
from app.payin.core.types import PayerIdType, PaymentMethodIdType
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
    Test external facing functions exposed by app/payin/ccore/cart_payment/processor.py.
    """

    @pytest.fixture
    def request_cart_payment(self):
        return generate_cart_payment()

    @pytest.fixture
    def payment_method_repo(self, request_cart_payment):
        mocked_payment_method_object = MagicMock()
        mocked_payment_method_object.pgp_resource_id = "test"
        mocked_payment_method_object.payer_id = request_cart_payment.payer_id

        payment_method_repo = MagicMock()
        payment_method_repo.get_pgp_payment_method_by_payment_method_id = FunctionMock(
            return_value=mocked_payment_method_object
        )

        payment_method_repo.get_stripe_card_by_stripe_id = FunctionMock(
            return_value=MagicMock()
        )
        return payment_method_repo

    @pytest.fixture
    def payer_repo(self):
        payer_repo = MagicMock()

        mocked_customer_object = MagicMock()
        mocked_customer_object.pgp_resource_id = "test"
        payer_repo.get_pgp_customer = FunctionMock(return_value=mocked_customer_object)
        return payer_repo

    @pytest.fixture
    def payment_method_client(self, payment_method_repo):
        return PaymentMethodClient(
            payment_method_repo=payment_method_repo,
            log=MagicMock(),
            app_ctxt=MagicMock(),
        )

    @pytest.fixture
    def payer_client(self, payer_repo):
        return PayerClient(payer_repo=payer_repo, log=MagicMock(), app_ctxt=MagicMock())

    @pytest.fixture
    def cart_payment_processor(self, cart_payment_interface):
        return processor.CartPaymentProcessor(cart_payment_interface)

    async def test_submit_with_no_payment_method(
        self,
        cart_payment_processor,
        request_cart_payment,
        payment_method_repo,
        payer_client,
        payment_method_client,
    ):
        cart_payment_interface = processor.CartPaymentInterface(
            app_context=MagicMock(),
            req_context=MagicMock(),
            payment_repo=MagicMock(),
            payer_client=payer_client,
            payment_method_client=payment_method_client,
        )

        # No payment method found
        payment_method_repo.get_pgp_payment_method_by_payment_method_id = FunctionMock(
            return_value=None
        )
        cart_payment_processor.cart_payment_interface.payment_repo.get_pgp_payment_method_by_payment_method_id = FunctionMock(
            return_value=None
        )

        cart_payment_processor = processor.CartPaymentProcessor(
            cart_payment_interface=cart_payment_interface
        )

        with pytest.raises(PaymentMethodReadError) as payment_error:
            await cart_payment_processor.submit_payment(
                request_cart_payment=request_cart_payment,
                idempotency_key=uuid.uuid4(),
                country="US",
                currency="USD",
                client_description="Client description",
                payer_id_type=PayerIdType.DD_PAYMENT_PAYER_ID,
                payment_method_id_type=PaymentMethodIdType.PAYMENT_PAYMENT_METHOD_ID,
            )
        assert (
            payment_error.value.error_code
            == PayinErrorCode.PAYMENT_METHOD_GET_NOT_FOUND.value
        )

    async def test_submit_with_other_owner(
        self, request_cart_payment, payer_client, payment_method_client
    ):
        # Avoid mocking of payment_method_client done in the cart_payment_processor fixture, as we need
        # the actual check to fail in order to ensure we see the proper exception.
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
                idempotency_key=uuid.uuid4(),
                country="US",
                currency="USD",
                client_description="Client description",
                payer_id_type=PayerIdType.DD_PAYMENT_PAYER_ID,
                payment_method_id_type=PaymentMethodIdType.PAYMENT_PAYMENT_METHOD_ID,
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
        cart_payment = generate_cart_payment()
        cart_payment_processor.cart_payment_interface.payment_repo.insert_cart_payment = FunctionMock(
            return_value=cart_payment
        )

        new_intent = generate_payment_intent()
        cart_payment_processor.cart_payment_interface.payment_repo.insert_payment_intent = FunctionMock(
            return_value=new_intent
        )
        cart_payment_processor.cart_payment_interface.payment_repo.insert_pgp_payment_intent = FunctionMock(
            return_value=generate_pgp_payment_intent(payment_intent_id=new_intent.id)
        )

        result = await cart_payment_processor.submit_payment(
            request_cart_payment=request_cart_payment,
            idempotency_key=uuid.uuid4(),
            country="US",
            currency="USD",
            client_description="Client description",
            payer_id_type=PayerIdType.DD_PAYMENT_PAYER_ID,
            payment_method_id_type=PaymentMethodIdType.PAYMENT_PAYMENT_METHOD_ID,
        )
        assert result
        assert result.id

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
            idempotency_key=uuid.uuid4(),
            country="US",
            currency="USD",
            client_description="Client description",
            payer_id_type=PayerIdType.DD_PAYMENT_PAYER_ID,
            payment_method_id_type=PaymentMethodIdType.PAYMENT_PAYMENT_METHOD_ID,
        )
        assert result

        cart_payment_processor.cart_payment_interface.payment_repo.get_cart_payment_by_id = FunctionMock(
            return_value=result
        )

        # Second submission attempt
        second_result = await cart_payment_processor.submit_payment(
            request_cart_payment=request_cart_payment,
            idempotency_key=uuid.uuid4(),
            country="US",
            currency="USD",
            client_description="Client description",
            payer_id_type=PayerIdType.DD_PAYMENT_PAYER_ID,
            payment_method_id_type=PaymentMethodIdType.PAYMENT_PAYMENT_METHOD_ID,
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
                idempotency_key=uuid.uuid4(),
                cart_payment_id=uuid.uuid4(),
                payer_id="payer_id",
                amount=500,
                legacy_payment=None,
                client_description=None,
                payer_statement_description=None,
                metadata=None,
            )
        assert (
            payment_error.value.error_code
            == PayinErrorCode.CART_PAYMENT_NOT_FOUND.value
        )

    @pytest.mark.asyncio
    async def test_update_payment_higher(self, cart_payment_processor):
        # Mock interactions with other layers
        cart_payment = generate_cart_payment()
        existing_intent = generate_payment_intent(
            cart_payment_id=cart_payment.id, status="requires_capture"
        )
        existing_pgp_intent = generate_pgp_payment_intent(
            payment_intent_id=existing_intent.id, status="requires_capture"
        )

        cart_payment_processor.cart_payment_interface.payment_repo.get_cart_payment_by_id = FunctionMock(
            return_value=cart_payment
        )
        cart_payment_processor.cart_payment_interface.payment_repo.get_payment_intents_for_cart_payment = FunctionMock(
            return_value=[existing_intent]
        )
        cart_payment_processor.cart_payment_interface.payment_repo.find_pgp_payment_intents = FunctionMock(
            return_value=[existing_pgp_intent]
        )

        new_intent = generate_payment_intent(
            cart_payment_id=cart_payment.id, status="requires_capture"
        )
        cart_payment_processor.cart_payment_interface.payment_repo.insert_payment_intent = FunctionMock(
            return_value=new_intent
        )
        cart_payment_processor.cart_payment_interface.payment_repo.insert_pgp_payment_intent = FunctionMock(
            return_value=generate_pgp_payment_intent(
                payment_intent_id=existing_intent.id, status="requires_capture"
            )
        )

        updated_cart_payment = deepcopy(cart_payment)
        updated_cart_payment.amount = cart_payment.amount + 100
        cart_payment_processor.cart_payment_interface.payment_repo.update_cart_payment_details = FunctionMock(
            return_value=updated_cart_payment
        )

        result = await cart_payment_processor.update_payment(
            idempotency_key=uuid.uuid4(),
            cart_payment_id=cart_payment.id,
            payer_id=cart_payment.payer_id,
            amount=(cart_payment.amount + 100),
            legacy_payment=None,
            client_description=None,
            payer_statement_description=None,
            metadata=None,
        )
        assert result == updated_cart_payment

    @pytest.mark.asyncio
    async def test_update_payment_higher_after_capture(self, cart_payment_processor):
        # Mock interactions with other layers
        cart_payment = generate_cart_payment()
        existing_intent = generate_payment_intent(
            cart_payment_id=cart_payment.id, status="succeeded"
        )
        existing_pgp_intent = generate_pgp_payment_intent(
            payment_intent_id=existing_intent.id, status="succeeded"
        )

        cart_payment_processor.cart_payment_interface.payment_repo.get_cart_payment_by_id = FunctionMock(
            return_value=cart_payment
        )
        cart_payment_processor.cart_payment_interface.payment_repo.get_payment_intents_for_cart_payment = FunctionMock(
            return_value=[existing_intent]
        )
        cart_payment_processor.cart_payment_interface.payment_repo.find_pgp_payment_intents = FunctionMock(
            return_value=[existing_pgp_intent]
        )

        new_intent = generate_payment_intent(
            cart_payment_id=cart_payment.id, status="requires_capture"
        )
        cart_payment_processor.cart_payment_interface.payment_repo.insert_payment_intent = FunctionMock(
            return_value=new_intent
        )
        cart_payment_processor.cart_payment_interface.payment_repo.insert_pgp_payment_intent = FunctionMock(
            return_value=generate_pgp_payment_intent(
                payment_intent_id=existing_intent.id, status="requires_capture"
            )
        )

        cart_payment_processor.cart_payment_interface._filter_payment_intents_by_idempotency_key = MagicMock(
            return_value=None
        )
        cart_payment_processor.cart_payment_interface.payment_repo.update_payment_charge = FunctionMock(
            return_value=MagicMock()
        )
        cart_payment_processor.cart_payment_interface.payment_repo.update_pgp_payment_charge = FunctionMock(
            return_value=MagicMock()
        )
        cart_payment_processor.cart_payment_interface.payment_repo.update_payment_intent_amount = FunctionMock(
            return_value=generate_payment_intent()
        )
        cart_payment_processor.cart_payment_interface.payment_repo.update_pgp_payment_intent_amount = FunctionMock(
            return_value=generate_pgp_payment_intent()
        )

        updated_cart_payment = deepcopy(cart_payment)
        updated_cart_payment.amount = cart_payment.amount + 100
        cart_payment_processor.cart_payment_interface.payment_repo.update_cart_payment_details = FunctionMock(
            return_value=updated_cart_payment
        )

        result = await cart_payment_processor.update_payment(
            idempotency_key=uuid.uuid4(),
            cart_payment_id=cart_payment.id,
            payer_id=cart_payment.payer_id,
            amount=(cart_payment.amount + 100),
            legacy_payment=None,
            client_description=None,
            payer_statement_description=None,
            metadata=None,
        )
        assert result == updated_cart_payment
