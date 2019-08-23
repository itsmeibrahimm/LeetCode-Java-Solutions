from asyncio import gather
import uuid
from typing import Tuple, List, Optional, Callable

from fastapi import Depends

from app.commons.context.app_context import AppContext, get_global_app_context
from app.commons.context.req_context import ReqContext, get_context_from_req
from app.commons.providers.stripe.stripe_models import (
    CapturePaymentIntent,
    CreatePaymentIntent,
    CancelPaymentIntent,
    RefundCharge,
    PaymentIntent as ProviderPaymentIntent,
    Refund as ProviderRefund,
)
from app.commons.types import CountryCode
from app.commons.utils.types import PaymentProvider
from app.payin.core.types import PayerIdType, PaymentMethodIdType
from app.payin.core.cart_payment.model import (
    CartMetadata,
    CartPayment,
    LegacyPayment,
    PaymentIntent,
    PgpPaymentIntent,
    PaymentCharge,
    PgpPaymentCharge,
)
from app.payin.core.exceptions import (
    PayinErrorCode,
    CartPaymentCreateError,
    CartPaymentReadError,
    PaymentIntentCaptureError,
    PaymentIntentCancelError,
    PaymentIntentRefundError,
    PaymentChargeRefundError,
)
from app.payin.core.cart_payment.types import (
    CaptureMethod,
    ConfirmationMethod,
    IntentStatus,
    ChargeStatus,
)
from app.payin.core.payment_method.processor import PaymentMethodClient
from app.payin.repository.cart_payment_repo import CartPaymentRepository
from app.payin.repository.payment_method_repo import PaymentMethodRepository
from app.payin.repository.payer_repo import PayerRepository, GetPgpCustomerInput


class CartPaymentInterface:
    def __init__(
        self,
        app_context: AppContext = Depends(get_global_app_context),
        req_context: ReqContext = Depends(get_context_from_req),
        payment_repo: CartPaymentRepository = Depends(
            CartPaymentRepository.get_repository
        ),
        payer_repo: PayerRepository = Depends(PayerRepository.get_repository),
        payment_method_repo: PaymentMethodRepository = Depends(
            PaymentMethodRepository.get_repository
        ),
        payment_method_client: PaymentMethodClient = Depends(PaymentMethodClient),
    ):
        self.app_context = app_context
        self.req_context = req_context
        self.payment_repo = payment_repo
        self.payer_repo = payer_repo
        self.payment_method_repo = payment_method_repo
        self.payment_method_client = payment_method_client

    async def _find_existing(
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

    async def _get_cart_payment(
        self, cart_payment_id: uuid.UUID
    ) -> Optional[CartPayment]:
        return await self.payment_repo.get_cart_payment_by_id(cart_payment_id)

    async def _get_most_recent_pgp_payment_intent(self, payment_intent: PaymentIntent):
        pgp_intents = await self.payment_repo.find_pgp_payment_intents(
            payment_intent.id
        )
        pgp_intents.sort(key=lambda x: x.created_at)
        return pgp_intents[-1]

    def _transform_method_for_stripe(self, method_name: str) -> str:
        if method_name == "auto":
            return "automatic"
        return method_name

    def _get_provider_capture_method(
        self, pgp_payment_intent: PgpPaymentIntent
    ) -> CreatePaymentIntent.CaptureMethod:
        target_method = self._transform_method_for_stripe(
            pgp_payment_intent.capture_method
        )
        return CreatePaymentIntent.CaptureMethod(target_method)

    def _get_provider_confirmation_method(
        self, pgp_payment_intent: PgpPaymentIntent
    ) -> CreatePaymentIntent.ConfirmationMethod:
        target_method = self._transform_method_for_stripe(
            pgp_payment_intent.confirmation_method
        )
        return CreatePaymentIntent.ConfirmationMethod(target_method)

    def _get_provider_future_usage(self, payment_intent: PaymentIntent) -> str:
        if payment_intent.capture_method == CaptureMethod.AUTO:
            return CreatePaymentIntent.SetupFutureUsage.ON_SESSION

        return CreatePaymentIntent.SetupFutureUsage.OFF_SESSION

    def _get_cart_payment_submission_pgp_intent(
        self, pgp_intents: List[PgpPaymentIntent]
    ) -> PgpPaymentIntent:
        # Since cart_payment/payment_intent/pgp_payment_intent are first created in one transaction,
        # we will have at least one.  Find the first one, since this is an attempt to recreate the
        # cart_payment.
        # TODO fix this logic
        return pgp_intents[0]

    def _filter_payment_intents_by_state(
        self, intents: List[PaymentIntent], status: IntentStatus
    ) -> List[PaymentIntent]:
        return list(filter(lambda intent: intent.status == status.value, intents))

    def _filter_payment_intents_by_idempotency_key(
        self, intents: List[PaymentIntent], idempotency_key: str
    ) -> Optional[PaymentIntent]:
        matched_intents = list(
            filter(lambda intent: intent.idempotency_key == idempotency_key, intents)
        )

        return matched_intents[0] if matched_intents else None

    def _filter_payment_intents_by_function(
        self,
        payment_intents: List[PaymentIntent],
        filter_function: Callable[[PaymentIntent], bool],
    ) -> List[PaymentIntent]:
        return list(filter(lambda intent: filter_function(intent), payment_intents))

    def _is_payment_intent_submitted(self, payment_intent: PaymentIntent) -> bool:
        return payment_intent.status != IntentStatus.INIT

    def _can_payment_intent_be_cancelled(self, payment_intent: PaymentIntent) -> bool:
        # Not yet captured.  SCA related states will be added here later.
        return payment_intent.status in [IntentStatus.REQUIRES_CAPTURE]

    def _can_payment_intent_be_refunded(self, payment_intent: PaymentIntent) -> bool:
        return payment_intent.status == IntentStatus.SUCCEEDED

    def _can_pgp_payment_intent_be_refunded(
        self, pgp_payment_intent: PgpPaymentIntent
    ) -> bool:
        return pgp_payment_intent.status == IntentStatus.SUCCEEDED

    def _has_capture_been_attempted(self, payment_intent: PaymentIntent) -> bool:
        return payment_intent.status in [IntentStatus.SUCCEEDED, IntentStatus.FAILED]

    def _get_intent_status_from_provider_status(
        self, provider_status: str
    ) -> IntentStatus:
        return IntentStatus(provider_status)

    def _get_charge_status_from_intent_status(
        self, intent_status: IntentStatus
    ) -> ChargeStatus:
        # Charge status is a subset of Intent status
        return ChargeStatus(intent_status)

    def _get_most_recent_intent(
        self, intent_list: List[PaymentIntent]
    ) -> PaymentIntent:
        intent_list.sort(key=lambda x: x.created_at)
        return intent_list[-1]

    def _is_pgp_payment_intent_submitted(self, pgp_payment_intent: PgpPaymentIntent):
        return pgp_payment_intent.status != IntentStatus.INIT

    def _is_amount_adjusted_higher(
        self, cart_payment: CartPayment, amount: int
    ) -> bool:
        return amount > cart_payment.amount

    def _is_amount_adjusted_lower(self, cart_payment: CartPayment, amount: int) -> bool:
        return amount < cart_payment.amount

    async def _create_provider_payment(
        self,
        payment_intent: PaymentIntent,
        pgp_payment_intent: PgpPaymentIntent,
        provider_payment_resource_id: str,
        provider_customer_resource_id: str,
    ) -> ProviderPaymentIntent:
        # Call to stripe payment intent API
        try:
            intent_request = CreatePaymentIntent(
                amount=pgp_payment_intent.amount,
                currency=pgp_payment_intent.currency,
                application_fee_amount=pgp_payment_intent.application_fee_amount,
                capture_method=self._get_provider_capture_method(pgp_payment_intent),
                confirm=True,
                confirmation_method=self._get_provider_confirmation_method(
                    pgp_payment_intent
                ),
                on_behalf_of=pgp_payment_intent.payout_account_id,
                setup_future_usage=self._get_provider_future_usage(payment_intent),
                payment_method=provider_payment_resource_id,
                customer=provider_customer_resource_id,
                statement_descriptor=payment_intent.statement_descriptor,
            )

            response = await self.app_context.stripe.create_payment_intent(
                country=CountryCode(payment_intent.country),
                request=intent_request,
                idempotency_key=pgp_payment_intent.idempotency_key,
            )
            return response
        except Exception as e:
            self.req_context.log.error(
                f"Error invoking provider to create a payment intent: {e}"
            )
            raise CartPaymentCreateError(
                error_code=PayinErrorCode.PAYMENT_INTENT_CREATE_STRIPE_ERROR,
                retryable=False,
            )

    async def _submit_payment_to_provider(
        self,
        payment_intent: PaymentIntent,
        pgp_payment_intent: PgpPaymentIntent,
        provider_payment_resource_id: str,
        provider_customer_resource_id: str,
    ) -> None:
        # Call out to provider to create the payment intent in their system.  The payment_intent
        # instance includes the idempotency_key, which is passed to provider to ensure records already
        # submitted are actually processed only once.
        self.req_context.log.debug(
            f"Creating new intent with provider.  IDs: {payment_intent.id}, {pgp_payment_intent.id}"
        )
        provider_payment_intent = await self._create_provider_payment(
            payment_intent=payment_intent,
            pgp_payment_intent=pgp_payment_intent,
            provider_payment_resource_id=provider_payment_resource_id,
            provider_customer_resource_id=provider_customer_resource_id,
        )

        async with self.payment_repo.payment_database_transaction():
            # Update the records we created to reflect that the provider has been invoked.
            # Cannot gather calls here because of shared connection/transaction
            await self.payment_repo.update_payment_intent_status(
                id=payment_intent.id, status=IntentStatus.REQUIRES_CAPTURE
            )
            await self.payment_repo.update_pgp_payment_intent(
                id=pgp_payment_intent.id,
                status=IntentStatus.REQUIRES_CAPTURE,
                resource_id=provider_payment_intent.id,
                charge_resource_id=provider_payment_intent.charges.data[0].id,
            )
            await self._create_new_charge_pair(
                payment_intent=payment_intent,
                pgp_payment_intent=pgp_payment_intent,
                provider_intent=provider_payment_intent,
            )

        # Depending on configuration, submitting payment to provider may require immediate capture.
        if self._is_capture_immediate(payment_intent):
            await self.capture_payment(payment_intent)

    async def _update_charge_pair_after_capture(
        self,
        payment_intent: PaymentIntent,
        status: ChargeStatus,
        provider_intent: ProviderPaymentIntent,
    ) -> Tuple[PaymentCharge, PgpPaymentCharge]:
        # Assumption: this is called within a transaction already
        # TODO add a config parameter and switch between writing to payin db and main db legacy tables.
        payment_charge = await self.payment_repo.update_payment_charge_status(
            payment_intent.id, status.value
        )
        pgp_charge = await self._update_pgp_charge_from_provider(
            payment_charge.id, status, provider_intent
        )
        return payment_charge, pgp_charge

    async def _update_charge_pair_after_refund(
        self, payment_intent: PaymentIntent, provider_refund: ProviderRefund
    ) -> Tuple[PaymentCharge, PgpPaymentCharge]:
        # Assumption: this is called within a transaction already
        # TODO add a config parameter and switch between writing to payin db and main db legacy tables.
        status = ChargeStatus(provider_refund.status)
        payment_charge = await self.payment_repo.update_payment_charge(
            payment_intent_id=payment_intent.id,
            status=status.value,
            amount_refunded=provider_refund.amount,
        )
        pgp_charge = await self.payment_repo.update_pgp_payment_charge(
            payment_charge_id=payment_charge.id,
            status=status.value,
            amount=provider_refund.amount,
            amount_refunded=provider_refund.amount,
        )
        return payment_charge, pgp_charge

    async def _update_charge_pair_after_amount_reduction(
        self, payment_intent: PaymentIntent, amount: int
    ) -> Tuple[PaymentCharge, PgpPaymentCharge]:
        # Assumption: this is called within a transaction already
        # TODO add a config parameter and switch between writing to payin db and main db legacy tables
        payment_charge = await self.payment_repo.update_payment_charge_amount(
            payment_intent_id=payment_intent.id, amount=amount
        )
        pgp_charge = await self.payment_repo.update_pgp_payment_charge_amount(
            payment_charge_id=payment_charge.id, amount=amount
        )
        return payment_charge, pgp_charge

    async def _capture_payment_with_provider(
        self, payment_intent: PaymentIntent, pgp_payment_intent: PgpPaymentIntent
    ) -> ProviderPaymentIntent:
        # Call to stripe payment intent API
        try:
            intent_request = CapturePaymentIntent(sid=pgp_payment_intent.resource_id)

            self.req_context.log.info(
                f"Capturing payment intent: {payment_intent.country}, key: {pgp_payment_intent.idempotency_key}"
            )
            provider_intent = await self.app_context.stripe.capture_payment_intent(
                country=CountryCode(payment_intent.country),
                request=intent_request,
                idempotency_key=str(uuid.uuid4()),  # TODO handle idempotency key
            )
        except Exception as e:
            self.req_context.log.error(f"Error capturing intent with provider: {e}")
            raise PaymentIntentCaptureError(
                error_code=PayinErrorCode.PAYMENT_INTENT_CAPTURE_STRIPE_ERROR,
                retryable=False,
            )

        new_intent_status = self._get_intent_status_from_provider_status(
            provider_intent.status
        )
        new_charge_status = self._get_charge_status_from_intent_status(
            new_intent_status
        )
        self.req_context.log.debug(
            f"Updating intent {payment_intent.id}, pgp intent {pgp_payment_intent.id} to status {new_intent_status}"
        )

        # Update state
        async with self.payment_repo.payment_database_transaction():
            # TODO try gather
            await self.payment_repo.update_payment_intent_status(
                payment_intent.id, new_intent_status
            )
            await self.payment_repo.update_pgp_payment_intent_status(
                pgp_payment_intent.id, new_intent_status
            )
            await self._update_charge_pair_after_capture(
                payment_intent, new_charge_status, provider_intent
            )

        return provider_intent

    async def _cancel_provider_payment_charge(
        self,
        payment_intent: PaymentIntent,
        pgp_payment_intent: PgpPaymentIntent,
        reason,
    ) -> str:
        try:
            intent_request = CancelPaymentIntent(
                sid=pgp_payment_intent.resource_id, cancellation_reason=reason
            )

            self.req_context.log.info(
                f"Cancelling payment intent: {payment_intent.id}, key: {pgp_payment_intent.idempotency_key}"
            )
            response = await self.app_context.stripe.cancel_payment_intent(
                country=CountryCode(payment_intent.country),
                request=intent_request,
                idempotency_key=str(uuid.uuid4()),  # TODO handle idempotency key
            )
            self.req_context.log.debug(f"Provider response: {response}")
            return response
        except Exception as e:
            self.req_context.log.error(f"Error refunding payment with provider: {e}")
            raise PaymentChargeRefundError(
                error_code=PayinErrorCode.PAYMENT_INTENT_ADJUST_REFUND_ERROR,
                retryable=False,
            )

    async def _refund_provider_payment(
        self,
        payment_intent: PaymentIntent,
        pgp_payment_intent: PgpPaymentIntent,
        reason: str,
        amount: int,
    ) -> ProviderRefund:
        try:
            refund_request = RefundCharge(
                charge=pgp_payment_intent.charge_resource_id,
                amount=amount,
                reason=reason,
            )

            self.req_context.log.info(
                f"Refunding charge {pgp_payment_intent.charge_resource_id}"
            )
            response = await self.app_context.stripe.refund_charge(
                country=CountryCode(payment_intent.country),
                request=refund_request,
                idempotency_key=str(uuid.uuid4()),  # TODO handle idempotency key
            )
            self.req_context.log.debug(f"Provider response: {response}")
            return response
        except Exception as e:
            self.req_context.log.error(f"Error cancelling charge with provider: {e}")
            raise PaymentIntentCancelError(
                error_code=PayinErrorCode.PAYMENT_INTENT_ADJUST_REFUND_ERROR,
                retryable=False,
            )

    async def _update_pgp_charge_from_provider(
        self,
        payment_charge_id: uuid.UUID,
        status: ChargeStatus,
        provider_intent: ProviderPaymentIntent,
    ):
        charge = provider_intent.charges.data[0]
        return await self.payment_repo.update_pgp_payment_charge(
            payment_charge_id=payment_charge_id,
            status=status.value,
            amount=charge.amount,
            amount_refunded=charge.amount_refunded,
        )

    def _populate_cart_payment_for_response(
        self,
        cart_payment: CartPayment,
        payment_intent: PaymentIntent,
        pgp_payment_intent: PgpPaymentIntent,
    ):
        """
        Populate fields within a CartPayment instance to be suitable for an API response body.
        Since CartPayment is a view on top of several models, it is necessary to synthesize info
        into a CartPayment instance from associated models.

        Arguments:
            cart_payment {CartPayment} -- The CartPayment instance to update.
            payment_intent {PaymentIntent} -- An associated PaymentIntent.
            pgp_payment_intent {PgpPaymentIntent} -- An associated PgpPaymentIntent.
        """
        cart_payment.capture_method = payment_intent.capture_method
        cart_payment.payer_statement_description = payment_intent.statement_descriptor
        cart_payment.payment_method_id = pgp_payment_intent.payment_method_resource_id

    def is_accessible(
        self, cart_payment: CartPayment, request_payer_id: str, credential_owner: str
    ) -> bool:
        # TODO verify the caller (as identified by the provided credentials for this request) owns the cart payment
        # From credential_owner, get payer_id
        # return cart_payment.payer_id == payer_id and cart_payment.payer_id == request_payer_id
        return True

    def _is_capture_immediate(self, payment_intent: PaymentIntent) -> bool:
        # TODO control percentage of intents for delayed capture here with a config parameter
        return False
        # return True

    async def _create_new_charge_pair(
        self,
        payment_intent: PaymentIntent,
        pgp_payment_intent: PgpPaymentIntent,
        provider_intent: ProviderPaymentIntent,
    ) -> Tuple[PaymentCharge, PgpPaymentCharge]:
        # TODO Add config parameter that switches between writing to payment db and legacy tables in main db, and support
        # writing to those legacy tables for backward compatibility.
        payment_charge = await self.payment_repo.insert_payment_charge(
            id=uuid.uuid4(),
            payment_intent_id=payment_intent.id,
            provider=PaymentProvider.STRIPE.value,
            idempotency_key=str(uuid.uuid4()),  # TODO handle idempotency key
            status=ChargeStatus.REQUIRES_CAPTURE,
            currency=payment_intent.currency,
            amount=payment_intent.amount,
            amount_refunded=0,
            application_fee_amount=payment_intent.application_fee_amount,
            payout_account_id=pgp_payment_intent.payout_account_id,
        )

        provider_charges = provider_intent.charges
        if len(provider_charges.data) > 1:
            # Upon creation, there is expected to be one provider charge.
            self.req_context.log.warn(
                f"Multiple pgp charges at time of creation for intent {payment_intent.id}, pgp intent {pgp_payment_intent.id}"
            )
        provider_charge = provider_charges.data[0]
        pgp_payment_charge = await self.payment_repo.insert_pgp_payment_charge(
            id=uuid.uuid4(),
            payment_charge_id=payment_charge.id,
            provider=PaymentProvider.STRIPE.value,
            idempotency_key=payment_charge.idempotency_key,
            status=ChargeStatus.REQUIRES_CAPTURE,
            currency=provider_charge.currency,
            amount=provider_charge.amount,
            amount_refunded=provider_charge.amount_refunded,
            application_fee_amount=provider_charge.application_fee_amount,
            payout_account_id=provider_charge.on_behalf_of,
            resource_id=provider_charge.id,
            intent_resource_id=provider_charge.payment_intent,
            invoice_resource_id=provider_charge.invoice,
            payment_method_resource_id=provider_charge.payment_method,
        )

        return payment_charge, pgp_payment_charge

    async def _create_new_intent_pair(
        self,
        cart_payment: CartPayment,
        idempotency_key: str,
        payment_method_id: str,
        amount: int,
        country: str,
        currency: str,
        capture_method: str,
        payer_statement_description: Optional[str] = None,
    ) -> Tuple[PaymentIntent, PgpPaymentIntent]:
        # Create PaymentIntent
        payment_intent = await self.payment_repo.insert_payment_intent(
            id=uuid.uuid4(),
            cart_payment_id=cart_payment.id,
            idempotency_key=idempotency_key,
            amount_initiated=amount,
            amount=amount,
            application_fee_amount=getattr(
                cart_payment.split_payment, "application_fee_amount", None
            ),
            country=country,
            currency=currency,
            capture_method=capture_method,
            confirmation_method=ConfirmationMethod.MANUAL,
            status=IntentStatus.INIT,
            statement_descriptor=payer_statement_description,
        )

        # Create PgpPaymentIntent
        pgp_payment_intent = await self.payment_repo.insert_pgp_payment_intent(
            id=uuid.uuid4(),
            payment_intent_id=payment_intent.id,
            idempotency_key=idempotency_key,
            provider=PaymentProvider.STRIPE.value,
            payment_method_resource_id=payment_method_id,
            currency=currency,
            amount=amount,
            application_fee_amount=getattr(
                cart_payment.split_payment, "application_fee_amount", None
            ),
            payout_account_id=getattr(
                cart_payment.split_payment, "payout_account_id", None
            ),
            capture_method=capture_method,
            confirmation_method=ConfirmationMethod.MANUAL,
            status=IntentStatus.INIT,
            statement_descriptor=payer_statement_description,
        )

        return (payment_intent, pgp_payment_intent)

    async def submit_new_payment(
        self,
        request_cart_payment: CartPayment,
        provider_payment_resource_id: str,
        provider_customer_resource_id: str,
        idempotency_key: str,
        country: str,
        currency: str,
        client_description: str,
    ) -> Tuple[CartPayment, PaymentIntent]:
        # Create a new cart payment, with associated models
        self.req_context.log.info(
            f"Submitting new payment for payer {request_cart_payment.payer_id}"
        )

        # Required as inputs to creation API, but optional in model.  Verify we have the required fields.
        # TODO add codes to distinguish between different cases for client
        if (
            not request_cart_payment.capture_method
            or not request_cart_payment.payment_method_id
        ):
            raise CartPaymentCreateError(
                error_code=PayinErrorCode.CART_PAYMENT_CREATE_INVALID_DATA,
                retryable=False,
            )

        async with self.payment_repo.payment_database_transaction():
            # Create CartPayment
            cart_payment = await self.payment_repo.insert_cart_payment(
                id=request_cart_payment.id,
                payer_id=request_cart_payment.payer_id,
                type=request_cart_payment.cart_metadata.type,
                client_description=request_cart_payment.client_description,
                reference_id=request_cart_payment.cart_metadata.reference_id,
                reference_ct_id=request_cart_payment.cart_metadata.ct_reference_id,
                legacy_consumer_id=request_cart_payment.legacy_payment.consumer_id
                if request_cart_payment.legacy_payment
                else None,
                amount_original=request_cart_payment.amount,
                amount_total=request_cart_payment.amount,
            )

            payment_intent, pgp_payment_intent = await self._create_new_intent_pair(
                cart_payment=cart_payment,
                idempotency_key=idempotency_key,
                payment_method_id=request_cart_payment.payment_method_id,
                amount=cart_payment.amount,
                country=country,
                currency=currency,
                capture_method=request_cart_payment.capture_method,
                payer_statement_description=request_cart_payment.payer_statement_description,
            )

        await self._submit_payment_to_provider(
            payment_intent,
            pgp_payment_intent,
            provider_payment_resource_id,
            provider_customer_resource_id,
        )
        self._populate_cart_payment_for_response(
            cart_payment, payment_intent, pgp_payment_intent
        )
        return cart_payment, payment_intent

    async def resubmit_existing_payment(
        self,
        cart_payment: CartPayment,
        payment_intent: PaymentIntent,
        provider_payment_resource_id: str,
        provider_customer_resource_id: str,
    ) -> CartPayment:
        """
        Resubmit an existing cart payment.  Intended to be used for second calls to create a cart payment for the same idempotency key.

        Arguments:
            cart_payment {CartPayment} -- The CartPayment instance to resubmit.
            payment_intent {PaymentIntent} -- The associated PaymentIntent instance for the cart payment.

        Returns:
            CartPayment -- The (resubmitted) CartPayment.
        """
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
        await self._submit_payment_to_provider(
            payment_intent,
            pgp_intent,
            provider_payment_resource_id,
            provider_customer_resource_id,
        )
        self._populate_cart_payment_for_response(
            cart_payment, payment_intent, pgp_intent
        )
        return cart_payment

    async def _update_charge_pair_after_cancel(
        self, payment_intent: PaymentIntent, status: ChargeStatus
    ) -> Tuple[PaymentCharge, PgpPaymentCharge]:
        # Assumption: this is called within a transaction already
        # TODO add a config parameter and switch between writing to payin db and main db legacy tables.
        payment_charge = await self.payment_repo.update_payment_charge_status(
            payment_intent_id=payment_intent.id, status=status.value
        )
        pgp_payment_charge = await self.payment_repo.update_pgp_payment_charge_status(
            payment_charge_id=payment_charge.id, status=status.value
        )
        return payment_charge, pgp_payment_charge

    async def _cancel_intent(
        self, payment_intent: PaymentIntent, pgp_payment_intents: List[PgpPaymentIntent]
    ):
        self.req_context.log.info(f"Cancelling payment intent {payment_intent.id}")
        # TODO handle case where there are multiple pgp intents
        pgp_payment_intent = pgp_payment_intents[0]
        await self._cancel_provider_payment_charge(
            payment_intent,
            pgp_payment_intent,
            CancelPaymentIntent.CancellationReason.ABANDONED,
        )

        async with self.payment_repo.payment_database_transaction():
            await self.payment_repo.update_payment_intent_status(
                id=payment_intent.id, status=IntentStatus.CANCELLED
            )
            await self.payment_repo.update_pgp_payment_intent_status(
                id=pgp_payment_intent.id, status=IntentStatus.CANCELLED
            )
            await self.payment_repo.update_pgp_payment_intent_status(
                id=pgp_payment_intent.id, status=IntentStatus.CANCELLED
            )
            await self._update_charge_pair_after_cancel(
                payment_intent=payment_intent, status=ChargeStatus.CANCELLED
            )

    async def _refund_intent(
        self,
        payment_intent: PaymentIntent,
        pgp_payment_intents: List[PgpPaymentIntent],
        amount: int,
    ) -> Tuple[PaymentIntent, PgpPaymentIntent]:
        self.req_context.log.info(
            f"Refunding payment intent {payment_intent.id} for amount {amount}"
        )
        # TODO handle case where there may be multiple pgp_payment_intents
        pgp_payment_intent = pgp_payment_intents[0]
        if not self._can_pgp_payment_intent_be_refunded(pgp_payment_intent):
            self.req_context.log.error(
                f"Attempt to refund pgp intent {pgp_payment_intent.id} in invalid state {pgp_payment_intent.status}"
            )
            raise PaymentIntentRefundError(
                error_code=PayinErrorCode.PAYMENT_INTENT_ADJUST_REFUND_ERROR,
                retryable=False,
            )

        # TODO verify if pgp intent can be refunded: may have been refunded previously, protect against
        # exceeding limits (avoid call to provider if not necessary)

        refund = await self._refund_provider_payment(
            payment_intent=payment_intent,
            pgp_payment_intent=pgp_payment_intent,
            reason=RefundCharge.RefundReason.REQUESTED_BY_CONSUMER,
            amount=amount,
        )

        async with self.payment_repo.payment_database_transaction():
            await self._update_charge_pair_after_refund(
                payment_intent=payment_intent, provider_refund=refund
            )

        return payment_intent, pgp_payment_intent

    async def _get_required_payment_resource_ids(
        self,
        payer_id: str,
        payer_id_type: PayerIdType,
        payment_method_id,
        payment_method_id_type: PaymentMethodIdType,
    ) -> Tuple[str, str]:
        assert self.payer_repo
        assert self.payment_method_repo
        # Get payment method, in order to submit new intent to the provider

        payment_method, stripe_card = await self.payment_method_client.get_payment_method(
            payer_id=payer_id,
            payment_method_id=payment_method_id,
            payer_id_type=payer_id_type,
            payment_method_id_type=payment_method_id_type,
        )

        # TODO add more error_code values to help client distinguish error cases
        if not payment_method or not payment_method.pgp_resource_id:
            raise CartPaymentCreateError(
                error_code=PayinErrorCode.CART_PAYMENT_CREATE_INVALID_DATA,
                retryable=False,
            )

        # TODO Get customer ID from payer processor
        pgp_customer = await self.payer_repo.get_pgp_customer(
            GetPgpCustomerInput(payer_id=payer_id)
        )
        if not pgp_customer:
            raise CartPaymentCreateError(
                error_code=PayinErrorCode.CART_PAYMENT_CREATE_INVALID_DATA,
                retryable=False,
            )

        return payment_method.pgp_resource_id, pgp_customer.pgp_resource_id

    async def _resubmit_add_amount_to_cart_payment(
        self, cart_payment: CartPayment, payment_intent: PaymentIntent
    ) -> Tuple[PaymentIntent, PgpPaymentIntent]:
        pgp_intent = await self._get_most_recent_pgp_payment_intent(payment_intent)
        # There is already an intent with the client specified idempotency key, so this is a resubmit attempt.
        if self._is_payment_intent_submitted(payment_intent):
            # If intent is already done (success or fail), we can immediately return
            self.req_context.log.info(
                f"Resubmit request for cart payment {cart_payment.id} update"
            )
            return payment_intent, pgp_intent

        # Intent is in init state, so there may have been an issue with calling provider.  Call again.
        payment_resource_id, customer_resource_id = await self._get_required_payment_resource_ids(
            cart_payment.payer_id,
            PayerIdType.DD_PAYMENT_PAYER_ID,
            pgp_intent.payment_method_resource_id,
            PaymentMethodIdType.PAYMENT_PAYMENT_METHOD_ID,
        )
        await self._submit_payment_to_provider(
            payment_intent, pgp_intent, payment_resource_id, customer_resource_id
        )

        return payment_intent, pgp_intent

    async def _submit_amount_increase_to_cart_payment(
        self,
        cart_payment: CartPayment,
        most_recent_intent: PaymentIntent,
        amount: int,
        idempotency_key: str,
    ) -> Tuple[PaymentIntent, PgpPaymentIntent]:
        self.req_context.log.info(
            f"New intent for cart payment {cart_payment.id}, due to higher amount {amount} (from {cart_payment.amount})"
        )
        # Get payment resource IDs, required for submitting intent to providers
        pgp_intent = await self._get_most_recent_pgp_payment_intent(most_recent_intent)
        self.req_context.log.debug(f"Gathering fields from last intent {pgp_intent.id}")

        payment_resource_id, customer_resource_id = await self._get_required_payment_resource_ids(
            cart_payment.payer_id,
            PayerIdType.DD_PAYMENT_PAYER_ID,
            pgp_intent.payment_method_resource_id,
            PaymentMethodIdType.PAYMENT_PAYMENT_METHOD_ID,
        )

        # New intent pair for the higher amount
        async with self.payment_repo.payment_database_transaction():
            payment_intent_for_submit, pgp_intent_for_submit = await self._create_new_intent_pair(
                cart_payment=cart_payment,
                idempotency_key=idempotency_key,
                payment_method_id=pgp_intent.payment_method_resource_id,
                amount=amount,
                country=most_recent_intent.country,
                currency=most_recent_intent.currency,
                capture_method=most_recent_intent.capture_method,
                payer_statement_description=most_recent_intent.statement_descriptor,
            )

            # Insert adjustment history record
            # TODO consider adding cart_payment_id
            await self.payment_repo.insert_payment_intent_adjustment_history(
                id=uuid.uuid4(),
                payer_id=cart_payment.payer_id,
                payment_intent_id=payment_intent_for_submit.id,
                amount=amount,
                amount_original=cart_payment.amount,
                amount_delta=(amount - cart_payment.amount),
                currency=payment_intent_for_submit.currency,
            )

            self.req_context.log.info(
                f"Created intent pair {payment_intent_for_submit.id}, {pgp_intent_for_submit.id}"
            )

        await self._submit_payment_to_provider(
            payment_intent_for_submit,
            pgp_intent_for_submit,
            payment_resource_id,
            customer_resource_id,
        )

        return payment_intent_for_submit, pgp_intent_for_submit

    async def _add_amount_to_cart_payment(
        self,
        cart_payment: CartPayment,
        idempotency_key: str,
        payment_intents: List[PaymentIntent],
        amount: int,
        legacy_payment: Optional[LegacyPayment],
        client_description: Optional[str],
        payer_statement_description: Optional[str],
        metadata: Optional[CartMetadata],
    ) -> CartPayment:
        self.req_context.log.info(
            f"Adjusting amount higher to {amount} from {cart_payment.amount} for cart payment {cart_payment.id}"
        )
        existing_intent = self._filter_payment_intents_by_idempotency_key(
            payment_intents, idempotency_key
        )

        if existing_intent:
            # Second attempt to adjust cart payment amount, with same idempotency key
            payment_intent, pgp_payment_intent = await self._resubmit_add_amount_to_cart_payment(
                cart_payment, existing_intent
            )
        else:
            # First attempt at cart payment adjustment for this idempotency key.
            # Immutable properties, such as currency, are derived from the previous/most recent intent in order to
            # have these fields for new intent submission and keep API simple for clients.
            most_recent_intent = self._get_most_recent_intent(payment_intents)
            payment_intent, pgp_payment_intent = await self._submit_amount_increase_to_cart_payment(
                cart_payment, most_recent_intent, amount, idempotency_key
            )

        # Cancel previous intents
        intent_operations = []
        for intent in payment_intents:
            if self._can_payment_intent_be_cancelled(intent):
                # Intent not yet captured: it can be cancelled.
                intent_operations.append(
                    self._cancel_intent(
                        intent,
                        await self.payment_repo.find_pgp_payment_intents(intent.id),
                    )
                )
            elif self._can_payment_intent_be_refunded(intent):
                # The intent cannot be cancelled because its state is beyond capture.  Instead we must refund
                intent_operations.append(
                    self._refund_intent(
                        intent,
                        await self.payment_repo.find_pgp_payment_intents(intent.id),
                        intent.amount,
                    )
                )
            # No need for else block here: If not able to cancel or refund, no action is needed (for example, intent is in failed state).

        if len(intent_operations) > 0:
            self.req_context.log.info(
                f"Cancelling intents for cart payment {cart_payment.id}"
            )
            await gather(*intent_operations)

        # Update properties of the cart payment
        return await self._update_cart_payment_attributes(
            cart_payment=cart_payment,
            idempotency_key=idempotency_key,
            payment_intent=payment_intent,
            pgp_payment_intent=pgp_payment_intent,
            amount=amount,
            client_description=client_description,
        )

    async def _record_amount_decrease(
        self,
        cart_payment: CartPayment,
        payment_intent: PaymentIntent,
        pgp_payment_intent: PgpPaymentIntent,
        amount: int,
    ) -> Tuple[PaymentIntent, PgpPaymentIntent]:
        async with self.payment_repo.payment_database_transaction():
            updated_intent = await self.payment_repo.update_payment_intent_amount(
                id=payment_intent.id, amount=amount
            )
            updated_pgp_intent = await self.payment_repo.update_pgp_payment_intent_amount(
                id=pgp_payment_intent.id, amount=amount
            )
            await self._update_charge_pair_after_amount_reduction(
                payment_intent=payment_intent, amount=amount
            )
            await self.payment_repo.insert_payment_intent_adjustment_history(
                id=uuid.uuid4(),
                payer_id=cart_payment.payer_id,
                payment_intent_id=payment_intent.id,
                amount=amount,
                amount_original=cart_payment.amount,
                amount_delta=(amount - cart_payment.amount),
                currency=payment_intent.currency,
            )

        return updated_intent, updated_pgp_intent

    async def _submit_refund_to_cart_payment(
        self, cart_payment: CartPayment, payment_intent: PaymentIntent, amount: int
    ):
        refunded_intent, refunded_pgp_intent = await self._refund_intent(
            payment_intent,
            await self.payment_repo.find_pgp_payment_intents(payment_intent.id),
            payment_intent.amount - amount,
        )

        return await self._record_amount_decrease(
            cart_payment=cart_payment,
            payment_intent=refunded_intent,
            pgp_payment_intent=refunded_pgp_intent,
            amount=amount,
        )

    async def _submit_amount_decrease_to_cart_payment(
        self, cart_payment: CartPayment, payment_intent: PaymentIntent, amount: int
    ):
        # TODO handle case where there are multiple pgp intents
        pgp_payment_intents = await self.payment_repo.find_pgp_payment_intents(
            payment_intent.id
        )
        pgp_payment_intent = pgp_payment_intents[0]

        # There is no need to call provider at this point in time.  The original auth done upon cart payment
        # creation is sufficient to cover a lower amount, so there is no need to update the amount with the provider.
        # Instead we will record updated amounts in our system, which will be reflected at time of (delayed) capture.

        return await self._record_amount_decrease(
            cart_payment=cart_payment,
            payment_intent=payment_intent,
            pgp_payment_intent=pgp_payment_intent,
            amount=amount,
        )

    async def _deduct_amount_from_cart_payment(
        self,
        cart_payment: CartPayment,
        idempotency_key: str,
        payment_intents: List[PaymentIntent],
        amount: int,
        legacy_payment: Optional[LegacyPayment],
        client_description: Optional[str],
        payer_statement_description: Optional[str],
        metadata: Optional[CartMetadata],
    ) -> CartPayment:
        self.req_context.log.info(
            f"Adjusting amount lower to {amount} from {cart_payment.amount} for cart payment {cart_payment.id}"
        )

        capturable_intents = self._filter_payment_intents_by_state(
            payment_intents, IntentStatus.REQUIRES_CAPTURE
        )

        # TODO handle resubmit case via idempotency key

        if capturable_intents:
            # If there are any uncaptured intents suitable for this amount change, update
            capturable_intent = self._get_most_recent_intent(capturable_intents)
            payment_intent, pgp_payment_intent = await self._submit_amount_decrease_to_cart_payment(
                cart_payment=cart_payment,
                payment_intent=capturable_intent,
                amount=amount,
            )
        else:
            # If there are no uncaptured intents suitable for this amount change, a refund is necessary.
            refundable_intents = self._filter_payment_intents_by_function(
                payment_intents, self._can_payment_intent_be_refunded
            )
            refundable_intent = self._get_most_recent_intent(refundable_intents)
            payment_intent, pgp_payment_intent = await self._submit_refund_to_cart_payment(
                cart_payment=cart_payment,
                payment_intent=refundable_intent,
                amount=amount,
            )

        # Update properties of the cart payment
        return await self._update_cart_payment_attributes(
            cart_payment=cart_payment,
            idempotency_key=idempotency_key,
            payment_intent=payment_intent,
            pgp_payment_intent=pgp_payment_intent,
            amount=amount,
            client_description=client_description,
        )

    async def _update_cart_payment_attributes(
        self,
        cart_payment: CartPayment,
        idempotency_key: str,
        payment_intent: PaymentIntent,
        pgp_payment_intent: PgpPaymentIntent,
        amount: int,
        client_description: Optional[str],
    ) -> CartPayment:
        updated_cart_payment = await self.payment_repo.update_cart_payment_details(
            cart_payment_id=cart_payment.id,
            amount=amount,
            client_description=client_description,
        )
        self._populate_cart_payment_for_response(
            updated_cart_payment, payment_intent, pgp_payment_intent
        )
        return updated_cart_payment

    async def update_payment(
        self,
        cart_payment: CartPayment,
        idempotency_key: str,
        amount: int,
        legacy_payment: Optional[LegacyPayment],
        client_description: Optional[str],
        payer_statement_description: Optional[str],
        metadata: Optional[CartMetadata],
    ) -> CartPayment:
        # Update the amount of a cart payment.  Includes managing underlying/associated payment intent/pgp payment intents.

        # TODO concurrency control for attempts to update the same cart payment

        payment_intents = await self.payment_repo.get_payment_intents_for_cart_payment(
            cart_payment.id
        )

        if self._is_amount_adjusted_higher(cart_payment, amount):
            updated_cart_payment = await self._add_amount_to_cart_payment(
                cart_payment=cart_payment,
                idempotency_key=idempotency_key,
                payment_intents=payment_intents,
                amount=amount,
                legacy_payment=legacy_payment,
                client_description=client_description,
                payer_statement_description=payer_statement_description,
                metadata=metadata,
            )
        elif self._is_amount_adjusted_lower(cart_payment, amount):
            updated_cart_payment = await self._deduct_amount_from_cart_payment(
                cart_payment=cart_payment,
                idempotency_key=idempotency_key,
                payment_intents=payment_intents,
                amount=amount,
                legacy_payment=legacy_payment,
                client_description=client_description,
                payer_statement_description=payer_statement_description,
                metadata=metadata,
            )
            pass
        else:
            # Amount is the same: properties of cart payment other than the amount may be changing
            payment_intent = self._get_most_recent_intent(payment_intents)
            # TODO handle case where there are multiple pgp intents
            pgp_payment_intents = await self.payment_repo.find_pgp_payment_intents(
                payment_intent.id
            )
            updated_cart_payment = await self._update_cart_payment_attributes(
                cart_payment=cart_payment,
                idempotency_key=idempotency_key,
                payment_intent=payment_intent,
                pgp_payment_intent=pgp_payment_intents[0],
                amount=amount,
                client_description=client_description,
            )

        return updated_cart_payment

    async def capture_payment(self, payment_intent: PaymentIntent) -> None:
        """Capture a payment intent.

        Arguments:
            payment_intent {PaymentIntent} -- The PaymentIntent to capture.

        Raises:
            e: Raises an exception if database operations fail.

        Returns:
            None
        """
        self.req_context.log.info(
            f"Capture attempt for payment_intent {payment_intent.id}"
        )
        # TODO scheduling of this logic
        # TODO concurrency control to ensure we are capturing something once (though underlying provider call will be idempotent)
        # Check state of intent.  If already captured (successfully or not), stop.  Clients are expected to
        if self._has_capture_been_attempted(payment_intent):
            self.req_context.log.info(
                f"Payment intent not eligible for capturing, in state {payment_intent.status}"
            )
            return

        # Find the PgpPaymentIntent to capture
        pgp_intents = await self.payment_repo.find_pgp_payment_intents(
            payment_intent.id
        )
        # TODO work through case where there may be multiples
        pgp_payment_intent = pgp_intents[0]

        # Call to provider to capture, with idempotency key
        await self._capture_payment_with_provider(payment_intent, pgp_payment_intent)
        # TODO update captured_at dates, amounts


class CartPaymentProcessor:
    def __init__(
        self,
        cart_payment_interface: CartPaymentInterface = Depends(CartPaymentInterface),
    ):
        self.cart_payment_interface = cart_payment_interface

    async def update_payment(
        self,
        idempotency_key: str,
        cart_payment_id: uuid.UUID,
        payer_id: str,
        amount: int,
        legacy_payment: Optional[LegacyPayment],
        client_description: Optional[str],
        payer_statement_description: Optional[str],
        metadata: Optional[CartMetadata],
    ) -> CartPayment:
        """Update an existing payment.

        Arguments:
            payment_method_repo {PaymentMethodRepository} -- Repo for accessing PaymentMethod and associated models.
            idempotency_key {str} -- Client specified value for ensuring idempotency.
            cart_payment_id {uuid.UUID} -- ID of the cart payment to adjust.
            payer_id {str} -- ID of the payer who owns the specified cart payment.
            amount {int} -- New amount to use for cart payment.
            legacy_payment {Optional[LegacyPayment]} -- Legacy payment, for support legacy clients.
            client_description {Optional[str]} -- New client description to use for cart payment.
            payer_statement_description {Optional[str]} -- New payer statement description to use for cart payment.
            metadata {Optional[CartMetadata]} -- Metadata of cart payment.

        Raises:
            CartPaymentReadError: Raised when there is an error retrieving the specified cart payment.

        Returns:
            CartPayment -- An updated CartPayment instance, reflecting changes requested by the client.
        """

        # Get the payment intent by ID
        cart_payment = await self.cart_payment_interface._get_cart_payment(
            cart_payment_id
        )
        if not cart_payment:
            raise CartPaymentReadError(
                error_code=PayinErrorCode.CART_PAYMENT_NOT_FOUND, retryable=False
            )

        # Ensure the caller can access the cart payment being modified
        if not self.cart_payment_interface.is_accessible(cart_payment, payer_id, ""):
            raise CartPaymentReadError(
                error_code=PayinErrorCode.CART_PAYMENT_OWNER_MISMATCH, retryable=False
            )

        # Update the cart payment
        return await self.cart_payment_interface.update_payment(
            cart_payment,
            idempotency_key,
            amount,
            legacy_payment,
            client_description,
            payer_statement_description,
            metadata,
        )

    async def submit_payment(
        self,
        request_cart_payment: CartPayment,
        idempotency_key: str,
        country: str,
        currency: str,
        client_description: str,
        payer_id_type: PayerIdType,
        payment_method_id_type: PaymentMethodIdType,
    ) -> CartPayment:
        """Submit a cart payment creation request.

        Arguments:
            request_cart_payment {CartPayment} -- CartPayment model containing request paramters provided by client.
            idempotency_key {str} -- Client specified value for ensuring idempotency.
            country {str} -- ISO country code.
            currency {str} -- Currency for cart payment request.
            client_description {str} -- Pass through value clients may associated with the cart payment.
            payer_id_type {PayerIdType} -- Type for payer ID, to support legacy clients.
            payment_method_id_type {PaymentMethodIdType} -- Type for payment method ID, to support legacy clients.

        Returns:
            CartPayment -- A CartPayment model for the created payment.
        """
        # TODO: Validate amount does not exceed configured max for specified currency

        if not request_cart_payment.payment_method_id:
            raise CartPaymentCreateError(
                error_code=PayinErrorCode.CART_PAYMENT_CREATE_INVALID_DATA,
                retryable=False,
            )

        # If payment method is not found or not owned by the specified payer, an exception is raised and handled by
        # our exception handling middleware.
        payment_method_resource_id, customer_resource_id = await self.cart_payment_interface._get_required_payment_resource_ids(
            payer_id=request_cart_payment.payer_id,
            payer_id_type=payer_id_type,
            payment_method_id=request_cart_payment.payment_method_id,
            payment_method_id_type=payment_method_id_type,
        )

        # Check for resubmission by client
        cart_payment, payment_intent = await self.cart_payment_interface._find_existing(
            request_cart_payment.payer_id, idempotency_key
        )
        if cart_payment:
            assert payment_intent
            return await self.cart_payment_interface.resubmit_existing_payment(
                cart_payment,
                payment_intent,
                payment_method_resource_id,
                customer_resource_id,
            )

        cart_payment, payment_intent = await self.cart_payment_interface.submit_new_payment(
            request_cart_payment,
            payment_method_resource_id,
            customer_resource_id,
            idempotency_key,
            country,
            currency,
            client_description,
        )

        return cart_payment
