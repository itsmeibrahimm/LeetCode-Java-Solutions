from copy import deepcopy
import pytest
from unittest.mock import MagicMock
from app.payin.core.exceptions import (
    CartPaymentReadError,
    PayinErrorCode,
    PaymentMethodReadError,
)
from app.payin.core.payment_method.processor import PaymentMethodClient
from app.payin.core.types import PayerIdType, PaymentMethodIdType
import app.payin.core.cart_payment.processor as processor
from app.payin.tests.utils import (
    generate_payment_intent,
    generate_pgp_payment_intent,
    generate_cart_payment,
    ContextMock,
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
    def cart_payment_repo(self):
        cart_payment_repo = MagicMock()
        cart_payment_repo.get_payment_intent_for_idempotency_key = FunctionMock(
            return_value=None
        )
        cart_payment_repo.payment_database_transaction = ContextMock()
        cart_payment_repo.insert_cart_payment = FunctionMock(
            return_value=generate_cart_payment()
        )
        cart_payment_repo.insert_payment_intent = FunctionMock(
            return_value=generate_payment_intent()
        )
        cart_payment_repo.insert_pgp_payment_intent = FunctionMock(
            return_value=generate_pgp_payment_intent()
        )
        cart_payment_repo.update_payment_intent_status = FunctionMock()
        cart_payment_repo.update_pgp_payment_intent = FunctionMock()
        return cart_payment_repo

    @pytest.fixture
    def payment_method_client(self, payment_method_repo):
        return PaymentMethodClient(
            payment_method_repository=payment_method_repo, log=MagicMock()
        )

    async def test_submit_with_no_payment_method(
        self, request_cart_payment, payment_method_repo, payment_method_client
    ):
        cart_payment_interface = processor.CartPaymentInterface(
            app_context=MagicMock(),
            req_context=MagicMock(),
            payment_repo=MagicMock(),
            payer_repo=MagicMock(),
            payment_method_repo=payment_method_repo,
            payment_method_client=payment_method_client,
        )

        # No payment method found
        payment_method_repo.get_pgp_payment_method_by_payment_method_id = FunctionMock(
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
        self, request_cart_payment, payment_method_repo, payment_method_client
    ):
        request_cart_payment.payer_id = f"changed-{request_cart_payment.payer_id}"

        cart_payment_interface = processor.CartPaymentInterface(
            app_context=MagicMock(),
            req_context=MagicMock(),
            payment_repo=MagicMock(),
            payer_repo=MagicMock(),
            payment_method_repo=payment_method_repo,
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

    async def test_submit(
        self,
        request_cart_payment,
        cart_payment_repo,
        payer_repo,
        payment_method_repo,
        payment_method_client,
    ):
        app_context = MagicMock()
        app_context.stripe = MagicMock()
        app_context.stripe.create_payment_intent = FunctionMock()

        cart_payment_interface = processor.CartPaymentInterface(
            app_context=app_context,
            req_context=MagicMock(),
            payment_repo=cart_payment_repo,
            payer_repo=payer_repo,
            payment_method_repo=payment_method_repo,
            payment_method_client=payment_method_client,
        )

        cart_payment_processor = processor.CartPaymentProcessor(
            cart_payment_interface=cart_payment_interface
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

    async def test_resubmit(
        self,
        request_cart_payment,
        cart_payment_repo,
        payer_repo,
        payment_method_repo,
        payment_method_client,
    ):
        app_context = MagicMock()
        app_context.stripe = MagicMock()
        app_context.stripe.create_payment_intent = FunctionMock()

        payment_method_repo.get_payment_intent_for_idempotency_key = FunctionMock(
            return_value=generate_payment_intent()
        )
        cart_payment_repo.get_cart_payment_by_id = FunctionMock(
            return_value=request_cart_payment
        )

        cart_payment_interface = processor.CartPaymentInterface(
            app_context=app_context,
            req_context=MagicMock(),
            payment_repo=cart_payment_repo,
            payer_repo=payer_repo,
            payment_method_repo=payment_method_repo,
            payment_method_client=payment_method_client,
        )

        cart_payment_processor = processor.CartPaymentProcessor(
            cart_payment_interface=cart_payment_interface
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

        # Second submission attempt
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

    @pytest.mark.asyncio
    async def test_update_fake_cart_payment(self, cart_payment_repo):
        payment_repo = MagicMock()
        payment_repo.get_cart_payment_by_id = FunctionMock(return_value=None)

        cart_payment_interface = processor.CartPaymentInterface(
            app_context=MagicMock(),
            req_context=MagicMock(),
            payment_repo=payment_repo,
            payer_repo=MagicMock(),
            payment_method_repo=MagicMock(),
            payment_method_client=MagicMock(),
        )

        cart_payment_processor = processor.CartPaymentProcessor(
            cart_payment_interface=cart_payment_interface
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
    async def test_update_payment_higher(
        self,
        request_cart_payment,
        cart_payment_repo,
        payer_repo,
        payment_method_repo,
        payment_method_client,
    ):
        # TODO move some of the mocking into the fixutre, if it is common across different test functions
        app_context = MagicMock()
        app_context.stripe = MagicMock()
        app_context.stripe.cancel_payment_intent = FunctionMock(
            return_value="pgp_id_cancel"
        )
        app_context.stripe.create_payment_intent = FunctionMock(
            return_value="pgp_id_create"
        )

        # Submit when lookup functions mocked above return a result, meaning we have existing cart payment/intent
        cart_payment = generate_cart_payment()
        existing_intent = generate_payment_intent(
            cart_payment_id=cart_payment.id, status="requires_capture"
        )
        existing_pgp_intent = generate_pgp_payment_intent(
            payment_intent_id=existing_intent.id, status="requires_capture"
        )

        # Mock interactions with other layers
        cart_payment_repo.get_cart_payment_by_id = FunctionMock(
            return_value=cart_payment
        )
        cart_payment_repo.get_payment_intents_for_cart_payment = FunctionMock(
            return_value=[existing_intent]
        )
        cart_payment_repo.find_pgp_payment_intents = FunctionMock(
            return_value=[existing_pgp_intent]
        )
        updated_cart_payment = deepcopy(cart_payment)
        updated_cart_payment.amount = cart_payment.amount + 100
        cart_payment_repo.update_cart_payment_details = FunctionMock(
            return_value=updated_cart_payment
        )
        cart_payment_repo.insert_payment_intent_adjustment_history = FunctionMock(
            return_value=MagicMock()
        )

        cart_payment_interface = processor.CartPaymentInterface(
            app_context=app_context,
            req_context=MagicMock(),
            payment_repo=cart_payment_repo,
            payer_repo=payer_repo,
            payment_method_repo=payment_method_repo,
            payment_method_client=payment_method_client,
        )

        cart_payment_processor = processor.CartPaymentProcessor(
            cart_payment_interface=cart_payment_interface
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
