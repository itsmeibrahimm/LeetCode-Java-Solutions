import uuid
from asyncio import gather
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

from doordash_python_stats.ddstats import doorstats_global
from fastapi import Depends
from structlog.stdlib import BoundLogger

from app.commons import tracing
from app.commons.context.req_context import get_logger_from_req
from app.commons.lock.locks import PaymentLock, PaymentLockAcquireError
from app.commons.providers.stripe.stripe_models import (
    PaymentIntent as ProviderPaymentIntent,
    Refund as ProviderRefund,
    StripeCancelPaymentIntentRequest,
)
from app.commons.timing import track_func
from app.commons.types import CountryCode, Currency
from app.commons.utils.legacy_utils import (
    get_country_code_by_id,
    get_country_id_by_code,
)
from app.commons.utils.validation import count_present, not_none
from app.payin.core import feature_flags
from app.payin.core.cart_payment.cart_payment_client import CartPaymentInterface
from app.payin.core.cart_payment.legacy_cart_payment_client import (
    LegacyPaymentInterface,
)
from app.payin.core.cart_payment.model import (
    CartPayment,
    CartPaymentList,
    CorrelationIds,
    LegacyPayment,
    LegacyStripeCharge,
    PaymentIntent,
    PaymentMethodToken,
    PgpPaymentIntent,
    PgpRefund,
    Refund,
    SplitPayment,
    LegacyConsumerCharge,
)
from app.payin.core.cart_payment.types import (
    IdempotencyKeyAction,
    IntentStatus,
    LegacyConsumerChargeId,
    RefundReason,
)
from app.payin.core.exceptions import (
    CartPaymentCreateError,
    CartPaymentReadError,
    CartPaymentUpdateError,
    PayinErrorCode,
    PaymentIntentConcurrentAccessError,
    PaymentIntentCouldNotBeUpdatedError,
    PaymentIntentNotInRequiresCaptureState,
    PaymentIntentRefundError,
    PaymentMethodReadError,
    ProviderPaymentIntentUnexpectedStatusError,
)
from app.payin.core.payer.model import Payer, RawPayer
from app.payin.core.payer.payer_client import PayerClient
from app.payin.core.payment_method.model import RawPaymentMethod
from app.payin.core.payment_method.processor import PaymentMethodProcessor
from app.payin.core.payment_method.types import CartPaymentSortKey, PgpPaymentInfo
from app.payin.core.types import PayerReferenceIdType, PaymentMethodIdType


@tracing.track_breadcrumb(processor_name="cart_payment_processor", only_trackable=True)
class CartPaymentProcessor:
    def __init__(
        self,
        log: BoundLogger = Depends(get_logger_from_req),
        cart_payment_interface: CartPaymentInterface = Depends(CartPaymentInterface),
        legacy_payment_interface: LegacyPaymentInterface = Depends(
            LegacyPaymentInterface
        ),
        payer_client: PayerClient = Depends(PayerClient),
        payment_method_processor: PaymentMethodProcessor = Depends(
            PaymentMethodProcessor
        ),
    ):
        self.log = log
        self.cart_payment_interface = cart_payment_interface
        self.legacy_payment_interface = legacy_payment_interface
        self.payer_client = payer_client
        self.payment_method_processor = payment_method_processor

    async def _update_state_after_cancel_with_provider(
        self,
        payment_intent: PaymentIntent,
        pgp_payment_intent: PgpPaymentIntent,
        provider_payment_intent: ProviderPaymentIntent,
    ) -> Tuple[PaymentIntent, PgpPaymentIntent, LegacyStripeCharge]:
        legacy_stripe_charge = await self.legacy_payment_interface.update_charge_after_payment_cancelled(
            provider_payment_intent
        )
        payment_intent, pgp_payment_intent = await self.cart_payment_interface.update_payment_after_cancel_with_provider(
            payment_intent=payment_intent,
            pgp_payment_intent=pgp_payment_intent,
            provider_payment_intent=provider_payment_intent,
        )
        return payment_intent, pgp_payment_intent, legacy_stripe_charge

    async def _update_state_after_provider_error(
        self,
        creation_exception: CartPaymentCreateError,
        payment_intent: PaymentIntent,
        pgp_payment_intent: PgpPaymentIntent,
        legacy_stripe_charge: LegacyStripeCharge,
    ) -> Tuple[PaymentIntent, PgpPaymentIntent, LegacyStripeCharge]:
        # Legacy system: update stripe_charge to failed
        stripe_charge = await self.legacy_payment_interface.mark_charge_as_failed(
            stripe_charge=legacy_stripe_charge, creation_exception=creation_exception
        )

        updated_payment_intent, updated_pgp_payment_intent = await self.cart_payment_interface.mark_payment_as_failed(
            payment_intent=payment_intent, pgp_payment_intent=pgp_payment_intent
        )
        return updated_payment_intent, updated_pgp_payment_intent, stripe_charge

    async def _update_state_after_submit_to_provider(
        self,
        payment_intent: PaymentIntent,
        pgp_payment_intent: PgpPaymentIntent,
        provider_payment_intent: ProviderPaymentIntent,
        cart_payment: CartPayment,
        correlation_ids: CorrelationIds,
        legacy_payment: LegacyPayment,
        legacy_stripe_charge: LegacyStripeCharge,
    ) -> Tuple[PaymentIntent, PgpPaymentIntent, LegacyStripeCharge]:
        # Update state of payment in our system now that payment exists in provider
        updated_payment_intent, updated_pgp_payment_intent = await self.cart_payment_interface.update_payment_after_submission_to_provider(
            payment_intent=payment_intent,
            pgp_payment_intent=pgp_payment_intent,
            provider_payment_intent=provider_payment_intent,
        )
        # Also update state in our legacy system: ConsumerCharge/StripeCharge still used there until migration to new service
        # is entirely complete.  If the stripe_charge record exists it is updated with details of the payment provider's intent.
        # If it does not exist it is created
        updated_stripe_charge = await self.legacy_payment_interface.update_state_after_provider_submission(
            legacy_stripe_charge=legacy_stripe_charge,
            idempotency_key=payment_intent.idempotency_key,
            provider_payment_intent=provider_payment_intent,
        )

        return (
            updated_payment_intent,
            updated_pgp_payment_intent,
            updated_stripe_charge,
        )

    async def _update_state_after_refund_with_provider(
        self,
        payment_intent: PaymentIntent,
        pgp_payment_intent: PgpPaymentIntent,
        refund: Refund,
        pgp_refund: PgpRefund,
        provider_refund: ProviderRefund,
        refund_amount: int,
    ) -> Tuple[PaymentIntent, PgpPaymentIntent]:
        updated_payment_intent = await self.cart_payment_interface.update_payment_after_refund_with_provider(
            payment_intent=payment_intent,
            pgp_payment_intent=await self.cart_payment_interface.get_cart_payment_submission_pgp_intent(
                payment_intent
            ),
            refund=refund,
            pgp_refund=pgp_refund,
            provider_refund=provider_refund,
            refund_amount=refund_amount,
        )

        await self.legacy_payment_interface.update_charge_after_payment_refunded(
            provider_refund=provider_refund
        )
        return updated_payment_intent, pgp_payment_intent

    async def _cancel_payment_intent(
        self, cart_payment: CartPayment, payment_intent: PaymentIntent
    ) -> Tuple[PaymentIntent, PgpPaymentIntent]:
        # For the specified intent, either (a) cancel with provider if not captured, or (b) refund full amount if previously captured.
        # If intent was already refunded, it will not be re-processed (please see cart_payment_interface.can_payment_intent_be_refunded).

        self.log.info(
            "[_cancel_payment_intent]",
            cart_payment_id=cart_payment.id,
            payment_intent_id=payment_intent.id,
            delay_capture=cart_payment.delay_capture,
            payment_intent_status=payment_intent.status,
        )

        can_intent_be_cancelled = self.cart_payment_interface.can_payment_intent_be_cancelled(
            payment_intent
        )
        can_intent_be_refunded = self.cart_payment_interface.can_payment_intent_be_refunded(
            payment_intent
        )
        pgp_payment_intent = await self.cart_payment_interface.get_cart_payment_submission_pgp_intent(
            payment_intent
        )

        if not can_intent_be_cancelled and not can_intent_be_refunded:
            # If not able to cancel or refund, no action is needed (for example, intent is in failed state or already fully refunded).
            # This includes immediate capture intents where amount was already brought down to 0.
            self.log.info(
                "[_cancel_payment_intent] Skipping intent, not in state that allows for cancel or refund",
                payment_intent_id=payment_intent.id,
                payment_intent_status=payment_intent.status,
                amount=payment_intent.amount,
            )
            return payment_intent, pgp_payment_intent

        if can_intent_be_cancelled:
            # Intent not yet captured: it can be cancelled.
            # Cancel with provider
            provider_payment_intent = await self.cart_payment_interface.cancel_provider_payment_charge(
                payment_intent,
                pgp_payment_intent,
                StripeCancelPaymentIntentRequest.CancellationReason.ABANDONED,
            )

            # Update state in our system after operation with provider
            updated_payment_intent, updated_pgp_payment_intent, _ = await self._update_state_after_cancel_with_provider(
                payment_intent=payment_intent,
                pgp_payment_intent=pgp_payment_intent,
                provider_payment_intent=provider_payment_intent,
            )
        elif can_intent_be_refunded:
            # The intent cannot be cancelled because its state is beyond capture.  Instead we must refund
            # Insert new refund, adjustment history
            reason = RefundReason.REQUESTED_BY_CUSTOMER
            refund, pgp_refund = await self.cart_payment_interface.create_new_refund(
                refund_amount=payment_intent.amount,
                cart_payment=cart_payment,
                payment_intent=payment_intent,
                idempotency_key=self.cart_payment_interface.get_idempotency_key_for_provider_call(
                    payment_intent.idempotency_key, IdempotencyKeyAction.REFUND
                ),
                reason=reason,
            )

            provider_refund = await self.cart_payment_interface.refund_provider_payment(
                refund=refund,
                payment_intent=payment_intent,
                pgp_payment_intent=pgp_payment_intent,
                refund_amount=payment_intent.amount,
            )

            # Update state
            updated_payment_intent, updated_pgp_payment_intent = await self._update_state_after_refund_with_provider(
                payment_intent=payment_intent,
                pgp_payment_intent=pgp_payment_intent,
                provider_refund=provider_refund,
                pgp_refund=pgp_refund,
                refund=refund,
                refund_amount=payment_intent.amount,
            )

        return updated_payment_intent, updated_pgp_payment_intent

    async def _update_payment_with_higher_amount(
        self,
        cart_payment: CartPayment,
        legacy_payment: LegacyPayment,
        existing_payment_intents: List[PaymentIntent],
        idempotency_key: str,
        payer_country: CountryCode,
        amount: int,
        description: Optional[str],
        split_payment: Optional[SplitPayment],
    ) -> Tuple[PaymentIntent, PgpPaymentIntent]:

        self.log.info(
            "[_update_payment_with_higher_amount]",
            cart_payment_id=cart_payment.id,
            delay_capture=cart_payment.delay_capture,
            amount=amount,
            idempotency_key=idempotency_key,
        )

        existing_payment_intent = self.cart_payment_interface.filter_payment_intents_by_idempotency_key(
            existing_payment_intents, idempotency_key
        )

        if cart_payment.payer_id:
            raw_payer: RawPayer = await self.cart_payment_interface.payer_client.get_raw_payer(
                mixed_payer_id=cart_payment.payer_id,
                payer_reference_id_type=PayerReferenceIdType.PAYER_ID,
            )

            raw_payment_method: RawPaymentMethod = await self.cart_payment_interface.payment_method_client.get_raw_payment_method_without_payer_auth(
                payment_method_id=not_none(
                    existing_payment_intents[0].payment_method_id
                ),
                payment_method_id_type=PaymentMethodIdType.PAYMENT_METHOD_ID,
            )

            try:
                pgp_payment_method, legacy_payment = await self.cart_payment_interface.get_pgp_payment_info_v1(
                    raw_payer=raw_payer,
                    raw_payment_method=raw_payment_method,
                    legacy_country_id=get_country_id_by_code(
                        existing_payment_intents[0].country
                    ),
                )
            except PaymentMethodReadError as e:
                if e.error_code == PayinErrorCode.PAYMENT_METHOD_GET_NOT_FOUND:
                    raise CartPaymentUpdateError(
                        error_code=PayinErrorCode.CART_PAYMENT_PAYMENT_METHOD_NOT_FOUND
                    ) from e
                raise
        else:  # legacy case
            pgp_payment_method = await self.cart_payment_interface.get_pgp_payment_info_v0(
                legacy_payment=legacy_payment
            )

        # The client description of the cart payment is the new value if provided in the update request, or else we
        # fall back to the current value.
        intent_description = (
            description if description else cart_payment.client_description
        )

        if existing_payment_intent:
            pgp_payment_intent = await self.cart_payment_interface.get_cart_payment_submission_pgp_intent(
                existing_payment_intent
            )

            # Client cart payment adjustment attempt received before.  If adjustment was entirely handled before, we can immediate return.
            if self.cart_payment_interface.is_payment_intent_submitted(
                existing_payment_intent
            ):
                self.log.info(
                    "[_update_payment_with_higher_amount] Duplicate amount increase request for idempotency_key",
                    idempotency_key=idempotency_key,
                    cart_payment_id=cart_payment.id,
                    payment_intent_id=existing_payment_intent.id,
                    payment_intent_status=existing_payment_intent.status,
                    payment_intent_capture_method=existing_payment_intent.capture_method,
                    pgp_payment_intent_id=pgp_payment_intent.id,
                )
                pgp_payment_intent = await self.cart_payment_interface.get_cart_payment_submission_pgp_intent(
                    existing_payment_intent
                )
                return existing_payment_intent, pgp_payment_intent

            # We have record of the payment but it did not make it to provider or previously failed.  Pick up where we left off by trying to
            # submit to provider and update state accordingly.
            payment_intent = existing_payment_intent
            pgp_payment_intent = await self.cart_payment_interface.get_cart_payment_submission_pgp_intent(
                payment_intent
            )
            _, legacy_stripe_charge = await self.legacy_payment_interface.find_existing_payment_charge(
                charge_id=payment_intent.legacy_consumer_charge_id,
                idempotency_key=idempotency_key,
            )
            if not legacy_stripe_charge:
                self.log.error(
                    "[_update_payment_with_higher_amount] Cannot find legacy charge for cart payment adjustment",
                    dd_charge_id=payment_intent.legacy_consumer_charge_id,
                    idempotency_key=idempotency_key,
                    cart_payment_id=cart_payment.id,
                    payment_intent_id=payment_intent.id,
                    pgp_payment_intent_id=pgp_payment_intent.id,
                )
                raise CartPaymentUpdateError(
                    error_code=PayinErrorCode.CART_PAYMENT_DATA_INVALID
                )

            self.log.info(
                "[_update_payment_with_higher_amount] Process existing intents for amount increase request",
                idempotency_key=idempotency_key,
                cart_payment_id=cart_payment.id,
                payment_intent_id=existing_payment_intent.id,
                payment_intent_status=existing_payment_intent.status,
                payment_intent_capture_method=existing_payment_intent.capture_method,
                pgp_payment_intent_id=pgp_payment_intent.id,
            )
        else:
            # First attempt at cart payment adjustment for this idempotency key.
            payment_intent, pgp_payment_intent = await self.cart_payment_interface.increase_payment_amount(
                cart_payment=cart_payment,
                existing_payment_intents=existing_payment_intents,
                amount=amount,
                split_payment=split_payment,
                idempotency_key=idempotency_key,
            )
            legacy_stripe_charge = await self.legacy_payment_interface.update_existing_payment_charge(
                charge_id=payment_intent.legacy_consumer_charge_id,
                amount=amount,
                currency=Currency(payment_intent.currency),
                idempotency_key=idempotency_key,
                description=intent_description,
                legacy_payment=legacy_payment,
            )

        # It may be possible that amount is higher yet still below original_amount of payment intent.  This may happen if: payment created
        # with amount A, then reduced down to B, and then raised up to C, where B < C < A.  In this case we can update the existing intent
        # rather than creating a new one, though that may make things a little bit harder to track and does not actually save calls out to
        # the provider.  To keep implementation as simple as possible we simply create a new intent in this case.

        # Call to provider to create payment on their side, and update state in our system based on the result
        try:
            provider_payment_intent = await self.cart_payment_interface.submit_payment_to_provider(
                payer_country=payer_country,
                payment_intent=payment_intent,
                pgp_payment_intent=pgp_payment_intent,
                pgp_payment_info=pgp_payment_method,
                provider_description=intent_description,
            )
        except CartPaymentCreateError as e:
            await self._update_state_after_provider_error(
                creation_exception=e,
                payment_intent=payment_intent,
                pgp_payment_intent=pgp_payment_intent,
                legacy_stripe_charge=legacy_stripe_charge,
            )
            raise

        # Update state of payment in our system now that payment exists in provider.
        # Update legacy values in main db
        await self.legacy_payment_interface.update_state_after_provider_submission(
            provider_payment_intent=provider_payment_intent,
            idempotency_key=idempotency_key,
            legacy_stripe_charge=legacy_stripe_charge,
        )
        # Update payment_intent and pgp_payment_intent pair in payment db
        payment_intent, pgp_payment_intent = await self.cart_payment_interface.update_state_after_provider_submission(
            payment_intent=payment_intent,
            pgp_payment_intent=pgp_payment_intent,
            provider_payment_intent=provider_payment_intent,
        )

        # Cancel old intents
        intent_operations = []
        for intent in existing_payment_intents:
            intent_operations.append(
                self._cancel_payment_intent(
                    cart_payment=cart_payment, payment_intent=intent
                )
            )
        if len(intent_operations) > 0:
            await gather(*intent_operations)

        return payment_intent, pgp_payment_intent

    async def _update_payment_with_lower_amount(
        self,
        cart_payment: CartPayment,
        existing_payment_intents: List[PaymentIntent],
        new_amount: int,
        idempotency_key: str,
    ) -> Tuple[PaymentIntent, PgpPaymentIntent]:
        # TODO: refactor the logic - there's no combination of capturable and refundable payment intents.
        # We can simplify the logic below streamline the handling.
        capturable_intents = self.cart_payment_interface.get_capturable_payment_intents(
            existing_payment_intents
        )
        refundable_intents = self.cart_payment_interface.get_refundable_payment_intents(
            existing_payment_intents
        )

        self.log.info(
            "[_update_payment_with_lower_amount]",
            cart_payment_id=cart_payment.id,
            delay_capture=cart_payment.delay_capture,
            payment_intents_capturable=bool(capturable_intents),
            payment_intents_refundable=bool(refundable_intents),
            amount=new_amount,
            idempotency_key=idempotency_key,
        )

        if not capturable_intents and not refundable_intents:
            self.log.warn(
                "[_update_payment_with_lower_amount] no payment_intent for adjustment with lower amount.",
                payment_intents=existing_payment_intents,
            )
            raise PaymentIntentRefundError(
                error_code=PayinErrorCode.PAYMENT_INTENT_ADJUST_REFUND_ERROR
            )

        if capturable_intents:
            capturable_intent = self.cart_payment_interface.get_most_recent_intent(
                capturable_intents
            )
            capturable_pgp_payment_intent = await self.cart_payment_interface.get_cart_payment_submission_pgp_intent(
                capturable_intent
            )

            # Check if we have seen this before.  If we have an adjustment_history record, then the transaction that updates
            # amount and also creates this record completed successfully, so we immediately return.
            adjustment_history = await self.cart_payment_interface.get_payment_intent_adjustment(
                idempotency_key=idempotency_key
            )
            if adjustment_history:
                if not self.cart_payment_interface.is_adjustment_for_payment_intents(
                    adjustment_history=adjustment_history,
                    intent_list=[capturable_intent],
                ):
                    self.log.warning(
                        "[_update_payment_with_lower_amount] idempotency_key for another cart_payment used",
                        idempotency_key=idempotency_key,
                        payment_intent_id=capturable_intent.cart_payment_id,
                        history_payment_intent_id=adjustment_history.payment_intent_id,
                    )
                    raise CartPaymentUpdateError(
                        error_code=PayinErrorCode.CART_PAYMENT_IDEMPOTENCY_KEY_ERROR
                    )
                self.log.info(
                    "[_update_payment_with_lower_amount] Duplicate adjustment for idempotency_key",
                    idempotency_key=idempotency_key,
                    payment_intent_id=capturable_intent.id,
                    pgp_payment_intent_id=capturable_pgp_payment_intent.id,
                )
                return capturable_intent, capturable_pgp_payment_intent

            # New adjustment attempt: Update the properties of existing models to reflect changed amount.  Provider call not
            # necessary as delayed capture will take the right amount at capture time.
            if not capturable_pgp_payment_intent.charge_resource_id:
                self.log.error(
                    "[_update_payment_with_lower_amount] no charge resource id for pgp_payment_intent.",
                    payment_intent_id=capturable_intent.id,
                    pgp_payment_intent_id=capturable_pgp_payment_intent.id,
                )
                raise PaymentIntentRefundError(
                    error_code=PayinErrorCode.PAYMENT_INTENT_ADJUST_REFUND_ERROR
                )
            amount_refunded = capturable_intent.amount - new_amount
            await self.legacy_payment_interface.lower_amount_for_uncaptured_payment(
                stripe_id=capturable_pgp_payment_intent.charge_resource_id,
                amount_refunded=amount_refunded,
            )
            payment_intent = await self.cart_payment_interface.lower_amount_for_uncaptured_payment(
                cart_payment=cart_payment,
                payment_intent=capturable_intent,
                amount=new_amount,
                idempotency_key=idempotency_key,
            )
            pgp_payment_intent = capturable_pgp_payment_intent
        elif refundable_intents:
            refundable_intent = self.cart_payment_interface.get_most_recent_intent(
                refundable_intents
            )
            refundable_pgp_payment_intent = await self.cart_payment_interface.get_cart_payment_submission_pgp_intent(
                refundable_intent
            )

            # Interface contracts restrict new_amount to be > 0, and this method is called when new amount is lower than previous.
            # Amount to refund is difference between current and new target value.
            refund_amount = refundable_intent.amount - new_amount
            reason = RefundReason.REQUESTED_BY_CUSTOMER

            # If refund for this idempotency key exists, return
            existing_refund, existing_pgp_refund = await self.cart_payment_interface.find_existing_refund(
                idempotency_key
            )
            if existing_refund and existing_pgp_refund:
                if self.cart_payment_interface.is_refund_ended(existing_refund):
                    # Refund already handled.
                    self.log.info(
                        "[_update_payment_with_lower_amount] Refund already completed",
                        refund_id=existing_refund.id,
                        pgp_refund_id=existing_pgp_refund.id,
                    )
                    return refundable_intent, refundable_pgp_payment_intent

                self.log.info(
                    "[_update_payment_with_lower_amount] Processing existing refund",
                    refund_id=existing_refund.id,
                    pgp_refund_id=existing_pgp_refund.id,
                )
                refund = existing_refund
                pgp_refund = existing_pgp_refund
            else:
                # Insert new refund, adjustment history
                refund, pgp_refund = await self.cart_payment_interface.create_new_refund(
                    refund_amount=refund_amount,
                    cart_payment=cart_payment,
                    payment_intent=refundable_intent,
                    idempotency_key=idempotency_key,
                    reason=reason,
                )

            provider_refund = await self.cart_payment_interface.refund_provider_payment(
                refund=refund,
                payment_intent=refundable_intent,
                pgp_payment_intent=refundable_pgp_payment_intent,
                refund_amount=refund_amount,
            )

            # Update state - handles both maindb and payment db state
            payment_intent, pgp_payment_intent = await self._update_state_after_refund_with_provider(
                payment_intent=refundable_intent,
                pgp_payment_intent=refundable_pgp_payment_intent,
                refund=refund,
                pgp_refund=pgp_refund,
                provider_refund=provider_refund,
                refund_amount=refund_amount,
            )

        return payment_intent, pgp_payment_intent

    @track_func
    @tracing.trackable
    def get_legacy_client_description(
        self, request_client_description: Optional[str]
    ) -> Optional[str]:
        if not request_client_description:
            return None

        return request_client_description[:1000]

    async def _get_payment_intent_if_completed(
        self, idempotency_key: str, existing_payment_intents: List[PaymentIntent]
    ) -> Optional[PaymentIntent]:
        """
        Determine if an idempotency key was used previous for a request related to the specified payment intents.
        Return the payment_intent if the key was successfully used before, otherwise return None.

        Raise error in these cases, since in these scenarios it is not possible or allowed for the caller to make use of the idempotency_key:
            - If idempotency key was used for other payment intents.

        Arguments:
            idempotency_key {str} -- The idempotency key to examine usage of.
            existing_payment_intent {PaymenIntent} -- A list of payment intents for a cart payment.
        """
        existing_payment_intent = self.cart_payment_interface.filter_payment_intents_by_idempotency_key(
            existing_payment_intents, idempotency_key
        )
        if existing_payment_intent:
            if self.cart_payment_interface.is_payment_intent_failed(
                payment_intent=existing_payment_intent
            ):
                # If there was an intent with the same idempotency key and it failed, return an error.
                # TODO support returning previous result based on idempotency key reuse.
                self.log.warning(
                    "[_is_idempotency_key_used_for_intents] Reuse of idempotency key for failed payment intent",
                    idempotency_key=idempotency_key,
                )
                raise CartPaymentUpdateError(
                    error_code=PayinErrorCode.PAYMENT_INTENT_CREATE_FAILED_ERROR
                )

            self.log.info(
                "[_is_idempotency_key_used_for_intents] Reuse of idempotency key for previous payment intent",
                idempotency_key=idempotency_key,
                payment_intent_id=existing_payment_intent.id,
            )
            return existing_payment_intent

        # No payment intent with idempotency key.  Next check adjustment history, which may hold key from previous amount reduction.
        adjustment_history = await self.cart_payment_interface.get_payment_intent_adjustment(
            idempotency_key=idempotency_key
        )
        if adjustment_history:
            adjustment_intent = self.cart_payment_interface.match_payment_intent_for_adjustment(
                adjustment_history=adjustment_history,
                intent_list=existing_payment_intents,
            )
            if not adjustment_intent:
                self.log.error(
                    "[_is_idempotency_key_used_for_intents] Reuse of idempotency key for used by another payment intent",
                    idempotency_key=idempotency_key,
                    payment_intent_id=adjustment_history.payment_intent_id,
                    adjustment_history_id=adjustment_history.id,
                )
                raise CartPaymentUpdateError(
                    error_code=PayinErrorCode.CART_PAYMENT_IDEMPOTENCY_KEY_ERROR
                )
            return adjustment_intent

        # No payment intent or adjustment history with this idempotency key.  Last possibility is in the refunds model.
        refund, _ = await self.cart_payment_interface.find_existing_refund(
            idempotency_key=idempotency_key
        )
        if refund:
            refund_intent = self.cart_payment_interface.match_payment_intent_for_refund(
                refund=refund, intent_list=existing_payment_intents
            )
            if not refund_intent:
                self.log.error(
                    "[_is_idempotency_key_used_for_intents] Reuse of idempotency key for used by another payment intent",
                    idempotency_key=idempotency_key,
                    payment_intent_id=refund.payment_intent_id,
                    refund_id=refund.id,
                )
                raise CartPaymentUpdateError(
                    error_code=PayinErrorCode.CART_PAYMENT_IDEMPOTENCY_KEY_ERROR
                )
            return refund_intent

        # No trace of this idempotency key being used before, so there is no previous operation that completed.
        return None

    @track_func
    @tracing.trackable
    async def update_payment_for_legacy_charge(
        self,
        idempotency_key: str,
        dd_charge_id: int,
        amount: int,
        client_description: Optional[str],
        dd_additional_payment_info: Optional[Dict[str, Any]],
        split_payment: Optional[SplitPayment],
    ) -> CartPayment:
        """Update an existing payment associated with a legacy consumer charge.

        Arguments:
            idempotency_key {str} -- Client specified value for ensuring idempotency.
            dd_charge_id {int} -- ID of the legacy consumer charge associated with the cart payment to adjust.
            payer_id {str} -- ID of the payer who owns the specified cart payment.
            amount {int} -- Delta amount to add to the cart payment amount.  May be negative to reduce amount.
            client_description {Optional[str]} -- New client description to use for cart payment.
            dd_additional_payment_info: {Optional[Dict[str, Any]]} -- Optional legacy payment additional_payment_info
                                        to use for legacy charge writes.
            split_payment: {Optional[SplitPayment]} -- Optional new split payment to use for payment.

        Raises:
            CartPaymentReadError: If there is no cart payment associated with the provided dd_charge_id.
            PaymentIntentConcurrentAccessError: If another request or process has modified the associated intent state.

        Returns:
            CartPayment -- The updated cart payment representation.
        """
        self.log.info(
            "[update_payment_for_legacy_charge] updating cart_payment",
            idempotency_key=idempotency_key,
            dd_charge_id=dd_charge_id,
            amount=amount,
        )
        cart_payment_id = await self.legacy_payment_interface.get_associated_cart_payment_id(
            dd_charge_id
        )
        if not cart_payment_id:
            # Return error if cart payment not found.  This will happen for calls to this API for charges made
            # prior to use of the new service: there exists consumer_charge/stripe_charge, but no new models in the
            # payment system.  In this case, within DSJ at the call site, we fall back to the old behavior rather than
            # relying on the new service.
            self.log.info(
                "[update_payment_for_legacy_charge] Did not find cart payment for consumer charge",
                dd_charge_id=dd_charge_id,
            )
            raise CartPaymentReadError(
                error_code=PayinErrorCode.CART_PAYMENT_NOT_FOUND_FOR_CHARGE_ID
            )

        cart_payment, legacy_payment = await self.cart_payment_interface.get_cart_payment(
            cart_payment_id
        )

        if not cart_payment or not legacy_payment:
            raise CartPaymentReadError(error_code=PayinErrorCode.CART_PAYMENT_NOT_FOUND)

        legacy_consumer_charge, _ = await self.legacy_payment_interface.find_existing_payment_charge(
            charge_id=dd_charge_id, idempotency_key=idempotency_key
        )
        if not legacy_consumer_charge:
            self.log.error(
                "[update_payment_for_legacy_charge] Failed to find legacy consumer charge for charge id",
                dd_charge_id=dd_charge_id,
            )
            raise CartPaymentReadError(error_code=PayinErrorCode.CART_PAYMENT_NOT_FOUND)

        payer_country_code = get_country_code_by_id(legacy_consumer_charge.country_id)

        # Clients may update additional_payment_info.
        if dd_additional_payment_info:
            legacy_payment.dd_additional_payment_info = dd_additional_payment_info

        # Amount is a delta.
        new_amount = cart_payment.amount + amount
        if new_amount < 0:
            self.log.warning(
                "[update_payment_for_legacy_charge] Invalid amount provided",
                amount=new_amount,
                idempotency_key=idempotency_key,
                dd_charge_id=dd_charge_id,
            )
            raise CartPaymentUpdateError(
                error_code=PayinErrorCode.CART_PAYMENT_AMOUNT_INVALID
            )

        # Client description cannot exceed 1000: truncated if needed
        payment_client_description = self.get_legacy_client_description(
            client_description
        )

        # If clients resubmit a previously used idempotency key for v0 interfaces, return immediatey based on
        # the previous result.  This takes care of cases where we see legacy interfaces in DSJ called multiple
        # times in succession (duplicate requests).  Handling is specific to v0 path, as we expect actual handling
        # of idempotency key with v1 clients: here we can immediately return, but with v1 we want to support retrying
        # previously attempted but incomplete/failed attempt.
        payment_intents = await self.cart_payment_interface.get_cart_payment_intents(
            cart_payment
        )
        completed_intent = await self._get_payment_intent_if_completed(
            idempotency_key=idempotency_key, existing_payment_intents=payment_intents
        )
        if completed_intent:
            # Form response for cart payment without taking any action: This idempotency key was already re-used, so we return immediately.
            pgp_payment_intent = await self.cart_payment_interface.get_cart_payment_submission_pgp_intent(
                payment_intent=completed_intent
            )
            return self.cart_payment_interface.populate_cart_payment_for_response(
                cart_payment=cart_payment,
                payment_intent=completed_intent,
                pgp_payment_intent=pgp_payment_intent,
                last_active_sibling_payment_intent=None,
            )

        updated_cart_payment = await self._lock_and_update_payment(
            idempotency_key=idempotency_key,
            cart_payment=cart_payment,
            legacy_payment=legacy_payment,
            existing_payment_intents=payment_intents,
            payer_id=None,
            payer_country=payer_country_code,
            amount=new_amount,
            client_description=payment_client_description,
            split_payment=split_payment,
        )
        self.log.info(
            "[update_payment_for_legacy_charge] updated cart_payment",
            idempotency_key=idempotency_key,
            dd_charge_id=dd_charge_id,
            amount=amount,
        )
        return updated_cart_payment

    @track_func
    @tracing.trackable
    async def update_payment(
        self,
        idempotency_key: str,
        cart_payment_id: uuid.UUID,
        amount: int,
        client_description: Optional[str],
        split_payment: Optional[SplitPayment],
        payer_id: Optional[uuid.UUID] = None,
    ) -> CartPayment:
        self.log.info(
            "[update_payment] updating cart_payment",
            idempotency_key=idempotency_key,
            cart_payment_id=cart_payment_id,
            amount=amount,
            payer_id=payer_id,
        )
        cart_payment, legacy_payment = await self.cart_payment_interface.get_cart_payment(
            cart_payment_id
        )

        if not cart_payment or not legacy_payment:
            raise CartPaymentReadError(error_code=PayinErrorCode.CART_PAYMENT_NOT_FOUND)

        if not cart_payment.payer_id:
            self.log.error(
                "[update_payment] Cart payment missing payer id",
                cart_payment_id=cart_payment.id,
            )
            raise CartPaymentReadError(
                error_code=PayinErrorCode.CART_PAYMENT_OWNER_MISMATCH
            )

        payer = await self.get_payer_by_id(cart_payment.payer_id)
        payment_intents = await self.cart_payment_interface.get_cart_payment_intents(
            cart_payment
        )

        updated_cart_payment = await self._lock_and_update_payment(
            idempotency_key=idempotency_key,
            cart_payment=cart_payment,
            legacy_payment=legacy_payment,
            existing_payment_intents=payment_intents,
            payer_id=payer_id,
            payer_country=CountryCode(payer.country),
            amount=amount,
            client_description=client_description,
            split_payment=split_payment,
        )
        self.log.info(
            "[update_payment] updated cart_payment",
            idempotency_key=idempotency_key,
            cart_payment_id=cart_payment_id,
            amount=amount,
            payer_id=payer_id,
        )

        return updated_cart_payment

    async def _lock_and_update_payment(
        self,
        idempotency_key: str,
        cart_payment: CartPayment,
        legacy_payment: LegacyPayment,
        existing_payment_intents: List[PaymentIntent],
        payer_id: Optional[uuid.UUID],
        payer_country: CountryCode,
        amount: int,
        client_description: Optional[str],
        split_payment: Optional[SplitPayment],
    ) -> CartPayment:
        if not feature_flags.cart_payment_update_locking_enabled():
            # TODO: Remove this once new locking behavior is proven in production use.
            self.log.info(
                "[_lock_and_update_payment] Cart payment locking for update is disabled.  Updating without lock."
            )
            return await self._update_payment(
                idempotency_key=idempotency_key,
                cart_payment=cart_payment,
                legacy_payment=legacy_payment,
                existing_payment_intents=existing_payment_intents,
                payer_id=payer_id,
                payer_country=payer_country,
                amount=amount,
                client_description=client_description,
                split_payment=split_payment,
            )

        # If locking is enabled, a redis based lock is used to ensure we only have one attempt to update a cart payment at a time.
        lock_key = f"{cart_payment.id}-update"
        try:
            self.log.info(
                "[_lock_and_update_payment] Acquiring lock for cart payment update.",
                lock_key=lock_key,
            )
            async with PaymentLock(
                lock_key, self.cart_payment_interface.app_context.redis_lock_manager
            ):
                return await self._update_payment(
                    idempotency_key=idempotency_key,
                    cart_payment=cart_payment,
                    legacy_payment=legacy_payment,
                    existing_payment_intents=existing_payment_intents,
                    payer_id=payer_id,
                    payer_country=payer_country,
                    amount=amount,
                    client_description=client_description,
                    split_payment=split_payment,
                )
        except PaymentLockAcquireError:
            # Another process currently holds the lock for updating this cart payment, so return an error to the caller.
            self.log.exception(
                "Failed to get lock for cart payment update", lock_key=lock_key
            )
            raise CartPaymentReadError(
                error_code=PayinErrorCode.CART_PAYMENT_CONCURRENT_ACCESS_ERROR
            )

    async def _update_payment(
        self,
        idempotency_key: str,
        cart_payment: CartPayment,
        legacy_payment: LegacyPayment,
        existing_payment_intents: List[PaymentIntent],
        payer_id: Optional[uuid.UUID],
        payer_country: CountryCode,
        amount: int,
        client_description: Optional[str],
        split_payment: Optional[SplitPayment],
    ) -> CartPayment:
        """Update an existing payment.

        Arguments:
            idempotency_key {str} -- Client specified value for ensuring idempotency.
            cart_payment {CartPayment} -- Existing cart payment.
            legacy_payment {LegacyPayment} -- Legacy payment associated with cart payment.
            existing_payment_intents: List[PaymentIntent] -- Existing payment intents for the cart payment.
            payer_id {str} -- ID of the payer who owns the specified cart payment.
            payer_country {CountryCode} -- The CountryCode of the payer whose payment is being modified.
            amount {int} -- New amount to use for cart payment.
            client_description {Optional[str]} -- New client description to use for cart payment.
            split_payment {Optional[SplitPayment]} -- New split payment to use, if needed.

        Raises:
            CartPaymentReadError: Raised when there is an error retrieving the specified cart payment.

        Returns:
            CartPayment -- An updated CartPayment instance, reflecting changes requested by the client.
        """
        # Ensure the caller can access the cart payment being modified

        self.log.info(
            "[_update_payment] Updating cart_payment",
            cart_payment_id=cart_payment.id,
            delay_capture=cart_payment.delay_capture,
        )

        if not self.cart_payment_interface.is_accessible(
            cart_payment=cart_payment, request_payer_id=payer_id, credential_owner=""
        ):
            raise CartPaymentReadError(
                error_code=PayinErrorCode.CART_PAYMENT_OWNER_MISMATCH
            )

        # TODO PAYIN-32 Move idempotency key based checks up to here (from inside _update_payment_with_higher_amount,
        # _update_payment_with_lower_amount functions).

        if self.cart_payment_interface.is_amount_adjusted_higher(cart_payment, amount):
            payment_intent, pgp_payment_intent = await self._update_payment_with_higher_amount(
                cart_payment=cart_payment,
                legacy_payment=legacy_payment,
                existing_payment_intents=existing_payment_intents,
                idempotency_key=idempotency_key,
                payer_country=payer_country,
                amount=amount,
                description=client_description,
                split_payment=split_payment,
            )
        elif self.cart_payment_interface.is_amount_adjusted_lower(cart_payment, amount):
            payment_intent, pgp_payment_intent = await self._update_payment_with_lower_amount(
                cart_payment, existing_payment_intents, amount, idempotency_key
            )

            # If new target amount is 0, we treat the operation as equivalent to cancelling the intent.
            if self.cart_payment_interface.is_amount_adjustment_cancelling_payment(
                cart_payment, amount
            ):
                self.log.info(
                    "Cancelling cart payment due to zero amount update",
                    cart_payment_id=cart_payment.id,
                    payment_intent_id=payment_intent.id,
                )
                payment_intent, pgp_payment_intent = await self._cancel_payment_intent(
                    cart_payment=cart_payment, payment_intent=payment_intent
                )
        else:
            # Amount is the same: properties of cart payment other than the amount may be changing
            payment_intent = self.cart_payment_interface.get_most_recent_intent(
                existing_payment_intents
            )
            pgp_payment_intent = await self.cart_payment_interface.get_cart_payment_submission_pgp_intent(
                payment_intent
            )

        updated_cart_payment = await self.cart_payment_interface.update_cart_payment_attributes(
            cart_payment=cart_payment,
            idempotency_key=idempotency_key,
            amount=amount,
            client_description=client_description,
            payment_intent=payment_intent,
            pgp_payment_intent=pgp_payment_intent,
        )
        last_active_payment_intent = self.cart_payment_interface.get_most_recent_active_intent(
            intent_list=existing_payment_intents
        )
        return self.cart_payment_interface.populate_cart_payment_for_response(
            cart_payment=updated_cart_payment,
            payment_intent=payment_intent,
            pgp_payment_intent=pgp_payment_intent,
            last_active_sibling_payment_intent=last_active_payment_intent,
        )

    @track_func
    @tracing.trackable
    async def cancel_payment_for_legacy_charge(self, dd_charge_id: int) -> CartPayment:
        """Cancel cart payment associated with legacy consumer charge ID.

        Arguments:
            dd_charge_id {int} -- The consumer charge ID whose associated cart payment will be cancelled.

        Returns:
            None
        """
        self.log.info(
            "[cancel_payment_for_legacy_charge] cancelling payment",
            dd_charge_id=dd_charge_id,
        )
        cart_payment_id = await self.legacy_payment_interface.get_associated_cart_payment_id(
            dd_charge_id
        )
        if not cart_payment_id:
            raise CartPaymentReadError(error_code=PayinErrorCode.CART_PAYMENT_NOT_FOUND)

        cancelled_payment = await self.cancel_payment(cart_payment_id)
        self.log.info(
            "[cancel_payment_for_legacy_charge] cancelling payment",
            dd_charge_id=dd_charge_id,
        )
        return cancelled_payment

    @track_func
    @tracing.trackable
    async def cancel_payment(self, cart_payment_id: uuid.UUID) -> CartPayment:
        """Cancel a previously submitted cart payment.  Results in full refund if charge was made.

        Arguments:
            cart_payment_id {uuid.UUID} -- ID of the cart payment to cance.

        Returns:
            None
        """
        self.log.info(
            "[cancel_payment] Canceling cart_payment", cart_payment_id=cart_payment_id
        )
        cart_payment, legacy_payment = await self.cart_payment_interface.get_cart_payment(
            cart_payment_id
        )
        if not cart_payment or not legacy_payment:
            raise CartPaymentReadError(error_code=PayinErrorCode.CART_PAYMENT_NOT_FOUND)

        # Ensure the caller can access the cart payment being modified
        if not self.cart_payment_interface.is_accessible(
            cart_payment=cart_payment, request_payer_id=None, credential_owner=""
        ):
            raise CartPaymentReadError(
                error_code=PayinErrorCode.CART_PAYMENT_OWNER_MISMATCH
            )

        # Cancel old intents
        payment_intents = await self.cart_payment_interface.get_cart_payment_intents(
            cart_payment
        )
        intent_operations = []
        for intent in payment_intents:
            intent_operations.append(
                self._cancel_payment_intent(
                    cart_payment=cart_payment, payment_intent=intent
                )
            )
        if len(intent_operations) > 0:
            await gather(*intent_operations)

        cancelled_cart_payment = await self.cart_payment_interface.update_cart_payment_post_cancellation(
            id=cart_payment_id
        )
        self.log.info(
            "[cancel_payment] Cancelled cart_payment", cart_payment_id=cart_payment_id
        )
        return cancelled_cart_payment

    @track_func
    @tracing.trackable
    async def capture_payment(self, payment_intent: PaymentIntent) -> None:
        """Capture a payment intent.
        Arguments:
            payment_intent {PaymentIntent} -- The PaymentIntent to capture.

        Raises:
            e: Raises an exception if database operations fail.

        Returns:
            None

        PaymentIntent state transition:
        1. Successful capture:
            [requires_capture] -> [capturing] -> [succeeded]
        2. PaymentIntent status out of sync with provider:
            [requires_capture] -> [capturing] -> [succeeded] / [cancelled]
        3. Failing capture:
            [requires_capture] -> [capturing]

        Capturing state:
        - [capturing] state is used as an optimistic lock when attempting to capture a payment intent.
        while capturing fails due to any reason, the intent's state will pause at this stage.
        - "app.payin.jobs.payin_jobs.ResolveCapturingPaymentIntents" will pickup payment intents stuck this stage
        and reset their states to [requires_capture] or [capture_failed] depending on how low the intent
        has been in [capturing] state
        """
        self.log.info(
            "[capture_payment] Capturing payment_intent",
            payment_intent=payment_intent.summary,
        )

        try:
            await self._capture_payment(payment_intent)
            create_to_capture_time: timedelta = datetime.now(
                payment_intent.created_at.tzinfo
            ) - payment_intent.created_at
            self.log.info(
                "[capture_payment] Captured payment_intent",
                payment_intent_id=payment_intent.id,
                amount=payment_intent.amount,
                create_to_capture_time_sec=create_to_capture_time.seconds,
            )
            doorstats_global.incr("capture-payment.success")
            doorstats_global.gauge(
                "capture-payment.capture-delay-sec", create_to_capture_time.seconds
            )
        except PaymentIntentConcurrentAccessError:
            doorstats_global.incr("capture-payment.invalid.concurrent-access")
            self.log.info(
                "[capture_payment] Unable to capture payment intent due to concurrent access",
                payment_intent_id=payment_intent.id,
            )
            raise
        except Exception:
            doorstats_global.incr("capture-payment.failed")
            self.log.exception(
                "[capture_payment] Attempted to capture payment intent but failed",
                payment_intent=payment_intent.summary,
            )
            raise

    async def _capture_payment(self, payment_intent: PaymentIntent) -> None:
        if not self.cart_payment_interface.does_intent_require_capture(payment_intent):
            self.log.warning(
                "[capture_payment] Payment intent not eligible for capturing",
                payment_intent_id=payment_intent.id,
                payment_intent_status=payment_intent.status,
            )
            raise PaymentIntentNotInRequiresCaptureState()

        # Update intent status; acts as optimistic lock
        try:
            payment_intent = await self.cart_payment_interface.acquire_for_capture(
                payment_intent
            )
        except PaymentIntentCouldNotBeUpdatedError:
            raise PaymentIntentConcurrentAccessError()

        # Find the PgpPaymentIntent to capture
        pgp_payment_intent = await self.cart_payment_interface.get_cart_payment_submission_pgp_intent(
            payment_intent
        )

        # Call to provider to capture, with idempotency key
        try:
            provider_payment_intent = await self.cart_payment_interface.submit_capture_to_provider(
                payment_intent, pgp_payment_intent
            )
        except ProviderPaymentIntentUnexpectedStatusError as e:
            self.log.error(
                "[capture_payment] failed to capture payment intent due to unexpected provider payment intent status",
                provider_payment_intent_status=e.provider_payment_intent_status,
                payment_service_pgp_payment_intent_status=pgp_payment_intent.status,
                payment_service_payment_intent_status=payment_intent.status,
                payment_intent_id=payment_intent.id,
                pgp_payment_intent_id=pgp_payment_intent.id,
            )
            if e.provider_payment_intent_status in ["succeeded", "canceled"]:
                self.log.info(
                    "[capture_payment] sync from provider payment intent status for unexpected status",
                    new_status=e.provider_payment_intent_status,
                    stale_pgp_payment_intent_status=pgp_payment_intent.status,
                    stale_payment_intent_status=payment_intent.status,
                    payment_intent_id=payment_intent.id,
                    pgp_payment_intent_id=pgp_payment_intent.id,
                )
                await self.cart_payment_interface.update_payment_and_pgp_intent_status_only(
                    new_status=IntentStatus.from_str(e.provider_payment_intent_status),
                    payment_intent=payment_intent,
                    pgp_payment_intent=pgp_payment_intent,
                )
                return
            else:
                raise

        # Update state in our system

        # This seems redundant since StripeCharge.status will always be "succeeded" after a successful authorization
        # And when capture succeeded to here, this is essentially a noop update.
        await self.legacy_payment_interface.update_charge_after_payment_captured(
            provider_payment_intent
        )

        await self.cart_payment_interface.update_payment_after_capture_with_provider(
            payment_intent=payment_intent,
            pgp_payment_intent=pgp_payment_intent,
            provider_payment_intent=provider_payment_intent,
        )

    @track_func
    @tracing.trackable
    async def create_cart_payment_v0(
        self,
        request_cart_payment: CartPayment,
        legacy_payment: LegacyPayment,
        idempotency_key: str,
        payment_country: CountryCode,
        payer_country: CountryCode,
        currency: Currency,
    ) -> Tuple[CartPayment, LegacyConsumerChargeId]:
        self.log.info(
            "[legacy_create_payment] creating cart_payment",
            idempotency_key=idempotency_key,
            dd_consumer_id=legacy_payment.dd_consumer_id,
            amount=request_cart_payment.amount,
            correlation_ids=request_cart_payment.correlation_ids,
            payer_country=payer_country,
            payment_country=payment_country,
            stripe_customer_id=legacy_payment.stripe_customer_id,
        )
        pgp_payment_method = await self.cart_payment_interface.get_pgp_payment_info_v0(
            legacy_payment=legacy_payment
        )

        # Client description cannot exceed 1000: truncated if needed
        request_cart_payment.client_description = self.get_legacy_client_description(
            request_cart_payment.client_description
        )

        cart_payment, legacy_consumer_charge_id = await self._create_cart_payment(
            request_cart_payment=request_cart_payment,
            pgp_payment_info=pgp_payment_method,
            legacy_payment=legacy_payment,
            idempotency_key=idempotency_key,
            payment_country=payment_country,
            payer_country=payer_country,
            currency=currency,
        )

        self.log.info(
            "[legacy_create_payment] created cart_payment",
            idempotency_key=idempotency_key,
            dd_consumer_id=legacy_payment.dd_consumer_id,
            amount=request_cart_payment.amount,
            correlation_ids=request_cart_payment.correlation_ids,
            cart_payment_id=cart_payment.id if cart_payment else None,
            legacy_consumer_charge_id=legacy_consumer_charge_id
            if legacy_consumer_charge_id
            else None,
            payer_country=payer_country,
            payment_country=payment_country,
            stripe_customer_id=legacy_payment.stripe_customer_id,
        )

        return cart_payment, legacy_consumer_charge_id

    @track_func
    @tracing.trackable
    async def create_cart_payment_v1(
        # TODO PAYIN-292 refactor and consolidate cart payment internal interfaces.
        self,
        request_cart_payment: CartPayment,
        idempotency_key: str,
        payment_country: CountryCode,
        currency: Currency,
        payment_method_token: Optional[PaymentMethodToken] = None,
    ) -> CartPayment:
        self.log.info(
            "[create_payment] creating cart_payment",
            idempotency_key=idempotency_key,
            payer_id=request_cart_payment.payer_id,
            amount=request_cart_payment.amount,
            payment_method_id=request_cart_payment.payment_method_id,
            delay_capture=request_cart_payment.delay_capture,
            correlation_ids=request_cart_payment.correlation_ids,
        )
        if (
            count_present(
                request_cart_payment.payment_method_id,
                request_cart_payment.dd_stripe_card_id,
                payment_method_token,
            )
            != 1
        ):
            raise ValueError(
                f"Expected exactly 1 of payment_method_id and dd_stripe_card_id being present by found "
                f"payment_method_id={request_cart_payment.payment_method_id}, "
                f"dd_stripe_card_id={request_cart_payment.dd_stripe_card_id}"
                f"payment_method_token={payment_method_token}"
            )

        if (
            count_present(
                request_cart_payment.payer_id,
                request_cart_payment.payer_correlation_ids,
            )
            != 1
        ):
            raise ValueError(
                f"Expected exactly 1 of payer_id and payer_correlation_ids being present by found "
                f"payer_id={request_cart_payment.payer_id}, "
                f"payer_correlation_ids={request_cart_payment.payer_correlation_ids}"
            )

        # TODO: PAYIN-292 consolidate the process of fetching all required metadata to create a cart payment
        payer_reference_id: Union[uuid.UUID, str]
        payer_reference_id_type: PayerReferenceIdType

        if request_cart_payment.payer_id:
            payer_reference_id = request_cart_payment.payer_id
            payer_reference_id_type = PayerReferenceIdType.PAYER_ID
        else:  # request_cart_payment.payer_correlation_ids
            payer_reference_id = not_none(
                request_cart_payment.payer_correlation_ids
            ).payer_reference_id
            payer_reference_id_type = not_none(
                request_cart_payment.payer_correlation_ids
            ).payer_reference_id_type

        raw_payer: RawPayer = await self.cart_payment_interface.payer_client.get_raw_payer(
            mixed_payer_id=payer_reference_id,
            payer_reference_id_type=payer_reference_id_type,
        )
        if not request_cart_payment.payer_id:
            request_cart_payment.payer_id = raw_payer.payer_id

        raw_payment_method: RawPaymentMethod

        try:
            if request_cart_payment.payment_method_id:
                raw_payment_method = await self.cart_payment_interface.payment_method_client.get_raw_payment_method_without_payer_auth(
                    payment_method_id=request_cart_payment.payment_method_id,
                    payment_method_id_type=PaymentMethodIdType.PAYMENT_METHOD_ID,
                )
            elif request_cart_payment.dd_stripe_card_id:
                raw_payment_method = await self.cart_payment_interface.payment_method_client.get_raw_payment_method_without_payer_auth(
                    payment_method_id=str(
                        not_none(request_cart_payment.dd_stripe_card_id)
                    ),
                    payment_method_id_type=PaymentMethodIdType.DD_STRIPE_CARD_ID,
                )
            else:  # payment_method_token
                raw_payment_method, _, _ = await self.payment_method_processor.create_payment_method(
                    pgp_code=not_none(payment_method_token).payment_gateway,
                    token=not_none(payment_method_token).token,
                    set_default=False,
                    is_scanned=False,
                    is_active=True,
                    payer_lookup_id=payer_reference_id,
                    payer_lookup_id_type=payer_reference_id_type,
                )
                request_cart_payment.payment_method_id = (
                    raw_payment_method.payment_method_id
                )
        except PaymentMethodReadError as e:
            if e.error_code == PayinErrorCode.PAYMENT_METHOD_GET_NOT_FOUND:
                raise CartPaymentCreateError(
                    error_code=PayinErrorCode.CART_PAYMENT_PAYMENT_METHOD_NOT_FOUND
                ) from e
            raise

        pgp_payment_info, legacy_payment = await self.cart_payment_interface.get_pgp_payment_info_v1(
            legacy_country_id=get_country_id_by_code(payment_country),
            raw_payer=raw_payer,
            raw_payment_method=raw_payment_method,
        )

        payer = raw_payer.to_payer()

        cart_payment, _ = await self._create_cart_payment(
            request_cart_payment=request_cart_payment,
            pgp_payment_info=pgp_payment_info,
            legacy_payment=legacy_payment,
            idempotency_key=idempotency_key,
            payment_country=payment_country,
            payer_country=CountryCode(payer.country),
            currency=currency,
        )

        self.log.info(
            "[create_payment] created cart_payment",
            cart_payment_id=cart_payment.id,
            idempotency_key=idempotency_key,
            payer_id=request_cart_payment.payer_id,
            amount=request_cart_payment.amount,
            payment_method_id=request_cart_payment.payment_method_id,
            delay_capture=request_cart_payment.delay_capture,
            correlation_ids=request_cart_payment.correlation_ids,
        )
        return cart_payment

    async def _create_cart_payment(
        self,
        request_cart_payment: CartPayment,
        pgp_payment_info: PgpPaymentInfo,
        legacy_payment: LegacyPayment,
        idempotency_key: str,
        payment_country: CountryCode,
        payer_country: CountryCode,
        currency: Currency,
    ) -> Tuple[CartPayment, LegacyConsumerChargeId]:
        """Submit a cart payment creation request.

        Arguments:
            request_cart_payment {CartPayment} -- CartPayment model containing request parameters provided by client.
            pgp_payment_info {PgpPaymentInfo} -- Payment method to use for cart payment creation.
            idempotency_key {str} -- Client specified value for ensuring idempotency.
            payment_country {CountryCode} -- ISO country code for payment
            payer_country {CountryCode} -- ISO country code for the payer who the payment is being created for.
            currency {Currency} -- Currency for cart payment request.

        Returns:
            CartPayment -- A CartPayment model for the created payment.
        """
        self.log.info(
            "[_create_payment] Creating cart payment with consumer charge",
            stripe_customer_id=legacy_payment.stripe_customer_id,
            payer_country=payer_country,
            payment_country=payment_country,
            idempotency_key=idempotency_key,
            stripe_card_id=legacy_payment.stripe_card_id,
        )
        # Check for resubmission by client
        existing_cart_payment, existing_legacy_payment, existing_payment_intent = await self.cart_payment_interface.find_existing_payment(
            request_cart_payment.payer_id, idempotency_key
        )
        if (
            existing_cart_payment
            and existing_legacy_payment
            and existing_payment_intent
        ):
            # Client is attempting to create payment that we already have record of
            # If payment was entirely submitted before, we can immediately return.
            if self.cart_payment_interface.is_payment_intent_submitted(
                existing_payment_intent
            ):
                self.log.info(
                    "[_create_payment] Duplicate cart payment creation request",
                    idempotency_key=existing_payment_intent.idempotency_key,
                    cart_payment_id=existing_cart_payment.id,
                    payment_intent_id=existing_payment_intent.id,
                    payer_country=payer_country,
                    payment_country=payment_country,
                    stripe_customer_id=legacy_payment.stripe_customer_id,
                )
                pgp_payment_intent = await self.cart_payment_interface.get_cart_payment_submission_pgp_intent(
                    existing_payment_intent
                )
                return (
                    self.cart_payment_interface.populate_cart_payment_for_response(
                        cart_payment=existing_cart_payment,
                        payment_intent=existing_payment_intent,
                        pgp_payment_intent=pgp_payment_intent,
                        last_active_sibling_payment_intent=None,
                    ),
                    existing_payment_intent.legacy_consumer_charge_id,
                )

            # We have record of the payment but it did not make it to provider or previously failed.  Pick up where we left off by trying to
            # submit to provider and update state accordingly.
            cart_payment = existing_cart_payment
            payment_intent = existing_payment_intent
            pgp_payment_intent = await self.cart_payment_interface.get_cart_payment_submission_pgp_intent(
                payment_intent
            )
            legacy_consumer_charge, legacy_stripe_charge = await self.legacy_payment_interface.find_existing_payment_charge(
                charge_id=payment_intent.legacy_consumer_charge_id,
                idempotency_key=idempotency_key,
            )
            if not legacy_consumer_charge or not legacy_stripe_charge:
                self.log.error(
                    "[_create_payment] Missing legacy charge information for cart payment",
                    idempotency_key=existing_payment_intent.idempotency_key,
                    cart_payment_id=cart_payment.id,
                    payment_intent_id=payment_intent.id,
                    payer_country=payer_country,
                    payment_country=payment_country,
                    stripe_customer_id=legacy_payment.stripe_customer_id,
                    stripe_card_id=legacy_payment.stripe_card_id,
                )
                raise CartPaymentCreateError(
                    error_code=PayinErrorCode.CART_PAYMENT_DATA_INVALID,
                    provider_charge_id=None,
                    provider_error_code=None,
                    provider_decline_code=None,
                    has_provider_error_details=False,
                )

            self.log.info(
                "[_create_payment] Processing existing intents for cart payment creation request",
                idempotency_key=existing_payment_intent.idempotency_key,
                cart_payment_id=cart_payment.id,
                payment_intent_id=payment_intent.id,
                payer_country=payer_country,
                payment_country=payment_country,
                stripe_customer_id=legacy_payment.stripe_customer_id,
                stripe_card_id=legacy_payment.stripe_card_id,
            )
        else:
            legacy_consumer_charge, legacy_stripe_charge = await self.legacy_payment_interface.create_new_payment_charges(
                request_cart_payment=request_cart_payment,
                legacy_payment=legacy_payment,
                correlation_ids=request_cart_payment.correlation_ids,
                idempotency_key=idempotency_key,
                country=payment_country,
                currency=currency,
            )
            legacy_consumer_charge_id = legacy_consumer_charge.id
            provider_metadata = None
            if (
                legacy_payment
                and legacy_payment.dd_additional_payment_info
                and "metadata" in legacy_payment.dd_additional_payment_info
            ):
                provider_metadata = legacy_payment.dd_additional_payment_info[
                    "metadata"
                ]

            # New payment: Create records in our system for the new cart payment
            cart_payment, payment_intent, pgp_payment_intent = await self.cart_payment_interface.create_new_payment(
                request_cart_payment=request_cart_payment,
                legacy_payment=legacy_payment,
                legacy_consumer_charge_id=legacy_consumer_charge_id,
                provider_payment_method_id=pgp_payment_info.pgp_payment_method_resource_id,
                provider_customer_resource_id=pgp_payment_info.pgp_payer_resource_id,
                provider_metadata=provider_metadata,
                idempotency_key=idempotency_key,
                country=payment_country,
                currency=currency,
            )

        # Call to provider to create payment on their side, and update state in our system based on the result
        try:
            provider_payment_intent = await self.cart_payment_interface.submit_payment_to_provider(
                payer_country=payer_country,
                payment_intent=payment_intent,
                pgp_payment_intent=pgp_payment_intent,
                pgp_payment_info=pgp_payment_info,
                provider_description=request_cart_payment.client_description,
            )
            self.log.info(
                "[_create_payment] Stripe Payment Intent created successfully",
                provider_payment_intent_id=provider_payment_intent.id,
                payment_intent_id=payment_intent.id,
                payer_country=payer_country,
                payment_country=payment_country,
                stripe_customer_id=legacy_payment.stripe_customer_id,
            )
        except CartPaymentCreateError as e:
            # If any error occurs reaching out to the provider, cart_payment_interface.submit_payment_to_provider throws an exception
            # of type CartPaymentCreateError.  In this case, update state in our system accordingly.
            await self._update_state_after_provider_error(
                creation_exception=e,
                payment_intent=payment_intent,
                pgp_payment_intent=pgp_payment_intent,
                legacy_stripe_charge=legacy_stripe_charge,
            )
            raise
        except Exception as e:
            # cart_payment_interface.submit_payment_to_provider should throw a CartPaymentCreateError, but to be sure we mark intent as failed,
            # we handle generic exceptions as well.
            creation_exception = CartPaymentCreateError(
                error_code=PayinErrorCode.PAYMENT_INTENT_CREATE_ERROR,
                provider_charge_id=None,
                provider_error_code=None,
                provider_decline_code=None,
                has_provider_error_details=False,
            )
            await self._update_state_after_provider_error(
                creation_exception=creation_exception,
                payment_intent=payment_intent,
                pgp_payment_intent=pgp_payment_intent,
                legacy_stripe_charge=legacy_stripe_charge,
            )
            raise creation_exception from e

        # Update state of payment in our system now that payment exists in provider.

        # update legacy values in db
        legacy_stripe_charge = await self.legacy_payment_interface.update_state_after_provider_submission(
            legacy_stripe_charge=legacy_stripe_charge,
            idempotency_key=idempotency_key,
            provider_payment_intent=provider_payment_intent,
        )
        # update payment_intent and pgp_payment_intent pair in db
        payment_intent, pgp_payment_intent = await self.cart_payment_interface.update_state_after_provider_submission(
            payment_intent=payment_intent,
            pgp_payment_intent=pgp_payment_intent,
            provider_payment_intent=provider_payment_intent,
        )

        self.cart_payment_interface.populate_cart_payment_for_response(
            cart_payment=cart_payment,
            payment_intent=payment_intent,
            pgp_payment_intent=pgp_payment_intent,
            last_active_sibling_payment_intent=None,
        )

        cart_payment.payer_correlation_ids = request_cart_payment.payer_correlation_ids
        cart_payment.dd_stripe_card_id = request_cart_payment.dd_stripe_card_id

        return cart_payment, legacy_consumer_charge.id

    @track_func
    @tracing.trackable
    async def get_payer_by_id(self, payer_id: uuid.UUID) -> Payer:
        return (
            await self.cart_payment_interface.payer_client.get_raw_payer(
                mixed_payer_id=payer_id,
                payer_reference_id_type=PayerReferenceIdType.PAYER_ID,
            )
        ).to_payer()

    async def list_legacy_cart_payment(
        self,
        dd_consumer_id: int,
        sort_by: CartPaymentSortKey,
        created_at_gte: datetime = None,
        created_at_lte: datetime = None,
    ) -> CartPaymentList:
        cart_payments: List[
            CartPayment
        ] = await self.legacy_payment_interface.list_cart_payments_by_dd_consumer_id(
            dd_consumer_id=dd_consumer_id
        )
        return self.build_cart_payment_list(
            cart_payments=cart_payments,
            sort_by=sort_by,
            created_at_gte=created_at_gte,
            created_at_lte=created_at_lte,
        )

    async def list_cart_payments(
        self,
        sort_by: CartPaymentSortKey,
        payer_id: Optional[str] = None,
        payer_reference_id: Optional[str] = None,
        payer_reference_id_type: Optional[PayerReferenceIdType] = None,
        reference_id: Optional[str] = None,
        reference_type: Optional[str] = None,
        created_at_gte: datetime = None,
        created_at_lte: datetime = None,
    ) -> CartPaymentList:
        use_payer_id: bool = bool(payer_id)
        use_payer_reference_id: bool = bool(
            payer_reference_id and payer_reference_id_type
        )
        use_reference_id: bool = bool(reference_id and reference_type)
        cart_payments: List[CartPayment]
        if use_reference_id:
            cart_payments = await self.cart_payment_interface.list_cart_payments_by_reference_id(
                reference_id=not_none(reference_id),
                reference_type=not_none(reference_type),
            )
        elif use_payer_reference_id:
            cart_payments = await self.cart_payment_interface.list_cart_payments_by_payer_reference_id(
                payer_reference_id=not_none(payer_reference_id),
                payer_reference_id_type=not_none(payer_reference_id_type),
            )
        elif use_payer_id:
            cart_payments = await self.cart_payment_interface.list_cart_payments_by_payer_id(
                payer_id=not_none(payer_id)
            )
        else:
            self.log.exception(
                "[list_cart_payments] Invalid input for list cart payments."
            )
            raise CartPaymentReadError(
                error_code=PayinErrorCode.CART_PAYMENT_DATA_INVALID
            )
        return self.build_cart_payment_list(
            cart_payments=cart_payments,
            created_at_gte=created_at_gte,
            created_at_lte=created_at_lte,
            sort_by=sort_by,
        )

    def build_cart_payment_list(
        self,
        cart_payments: List[CartPayment],
        sort_by: CartPaymentSortKey,
        created_at_gte: datetime = None,
        created_at_lte: datetime = None,
    ) -> CartPaymentList:
        if created_at_gte:
            cart_payments = list(
                filter(
                    lambda cart_payment: (
                        not cart_payment.created_at
                        or (
                            cart_payment.created_at
                            and created_at_gte
                            and cart_payment.created_at >= created_at_gte
                        )
                    ),
                    cart_payments,
                )
            )
        if created_at_lte:
            cart_payments = list(
                filter(
                    lambda cart_payment: (
                        not cart_payment.created_at
                        or (
                            cart_payment.created_at
                            and created_at_lte
                            and cart_payment.created_at <= created_at_lte
                        )
                    ),
                    cart_payments,
                )
            )
        cart_payments = sorted(
            cart_payments,
            key=lambda cart_payment: cart_payment.created_at,
            reverse=False,
        )
        return CartPaymentList(
            count=len(cart_payments), has_more=False, data=cart_payments
        )

    async def legacy_get_cart_payment(self, dd_charge_id: int) -> CartPayment:
        cart_payment_id = await self.legacy_payment_interface.get_associated_cart_payment_id(
            charge_id=dd_charge_id
        )
        if not cart_payment_id:
            self.log.exception(
                "[legacy_get_cart_payment] Cart payment not found for dd_charge_id",
                dd_charge_id=dd_charge_id,
            )
            raise CartPaymentReadError(error_code=PayinErrorCode.CART_PAYMENT_NOT_FOUND)
        return await self.get_cart_payment(cart_payment_id=cart_payment_id)

    async def get_cart_payment(self, cart_payment_id: uuid.UUID) -> CartPayment:
        cart_payment, _ = await self.cart_payment_interface.get_cart_payment(
            cart_payment_id=cart_payment_id
        )
        if not cart_payment:
            raise CartPaymentReadError(error_code=PayinErrorCode.CART_PAYMENT_NOT_FOUND)
        return cart_payment

    async def upsert_cart_payment(
        self,
        reference_id: str,
        reference_type: str,
        idempotency_key: str,
        request_cart_payment: CartPayment,
        currency: Currency,
        payment_country: CountryCode,
        dd_stripe_card_id: Optional[int] = None,
    ) -> Tuple[CartPayment, bool]:
        cart_payment: Optional[
            CartPayment
        ] = await self.cart_payment_interface.get_cart_payment_by_reference_id(
            reference_id=reference_id, reference_type=reference_type
        )
        if cart_payment:
            self.log.info(
                "[upsert_cart_payment] Existing cart payment found. Updating the cart payment",
                cart_payment_id=cart_payment.id,
                reference_id=reference_id,
                reference_type=reference_type,
                amount=request_cart_payment.amount,
            )
            updated_cart_payment = await self.update_payment(
                idempotency_key=idempotency_key,
                cart_payment_id=cart_payment.id,
                amount=request_cart_payment.amount + cart_payment.amount,
                client_description=request_cart_payment.client_description,
                split_payment=request_cart_payment.split_payment,
            )
            return updated_cart_payment, True
        else:
            legacy_charge: Optional[
                LegacyConsumerCharge
            ] = await self.cart_payment_interface.get_consumer_charge_by_reference_id(
                reference_id=reference_id, reference_type=reference_type
            )
            if legacy_charge:
                self.log.error(
                    "[upsert_cart_payment] Existing charge found for no corresponding cart payment",
                    reference_id=reference_id,
                    reference_type=reference_type,
                )
                raise CartPaymentCreateError(
                    error_code=PayinErrorCode.CART_PAYMENT_NOT_FOUND_FOR_CHARGE_ID
                )
            self.log.info(
                "[upsert_cart_payment] No cart payment found. Creating a new cart payment"
            )
            created_cart_payment = await self.create_cart_payment_v1(
                idempotency_key=idempotency_key,
                payment_country=payment_country,
                currency=currency,
                request_cart_payment=request_cart_payment,
            )
            return created_cart_payment, False
