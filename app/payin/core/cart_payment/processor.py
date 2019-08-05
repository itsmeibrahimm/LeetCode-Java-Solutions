from asyncio import gather
from fastapi import HTTPException
from typing import Dict, Tuple, List, Optional
import uuid

from app.commons.context.app_context import AppContext
from app.commons.context.req_context import ReqContext
from app.commons.types import CountryCode
from app.commons.providers.stripe_models import CreatePaymentIntent
from app.commons.utils.types import PaymentProvider
from app.payin.core.cart_payment.model import (
    CartPayment,
    PaymentIntent,
    PgpPaymentIntent,
)
from app.payin.core.cart_payment.types import (
    ConfirmationMethod,
    PaymentIntentStatus,
    PgpPaymentIntentStatus,
)

from app.payin.repository.cart_payment_repo import CartPaymentRepository


class CartPaymentInterface:
    def __init__(
        self,
        app_context: AppContext,
        req_context: ReqContext,
        payment_repo: CartPaymentRepository,
    ):
        self.app_context = app_context
        self.req_context = req_context
        self.payment_repo = payment_repo

    async def find_existing(
        self, payer_id: str, idempotency_key: str
    ) -> Tuple[Optional[CartPayment], Optional[PaymentIntent]]:
        payment_intent = await self.payment_repo.get_payment_intent_for_idempotency_key(
            idempotency_key
        )

        if not payment_intent:
            return (None, None)

        cart_payment = await self.payment_repo.get_cart_payment_by_id(
            payment_intent.cart_payment_id
        )

        return (cart_payment, payment_intent)

    def _get_sample_response(self):
        # Return an example reponse from Stripe, for payment intent creation.
        # TODO Delete this once we have integration tests in place.  This is only useful for local manual testing.
        return {
            "id": "pi_1DWxxK2eZvKYlo2CFnwDZCQP",
            "object": "payment_intent",
            "amount": 2000,
            "amount_capturable": 0,
            "amount_received": 0,
            "application": None,
            "application_fee_amount": None,
            "canceled_at": None,
            "cancellation_reason": None,
            "capture_method": "automatic",
            "charges": {
                "object": "list",
                "data": [],
                "has_more": False,
                "total_count": 0,
                "url": "/v1/charges?payment_intent=pi_1DWxxK2eZvKYlo2CFnwDZCQP",
            },
            "client_secret": "pi_bogus_value",
            "confirmation_method": "automatic",
            "created": 1542338718,
            "currency": "usd",
            "customer": None,
            "description": "Gold fish #20793",
            "invoice": None,
            "last_payment_error": None,
            "livemode": False,
            "metadata": {},
            "next_action": None,
            "on_behalf_of": None,
            "payment_method": None,
            "payment_method_options": {},
            "payment_method_types": ["card"],
            "receipt_email": None,
            "review": None,
            "setup_future_usage": None,
            "shipping": None,
            "source": None,
            "statement_descriptor": None,
            "status": "requires_payment_method",
            "transfer_data": None,
            "transfer_group": None,
        }

    async def _create_provider_payment(
        self, payment_intent: PaymentIntent, pgp_payment_intent: PgpPaymentIntent
    ):
        # Call to stripe payment intent API
        try:
            # TODO add idempotency_key
            intent_request: CreatePaymentIntent = CreatePaymentIntent(
                amount=pgp_payment_intent.amount,
                currency=pgp_payment_intent.currency,
                application_fee_amount=pgp_payment_intent.application_fee_amount,
                capture_method=CreatePaymentIntent.CaptureMethod.manual,
                confirm=False,
                confirmation_method=CreatePaymentIntent.ConfirmationMethod.manual,
                on_behalf_of=pgp_payment_intent.payout_account_id,
                setup_future_usage="off_session",
                payment_method=pgp_payment_intent.payment_method_resource_id,
                statement_descriptor=payment_intent.statement_descriptor,
            )
            response = await self.app_context.stripe.create_payment_intent(
                country=CountryCode(payment_intent.country), request=intent_request
            )
            # req_context.log.info("Stripe response:")
            # req_context.log.info(response)
            return response
            # return self._get_sample_response()
        except Exception as e:
            # TODO Add better error handling here
            self.req_context.log.error(f"Error invoking provider: {e}")
            raise HTTPException(status_code=500, detail="Internal error")

    # req_context, payin_repos, pgp_intent_id, provider_payment_response
    async def _update_pgp_intent_from_provider(
        self,
        pgp_intent_id: uuid.UUID,
        status: PgpPaymentIntentStatus,
        provider_payment_response: Dict,
    ) -> None:
        await self.payment_repo.update_pgp_payment_intent(
            pgp_intent_id,
            status,
            provider_payment_response["id"],
            provider_payment_response["amount"],
            provider_payment_response["amount_capturable"],
            provider_payment_response["amount_received"],
            provider_payment_response["application_fee_amount"],
        )

    async def _submit_payment_to_provider(
        self, payment_intent: PaymentIntent, pgp_payment_intent: PgpPaymentIntent
    ):
        # Call out to provider to create the payment intent in their system
        provider_payment_response = await self._create_provider_payment(
            payment_intent=payment_intent, pgp_payment_intent=pgp_payment_intent
        )

        # TODO Create a transaction

        # Update the records we created to reflect that the provider has been invoked.
        await gather(
            self.payment_repo.update_payment_intent_status(
                payment_intent.id, PaymentIntentStatus.PROCESSING
            ),
            self._update_pgp_intent_from_provider(
                pgp_payment_intent.id,
                PgpPaymentIntentStatus.PROCESSING,
                provider_payment_response,
            ),
        )

        # TODO Commit and close transaction

    async def submit_new_payment(
        self,
        request_cart_payment: CartPayment,
        idempotency_key: str,
        country: str,
        currency: str,
        client_description: str,
    ):
        # Create a new cart payment, with associated models
        self.req_context.log.debug(
            f"Submitting new payment for payer ${request_cart_payment.payer_id}"
        )

        # TODO Start transaction

        # Create CartPayment
        cart_payment: CartPayment = await self.payment_repo.insert_cart_payment(
            id=uuid.uuid4(),
            payer_id=request_cart_payment.payer_id,
            type=request_cart_payment.cart_metadata.type,
            reference_id=request_cart_payment.cart_metadata.reference_id,
            reference_ct_id=request_cart_payment.cart_metadata.ct_reference_id,
            legacy_consumer_id=request_cart_payment.legacy_payment.consumer_id
            if request_cart_payment.legacy_payment
            else None,
            amount_original=request_cart_payment.amount,
            amount_total=request_cart_payment.amount,
        )

        # Create PaymentIntent
        payment_intent: PaymentIntent = await self.payment_repo.insert_payment_intent(
            id=uuid.uuid4(),
            cart_payment_id=cart_payment.id,
            idempotency_key=idempotency_key,
            amount_initiated=request_cart_payment.amount,
            amount=request_cart_payment.amount,
            application_fee_amount=getattr(
                request_cart_payment.split_payment, "application_fee_amount", None
            ),
            country=country,
            currency=currency,
            capture_method=request_cart_payment.capture_method,
            confirmation_method=ConfirmationMethod.MANUAL,
            status=PaymentIntentStatus.INIT,
            statement_descriptor=request_cart_payment.payer_statement_description,
        )

        # Create PgpPaymentIntent
        pgp_payment_intent: PgpPaymentIntent = await self.payment_repo.insert_pgp_payment_intent(
            id=uuid.uuid4(),
            payment_intent_id=payment_intent.id,
            idempotency_key=idempotency_key,
            provider=PaymentProvider.STRIPE.value,
            payment_method_resource_id=request_cart_payment.payment_method_id,
            currency=currency,
            amount=request_cart_payment.amount,
            application_fee_amount=getattr(
                request_cart_payment.split_payment, "application_fee_amount", None
            ),
            payout_account_id=getattr(
                request_cart_payment.split_payment, "payout_account_id", None
            ),
            capture_method=request_cart_payment.capture_method,
            confirmation_method=ConfirmationMethod.MANUAL,
            status=PgpPaymentIntentStatus.INIT,
            statement_descriptor=request_cart_payment.payer_statement_description,
        )

        # TODO Commit and close transaction.  Close transaction prior to external call.

        await self._submit_payment_to_provider(payment_intent, pgp_payment_intent)
        return cart_payment

    def _get_cart_payment_submission_pgp_intent(
        self, pgp_intents: List[PgpPaymentIntent]
    ) -> PgpPaymentIntent:
        # Since cart_payment/payment_intent/pgp_payment_intent are first created in one transaction,
        # we will have at least one.  Find the first one, since this is an attempt to recreate the
        # cart_payment.
        return pgp_intents[0]

    def _is_payment_intent_submitted(self, payment_intent: PaymentIntent):
        return payment_intent.status != PaymentIntentStatus.INIT

    def _is_pgp_payment_intent_submitted(self, pgp_payment_intent: PgpPaymentIntent):
        return pgp_payment_intent.status != PaymentIntentStatus.INIT

    async def resubmit_existing_payment(
        self, cart_payment: CartPayment, payment_intent: PaymentIntent
    ) -> CartPayment:
        """
        Resubmit an existing cart payment.  Intended to be used for second calls to create a cart payment for the same idempotency key.

        Arguments:
            cart_payment {CartPayment} -- The CartPayment instance to resubmit.
            payment_intent {PaymentIntent} -- The associated PaymentIntent instance for the cart payment.

        Returns:
            CartPayment -- The (resubmitted) CartPayment.
        """
        assert cart_payment.id == payment_intent.cart_payment_id
        # Handle creation attempts of the same cart_payment/payment_intent
        if self._is_payment_intent_submitted(payment_intent):
            # Already submitted, nothing left to do.
            return cart_payment

        # Check state of call to provider/PgpPaymentIntent: resubmit if necessary
        pgp_intents = await self.payment_repo.find_pgp_payment_intents(
            payment_intent.id
        )

        pgp_intent = self._get_cart_payment_submission_pgp_intent(pgp_intents)
        if self._is_pgp_payment_intent_submitted(pgp_intent):
            return cart_payment

        self.req_context.log.info(
            f"Attempting resubmission of payment to provider for cart_payment {cart_payment.id}, payment_intent {payment_intent.id}, pgp_payment_intent {pgp_intent.id if pgp_intent else 'None'}"
        )
        await self._submit_payment_to_provider(payment_intent, pgp_intent)
        return cart_payment


async def submit_payment(
    app_context: AppContext,
    req_context: ReqContext,
    payment_repo: CartPaymentRepository,
    request_cart_payment: CartPayment,
    idempotency_key: str,
    country: str,
    currency: str,
    client_description: str,
) -> CartPayment:
    """Submit a cart payment creation request.

    Arguments:
        app_context {AppContext} -- Application context.
        req_context {ReqContext} -- Request context.
        payment_repo {CartPaymentRepository} -- Repo for accessing CartPayment and associated models.
        request_cart_payment {CartPayment} -- CartPayment model containing request paramters provided by client.
        idempotency_key {str} -- Client specified value for ensuring idempotency.
        country {str} -- ISO country code.
        currency {str} -- Currency for cart payment request.
        client_description {str} -- Pass through value clients may associated with the cart payment.

    Returns:
        CartPayment -- A CartPayment model for the created payment.
    """
    # Check for resubmission by client
    cart_payment_interface = CartPaymentInterface(
        app_context, req_context, payment_repo
    )

    cart_payment, payment_intent = await cart_payment_interface.find_existing(
        request_cart_payment.payer_id, idempotency_key
    )
    if cart_payment:
        assert payment_intent
        return await cart_payment_interface.resubmit_existing_payment(
            cart_payment, payment_intent
        )

    return await cart_payment_interface.submit_new_payment(
        request_cart_payment, idempotency_key, country, currency, client_description
    )
