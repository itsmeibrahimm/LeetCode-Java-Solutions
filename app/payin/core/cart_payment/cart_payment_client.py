import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Coroutine, Dict, List, Optional, Tuple, Union

from fastapi import Depends
from stripe.error import InvalidRequestError, StripeError

from app.commons import tracing
from app.commons.context.app_context import AppContext, get_global_app_context
from app.commons.context.req_context import (
    get_context_from_req,
    get_stripe_async_client_from_req,
    ReqContext,
)
from app.commons.core.errors import DBOperationError
from app.commons.operational_flags import (
    ENABLE_SMALL_AMOUNT_CAPTURE_THEN_REFUND,
    SET_ON_BE_HALF_OF_FOR_FLOW_OF_FUNDS,
)
from app.commons.providers.errors import StripeCommandoError
from app.commons.providers.stripe.commando import COMMANDO_PAYMENT_INTENT
from app.commons.providers.stripe.constants import STRIPE_PLATFORM_ACCOUNT_IDS
from app.commons.providers.stripe.errors import (
    StripeErrorCode,
    StripeErrorParser,
    StripeErrorType,
    StripeInvalidParam,
)
from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.commons.providers.stripe.stripe_models import (
    ClonePaymentMethodRequest,
    ConnectedAccountId,
    CustomerId,
    PaymentIntent as ProviderPaymentIntent,
    PaymentMethodId,
    Refund as ProviderRefund,
    StripeCancelPaymentIntentRequest,
    StripeCapturePaymentIntentRequest,
    StripeCreatePaymentIntentRequest,
    StripeRefundChargeRequest,
    StripeRetrievePaymentIntentRequest,
    TransferData,
)
from app.commons.runtime import runtime
from app.commons.types import CountryCode, PgpCode
from app.commons.utils.validation import not_none
from app.payin.core import feature_flags
from app.payin.core.cart_payment.model import (
    CartPayment,
    LegacyPayment,
    PaymentCharge,
    PaymentIntent,
    PaymentIntentAdjustmentHistory,
    PgpPaymentCharge,
    PgpPaymentIntent,
    PgpRefund,
    Refund,
    SplitPayment,
    LegacyConsumerCharge,
)
from app.payin.core.cart_payment.types import (
    CaptureMethod,
    ChargeStatus,
    IdempotencyKeyAction,
    IntentStatus,
    LegacyConsumerChargeId,
    RefundReason,
    RefundStatus,
)
from app.payin.core.exceptions import (
    CartPaymentCreateError,
    CartPaymentReadError,
    CartPaymentUpdateError,
    InvalidProviderRequestError,
    PayerReadError,
    PayinErrorCode,
    PaymentChargeRefundError,
    PaymentIntentCancelError,
    ProviderError,
    ProviderPaymentIntentUnexpectedStatusError,
)
from app.payin.core.payer.model import RawPayer
from app.payin.core.payer.payer_client import PayerClient
from app.payin.core.payer.types import DeletePayerRedactingText
from app.payin.core.payment_method.model import RawPaymentMethod
from app.payin.core.payment_method.processor import PaymentMethodClient
from app.payin.core.payment_method.types import PgpPaymentInfo
from app.payin.core.types import (
    PayerReferenceIdType,
    PgpPayerResourceId,
    PgpPaymentMethodResourceId,
)
from app.payin.repository.cart_payment_repo import (
    CartPaymentRepository,
    GetCartPaymentsByConsumerIdInput,
    ListCartPaymentsByReferenceId,
    UpdateCartPaymentPostCancellationInput,
    UpdateCartPaymentsRemovePiiSetInput,
    UpdateCartPaymentsRemovePiiWhereInput,
    UpdatePaymentIntentSetInput,
    UpdatePaymentIntentWhereInput,
    UpdatePgpPaymentIntentSetInput,
    UpdatePgpPaymentIntentWhereInput,
    GetCartPaymentsByReferenceId,
    GetConsumerChargeByReferenceId,
)


# TODO PAYIN-36: Rename to CartPaymentClient
@tracing.track_breadcrumb(processor_name="cart_payment_interface", only_trackable=False)
class CartPaymentInterface:
    ENABLE_NEW_CHARGE_TABLES = False
    PAYMENT_INTENT_SMALL_AMOUNT_THRESHOLD = 50

    def __init__(
        self,
        app_context: AppContext = Depends(get_global_app_context),
        req_context: ReqContext = Depends(get_context_from_req),
        payment_repo: CartPaymentRepository = Depends(
            CartPaymentRepository.get_repository
        ),
        payer_client: PayerClient = Depends(PayerClient),
        payment_method_client: PaymentMethodClient = Depends(PaymentMethodClient),
        stripe_async_client: StripeAsyncClient = Depends(
            get_stripe_async_client_from_req
        ),
    ):
        self.app_context = app_context
        self.req_context = req_context
        self.payment_repo = payment_repo
        self.payer_client = payer_client
        self.payment_method_client = payment_method_client
        self.stripe_async_client = stripe_async_client
        self.capture_service = self.app_context.capture_service

    async def update_cart_payments_remove_pii(
        self, consumer_id: int
    ) -> List[CartPayment]:
        try:
            return await self.payment_repo.update_cart_payments_remove_pii(
                update_cart_payments_remove_pii_where_input=UpdateCartPaymentsRemovePiiWhereInput(
                    legacy_consumer_id=consumer_id
                ),
                update_cart_payments_remove_pii_set_input=UpdateCartPaymentsRemovePiiSetInput(
                    client_description=DeletePayerRedactingText.REDACTED
                ),
            )
        except DBOperationError as e:
            self.req_context.log.exception(
                "[update_cart_payments_remove_pii] Error occurred while updating cart payments",
                consumer_id=consumer_id,
            )
            raise CartPaymentUpdateError(
                error_code=PayinErrorCode.CART_PAYMENT_UPDATE_DB_ERROR
            ) from e

    def get_idempotency_key_for_provider_call(
        self, client_key: str, action: IdempotencyKeyAction
    ) -> str:
        # Return a value that is deterministic given the parameters of the function.
        # Client key is what is provided by payment platform API caller.  For a given cart payment, we will need to
        # call provider different times (e.g. auth and then capture at least) and need a unique value each time, given
        # the same client specified idempotency key.  To achieve this we tack on a string describing the action at the
        # end of the client provided key.
        return f"{client_key}-{action.value}"

    def get_most_recent_intent(self, intent_list: List[PaymentIntent]) -> PaymentIntent:
        intent_list.sort(key=lambda x: x.created_at)
        return intent_list[-1]

    def get_most_recent_active_intent(
        self, intent_list: List[PaymentIntent]
    ) -> Optional[PaymentIntent]:
        # Sort with most recent first
        intent_list.sort(key=lambda x: x.created_at, reverse=True)
        for intent in intent_list:
            if self.is_payment_intent_submitted(
                intent
            ) or self.is_payment_intent_pending(intent):
                return intent
        return None

    async def _get_most_recent_pgp_payment_intent(self, payment_intent: PaymentIntent):
        pgp_intents = await self.payment_repo.list_pgp_payment_intents_from_primary(
            payment_intent.id
        )
        pgp_intents.sort(key=lambda x: x.created_at)
        return pgp_intents[-1]

    async def get_cart_payment_submission_pgp_intent(
        self, payment_intent: PaymentIntent
    ) -> PgpPaymentIntent:
        # Get pgp intents for this specific intent
        pgp_intents = await self.payment_repo.list_pgp_payment_intents_from_primary(
            payment_intent.id
        )

        # Since cart_payment/payment_intent/pgp_payment_intent are first created in one transaction,
        # we will have at least one.  Find the first one, since this is an attempt to recreate the
        # cart_payment.
        return pgp_intents[0]

    def _filter_payment_intents_by_state(
        self, intents: List[PaymentIntent], status: IntentStatus
    ) -> List[PaymentIntent]:
        return list(filter(lambda intent: intent.status == status.value, intents))

    def filter_payment_intents_by_idempotency_key(
        self, intents: List[PaymentIntent], idempotency_key: str
    ) -> Optional[PaymentIntent]:
        matched_intents = list(
            filter(lambda intent: intent.idempotency_key == idempotency_key, intents)
        )

        return matched_intents[0] if matched_intents else None

    def get_capturable_payment_intents(self, payment_intents: List[PaymentIntent]):
        return self._filter_payment_intents_by_state(
            payment_intents, IntentStatus.REQUIRES_CAPTURE
        )

    def get_refundable_payment_intents(self, payment_intents: List[PaymentIntent]):
        return self._filter_payment_intents_by_function(
            payment_intents, self.can_payment_intent_be_refunded
        )

    def get_submitted_or_captured_intents(self, payment_intents: List[PaymentIntent]):
        return list(
            filter(
                lambda intent: intent.status
                in [IntentStatus.REQUIRES_CAPTURE, IntentStatus.SUCCEEDED],
                payment_intents,
            )
        )

    def _filter_payment_intents_by_function(
        self,
        payment_intents: List[PaymentIntent],
        filter_function: Callable[[PaymentIntent], bool],
    ) -> List[PaymentIntent]:
        return list(filter(lambda intent: filter_function(intent), payment_intents))

    def is_payment_intent_submitted(self, payment_intent: PaymentIntent) -> bool:
        return payment_intent.status in [
            IntentStatus.REQUIRES_CAPTURE,
            IntentStatus.SUCCEEDED,
        ]

    def is_payment_intent_failed(self, payment_intent: PaymentIntent) -> bool:
        return payment_intent.status == IntentStatus.FAILED

    def is_payment_intent_pending(self, payment_intent: PaymentIntent) -> bool:
        return payment_intent.status == IntentStatus.PENDING

    def can_payment_intent_be_cancelled(self, payment_intent: PaymentIntent) -> bool:
        # Not yet captured.  SCA related states will be added here later.
        return payment_intent.status in [IntentStatus.REQUIRES_CAPTURE]

    def can_payment_intent_be_refunded(self, payment_intent: PaymentIntent) -> bool:
        return (
            payment_intent.status == IntentStatus.SUCCEEDED
            and payment_intent.amount > 0
        )

    def does_intent_require_capture(self, payment_intent: PaymentIntent) -> bool:
        return payment_intent.status == IntentStatus.REQUIRES_CAPTURE

    def _get_intent_status_from_provider_status(
        self, provider_status: str
    ) -> IntentStatus:
        return IntentStatus.from_str(provider_status)

    def _get_refund_status_from_provider_refund(
        self, provider_status: str
    ) -> RefundStatus:
        if provider_status == "pending":
            return RefundStatus.PROCESSING

        return RefundStatus(provider_status)

    def _get_refund_reason_from_provider_refund(
        self, provider_reason: Optional[str]
    ) -> Optional[RefundReason]:
        return RefundReason(provider_reason) if provider_reason else None

    def _get_charge_status_from_intent_status(
        self, intent_status: IntentStatus
    ) -> ChargeStatus:
        # Charge status is a subset of Intent status
        return ChargeStatus(intent_status)

    def is_amount_adjustment_cancelling_payment(
        self, cart_payment: CartPayment, amount: int
    ) -> bool:
        return amount == 0

    def is_amount_adjusted_higher(self, cart_payment: CartPayment, amount: int) -> bool:
        return amount > cart_payment.amount

    def is_amount_adjusted_lower(self, cart_payment: CartPayment, amount: int) -> bool:
        return amount < cart_payment.amount

    def is_refund_ended(self, refund: Refund) -> bool:
        return refund.status in [RefundStatus.SUCCEEDED, RefundStatus.FAILED]

    def _transform_method_for_stripe(self, method_name: str) -> str:
        if method_name == "auto":
            return "automatic"
        return method_name

    def _get_provider_capture_method(
        self, pgp_payment_intent: PgpPaymentIntent
    ) -> StripeCreatePaymentIntentRequest.CaptureMethod:
        target_method = self._transform_method_for_stripe(
            pgp_payment_intent.capture_method
        )
        return StripeCreatePaymentIntentRequest.CaptureMethod(target_method)

    def _get_provider_future_usage(self, payment_intent: PaymentIntent) -> str:
        if payment_intent.capture_method == CaptureMethod.AUTO:
            return StripeCreatePaymentIntentRequest.SetupFutureUsage.ON_SESSION

        return StripeCreatePaymentIntentRequest.SetupFutureUsage.OFF_SESSION

    def _get_provider_refund_from_intent_if_exists(
        self, provider_payment_intent: ProviderPaymentIntent
    ) -> Optional[ProviderRefund]:
        provider_charge = (
            provider_payment_intent.charges.data[0]
            if provider_payment_intent.charges and provider_payment_intent.charges.data
            else None
        )
        if (
            provider_charge
            and provider_charge.refunds
            and provider_charge.refunds.data
            and len(provider_charge.refunds.data) > 0
        ):
            return provider_charge.refunds.data[0]
        else:
            return None

    async def find_existing_payment(
        self, payer_id: Optional[uuid.UUID], idempotency_key: str
    ) -> Union[
        Tuple[CartPayment, LegacyPayment, PaymentIntent], Tuple[None, None, None]
    ]:
        payment_intent = await self.payment_repo.get_payment_intent_by_idempotency_key_from_primary(
            idempotency_key
        )

        if not payment_intent:
            return None, None, None

        cart_payment, legacy_payment = await self.payment_repo.get_cart_payment_by_id_from_primary(
            payment_intent.cart_payment_id
        )

        assert cart_payment
        assert legacy_payment
        return cart_payment, legacy_payment, payment_intent

    async def get_cart_payment(
        self, cart_payment_id: uuid.UUID
    ) -> Tuple[Optional[CartPayment], Optional[LegacyPayment]]:
        return await self.payment_repo.get_cart_payment_by_id_from_primary(
            cart_payment_id
        )

    async def get_cart_payment_intents(self, cart_payment) -> List[PaymentIntent]:
        return await self.payment_repo.get_payment_intents_by_cart_payment_id_from_primary(
            cart_payment.id
        )

    async def get_payment_intent_adjustment(
        self, idempotency_key: str
    ) -> Optional[PaymentIntentAdjustmentHistory]:
        return await self.payment_repo.get_payment_intent_adjustment_history_from_primary(
            idempotency_key=idempotency_key
        )

    async def find_existing_refund(
        self, idempotency_key: str
    ) -> Tuple[Optional[Refund], Optional[PgpRefund]]:
        refund = await self.payment_repo.get_refund_by_idempotency_key_from_primary(
            idempotency_key=idempotency_key
        )
        if not refund:
            return None, None

        pgp_refund = await self.payment_repo.get_pgp_refund_by_refund_id_from_primary(
            refund_id=refund.id
        )
        return refund, pgp_refund

    def match_payment_intent_for_adjustment(
        self,
        *,
        adjustment_history: PaymentIntentAdjustmentHistory,
        intent_list: List[PaymentIntent],
    ) -> Optional[PaymentIntent]:
        matched_intents = filter(
            lambda intent: intent.id == adjustment_history.payment_intent_id,
            intent_list,
        )
        return next(matched_intents, None)

    def is_adjustment_for_payment_intents(
        self,
        adjustment_history: PaymentIntentAdjustmentHistory,
        intent_list: List[PaymentIntent],
    ) -> bool:
        return any(
            [
                payment_intent.id == adjustment_history.payment_intent_id
                for payment_intent in intent_list
            ]
        )

    def match_payment_intent_for_refund(
        self, *, refund: Refund, intent_list: List[PaymentIntent]
    ) -> Optional[PaymentIntent]:
        matched_intents = filter(
            lambda intent: intent.id == refund.payment_intent_id, intent_list
        )
        return next(matched_intents, None)

    def is_accessible(
        self,
        cart_payment: CartPayment,
        request_payer_id: Optional[uuid.UUID],
        credential_owner: str,
    ) -> bool:
        # TODO PAY-3642 verify the caller (as identified by the provided credentials for this request) owns the cart payment.
        # May be skipped if this is handled by upstream services that make use of our payment platform.

        # From credential_owner, get payer_id
        # return cart_payment.payer_id == payer_id and cart_payment.payer_id == request_payer_id
        return True

    async def create_new_payment(
        self,
        request_cart_payment: CartPayment,
        legacy_payment: LegacyPayment,
        legacy_consumer_charge_id: LegacyConsumerChargeId,
        provider_payment_method_id: str,
        provider_customer_resource_id: str,
        provider_metadata: Optional[Dict[str, Any]],
        idempotency_key: str,
        country: CountryCode,
        currency: str,
    ) -> Tuple[CartPayment, PaymentIntent, PgpPaymentIntent]:
        # Create a new cart payment, with associated models
        self.req_context.log.info(
            "[create_new_payment] Creating new payment for payer",
            payer_id=request_cart_payment.payer_id,
            idempotency_key=idempotency_key,
            amount=request_cart_payment.amount,
        )

        # Capture Method
        capture_method = (
            CaptureMethod.MANUAL
            if request_cart_payment.delay_capture
            else CaptureMethod.AUTO
        )

        async with self.payment_repo.payment_database_transaction():
            # Create CartPayment

            cart_payment = await self.payment_repo.insert_cart_payment(
                id=request_cart_payment.id,
                payer_id=request_cart_payment.payer_id,
                client_description=request_cart_payment.client_description,
                reference_id=request_cart_payment.correlation_ids.reference_id,
                reference_type=request_cart_payment.correlation_ids.reference_type,
                amount_original=request_cart_payment.amount,
                amount_total=request_cart_payment.amount,
                delay_capture=request_cart_payment.delay_capture,
                metadata=request_cart_payment.metadata,
                # Legacy fields are associated with the cart_payment instance to support idempotency and
                # adjusting amount without the client having to provide full payment info again.  But these
                # fields are considered deprecated and will be removed once clients upgrade to new payin API.
                legacy_consumer_id=legacy_payment.dd_consumer_id,
                legacy_stripe_card_id=legacy_payment.dd_stripe_card_id,
                legacy_provider_customer_id=legacy_payment.stripe_customer_id,
                legacy_provider_card_id=legacy_payment.stripe_card_id,
            )

            payment_intent, pgp_payment_intent = await self._create_new_intent_pair(
                cart_payment_id=cart_payment.id,
                legacy_consumer_charge_id=legacy_consumer_charge_id,
                idempotency_key=idempotency_key,
                payment_method_id=request_cart_payment.payment_method_id,
                provider_payment_method_id=provider_payment_method_id,
                provider_customer_resource_id=provider_customer_resource_id,
                provider_metadata=provider_metadata,
                amount=request_cart_payment.amount,
                country=country,
                currency=currency,
                split_payment=request_cart_payment.split_payment,
                capture_method=capture_method,
                payer_statement_description=request_cart_payment.payer_statement_description,
            )

        self.req_context.log.debug(
            "[create_new_payment] insert payment_intent objects completed"
        )

        return cart_payment, payment_intent, pgp_payment_intent

    async def _create_new_charge_pair(
        self,
        payment_intent: PaymentIntent,
        pgp_payment_intent: PgpPaymentIntent,
        provider_intent: ProviderPaymentIntent,
        status: ChargeStatus,
    ) -> Tuple[PaymentCharge, PgpPaymentCharge]:

        payment_charge = await self.payment_repo.insert_payment_charge(
            id=uuid.uuid4(),
            payment_intent_id=payment_intent.id,
            pgp_code=PgpCode.STRIPE,
            idempotency_key=str(uuid.uuid4()),  # TODO handle idempotency key
            status=status,
            currency=payment_intent.currency,
            amount=payment_intent.amount,
            amount_refunded=0,
            application_fee_amount=payment_intent.application_fee_amount,
            payout_account_id=pgp_payment_intent.payout_account_id,
        )

        provider_charges = provider_intent.charges
        if len(provider_charges.data) > 1:
            # Upon creation, there is expected to be one provider charge.
            self.req_context.log.warning(
                "[_create_new_charge_pair] Multiple pgp charges at time of creation for intent",
                payment_intent_id=payment_intent.id,
                pgp_payment_intent_id=pgp_payment_intent.id,
            )
        provider_charge = provider_charges.data[0]
        pgp_payment_charge = await self.payment_repo.insert_pgp_payment_charge(
            id=uuid.uuid4(),
            payment_charge_id=payment_charge.id,
            pgp_code=PgpCode.STRIPE,
            idempotency_key=payment_charge.idempotency_key,
            status=status,
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
        cart_payment_id: uuid.UUID,
        legacy_consumer_charge_id: LegacyConsumerChargeId,
        idempotency_key: str,
        payment_method_id: Optional[uuid.UUID],
        provider_payment_method_id: str,
        provider_customer_resource_id: str,
        provider_metadata: Optional[Dict[str, Any]],
        amount: int,
        country: CountryCode,
        currency: str,
        split_payment: Optional[SplitPayment],
        capture_method: str,
        payer_statement_description: Optional[str] = None,
    ) -> Tuple[PaymentIntent, PgpPaymentIntent]:
        # Create PaymentIntent
        payment_intent = await self.payment_repo.insert_payment_intent(
            id=uuid.uuid4(),
            cart_payment_id=cart_payment_id,
            idempotency_key=idempotency_key,
            amount_initiated=amount,
            amount=amount,
            application_fee_amount=split_payment.application_fee_amount
            if split_payment
            else None,
            country=country,
            currency=currency,
            capture_method=capture_method,
            status=IntentStatus.INIT,
            statement_descriptor=payer_statement_description,
            payment_method_id=payment_method_id,
            metadata=provider_metadata,
            legacy_consumer_charge_id=legacy_consumer_charge_id,
            capture_after=None,
        )

        # Create PgpPaymentIntent
        pgp_payment_intent = await self.payment_repo.insert_pgp_payment_intent(
            id=uuid.uuid4(),
            payment_intent_id=payment_intent.id,
            idempotency_key=idempotency_key,
            pgp_code=PgpCode.STRIPE,
            payment_method_resource_id=provider_payment_method_id,
            customer_resource_id=provider_customer_resource_id,
            currency=currency,
            amount=amount,
            application_fee_amount=split_payment.application_fee_amount
            if split_payment
            else None,
            payout_account_id=split_payment.payout_account_id
            if split_payment
            else None,
            capture_method=capture_method,
            status=IntentStatus.INIT,
            statement_descriptor=payer_statement_description,
        )

        return payment_intent, pgp_payment_intent

    async def _clone_payment_method(
        self,
        payment_intent_id: uuid.UUID,
        provider_payment_method_id: PaymentMethodId,
        provider_customer_id: CustomerId,
        source_country: CountryCode,
        destination_country: CountryCode,
    ) -> PaymentMethodId:
        # Clone a payment method for use in another country.  Return the ID of the cloned payment method.
        try:
            cloned_provider_payment_method = await self.stripe_async_client.clone_payment_method(
                request=ClonePaymentMethodRequest(
                    payment_method=provider_payment_method_id,
                    customer=provider_customer_id,
                    stripe_account=STRIPE_PLATFORM_ACCOUNT_IDS[destination_country],
                ),
                country=source_country,
            )
            return PaymentMethodId(cloned_provider_payment_method.id)
        except StripeError as e:
            self.req_context.log.exception(
                "[_clone_payment_method] Could not clone payment method",
                payment_intent_id=payment_intent_id,
                stripe_error_code=e.code,
            )
            raise CartPaymentCreateError(
                error_code=PayinErrorCode.PAYMENT_INTENT_CREATE_CROSS_COUNTRY_PAYMENT_METHOD_ERROR,
                provider_charge_id=None,
                provider_error_code=None,
                provider_decline_code=None,
                has_provider_error_details=False,
            ) from e
        except Exception as e:
            self.req_context.log.exception(
                "[_clone_payment_method] Error invoking provider to clone payment method",
                payment_intent_id=payment_intent_id,
            )
            raise CartPaymentCreateError(
                error_code=PayinErrorCode.PAYMENT_INTENT_CREATE_ERROR,
                provider_charge_id=None,
                provider_error_code=None,
                provider_decline_code=None,
                has_provider_error_details=False,
            ) from e

    async def submit_payment_to_provider(
        self,
        *,
        payer_country: CountryCode,
        payment_intent: PaymentIntent,
        pgp_payment_intent: PgpPaymentIntent,
        pgp_payment_info: PgpPaymentInfo,
        provider_description: Optional[str],
    ) -> ProviderPaymentIntent:
        self.req_context.log.info(
            "[submit_payment_to_provider][start]",
            payment_intent=payment_intent.summary,
            pgp_payment_intent=pgp_payment_intent.summary,
        )

        # If the country for the payment intent does not match the country in which the payer is, then the payment
        # method needs to be converted into a payment method that can be used in the pgp account for that country as
        # payment methods are pgp account-specific
        # TODO(update to use pgp_customer.country when that model exists)
        pgp_payment_method_resource_id: PaymentMethodId = PaymentMethodId(
            pgp_payment_info.pgp_payment_method_resource_id
        )
        pgp_customer_resource_id: Optional[
            PgpPayerResourceId
        ] = pgp_payment_info.pgp_payer_resource_id
        if payment_intent.country != payer_country:
            pgp_payment_method_resource_id = await self._clone_payment_method(
                payment_intent_id=payment_intent.id,
                provider_payment_method_id=pgp_payment_method_resource_id,
                provider_customer_id=CustomerId(pgp_payment_info.pgp_payer_resource_id),
                source_country=payer_country,
                destination_country=payment_intent.country,
            )
            pgp_customer_resource_id = None

        # For retrieval of payment intent as a part of the webhook
        # https://stripe.com/docs/payments/payment-intents/verifying-status#webhooks
        payment_intent_metadata = (
            payment_intent.metadata if payment_intent.metadata else {}
        )
        payment_intent_metadata["payment_intent_id"] = str(payment_intent.id)

        # TODO PAYIN-140: Remove this, which is a workaround until that issue is resolved.
        if pgp_customer_resource_id == "None":
            pgp_customer_resource_id = None

        # Actually create the payment intent
        try:
            intent_request = StripeCreatePaymentIntentRequest(
                amount=pgp_payment_intent.amount,
                currency=pgp_payment_intent.currency,
                capture_method=self._get_provider_capture_method(pgp_payment_intent),
                confirm=True,
                # Set confirmation method to "manual". Do not change this!
                # See link below for more details on what confirmation_method is
                # https://stripe.com/docs/api/payment_intents/create#create_payment_intent-confirmation_method
                confirmation_method="manual",
                setup_future_usage=self._get_provider_future_usage(payment_intent),
                payment_method=pgp_payment_method_resource_id,
                customer=pgp_customer_resource_id,
                description=provider_description,
                statement_descriptor=payment_intent.statement_descriptor,
                metadata=payment_intent_metadata,
            )

            if (
                payment_intent.application_fee_amount
                and pgp_payment_intent.payout_account_id
            ):
                intent_request.application_fee_amount = (
                    payment_intent.application_fee_amount
                )
                intent_request.transfer_data = TransferData(
                    destination=ConnectedAccountId(pgp_payment_intent.payout_account_id)
                )

                if runtime.get_bool(SET_ON_BE_HALF_OF_FOR_FLOW_OF_FUNDS, True):
                    self.req_context.log.info(
                        "[submit_payment_to_provider] set on_behalf_of for flow of funds charge",
                        pgp_intent_id=pgp_payment_intent.id,
                        destination_account_id=pgp_payment_intent.payout_account_id,
                    )
                    intent_request.on_behalf_of = ConnectedAccountId(
                        pgp_payment_intent.payout_account_id
                    )

            self.req_context.log.debug(
                "[submit_payment_to_provider] Calling provider to create payment intent"
            )
            response = await self.stripe_async_client.create_payment_intent(
                country=CountryCode(payment_intent.country),
                request=intent_request,
                idempotency_key=self.get_idempotency_key_for_provider_call(
                    payment_intent.idempotency_key, IdempotencyKeyAction.CREATE
                ),
            )
            return response
        except StripeError as e:
            self.req_context.log.warning(
                "[submit_payment_to_provider] Could not create payment in provider",
                payment_intent_id=payment_intent.id,
                stripe_error_code=e.code,
                exception=str(e),
            )

            parser = StripeErrorParser(e)
            error_code = PayinErrorCode.PAYMENT_INTENT_CREATE_STRIPE_ERROR
            if parser.code == StripeErrorCode.card_declined:
                error_code = PayinErrorCode.PAYMENT_INTENT_CREATE_CARD_DECLINED_ERROR
            elif parser.code == StripeErrorCode.incorrect_number:
                error_code = (
                    PayinErrorCode.PAYMENT_INTENT_CREATE_CARD_INCORRECT_NUMBER_ERROR
                )
            elif parser.code == StripeErrorCode.testmode_charges_only:
                error_code = (
                    PayinErrorCode.PAYMENT_INTENT_CREATE_INVALID_SPLIT_PAYMENT_ACCOUNT
                )
            elif parser.code == StripeErrorCode.expired_card:
                error_code = PayinErrorCode.PAYMENT_INTENT_CREATE_CARD_EXPIRED_ERROR
            elif parser.code == StripeErrorCode.processing_error:
                error_code = PayinErrorCode.PAYMENT_INTENT_CREATE_CARD_PROCESSING_ERROR
            elif parser.code == StripeErrorCode.incorrect_cvc:
                error_code = (
                    PayinErrorCode.PAYMENT_INTENT_CREATE_CARD_INCORRECT_CVC_ERROR
                )
            elif (
                parser.type == StripeErrorType.invalid_request_error
                and parser.has_invalid_param(StripeInvalidParam.payment_method)
            ):
                error_code = (
                    PayinErrorCode.PAYMENT_INTENT_CREATE_INVALID_PROVIDER_PAYMENT_METHOD
                )
            raise CartPaymentCreateError(
                error_code=error_code,
                provider_charge_id=parser.charge_id,
                provider_error_code=parser.code,
                provider_decline_code=parser.decline_code,
                has_provider_error_details=parser.has_details,
            ) from e
        except StripeCommandoError as e:
            if await self._is_card_verified(pgp_payment_info=pgp_payment_info):
                self.req_context.log.info(
                    "[submit_payment_to_provider] Returning mocked payment_intent response for commando mode"
                )
                return COMMANDO_PAYMENT_INTENT

            self.req_context.log.warning(
                "[submit_payment_to_provider] Did not honor payment_intent creation in commando mode",
                payment_intent_id=payment_intent.id,
            )
            raise CartPaymentCreateError(
                error_code=PayinErrorCode.PAYMENT_INTENT_CREATE_ERROR,
                provider_charge_id=None,
                provider_error_code=None,
                provider_decline_code=None,
                has_provider_error_details=False,
            ) from e
        except Exception as e:
            self.req_context.log.exception(
                "[submit_payment_to_provider] Error invoking provider to create a payment",
                payment_intent_id=payment_intent.id,
            )
            raise CartPaymentCreateError(
                error_code=PayinErrorCode.PAYMENT_INTENT_CREATE_ERROR,
                provider_charge_id=None,
                provider_error_code=None,
                provider_decline_code=None,
                has_provider_error_details=False,
            ) from e

    async def _is_card_verified(self, pgp_payment_info: PgpPaymentInfo) -> bool:
        if self.req_context.verify_card_in_commando_mode:
            return await self.payment_repo.is_stripe_card_valid_and_has_success_charge_record(
                stripe_card_stripe_id=pgp_payment_info.pgp_payment_method_resource_id
            )
        return True

    async def update_payment_after_submission_to_provider(
        self,
        payment_intent: PaymentIntent,
        pgp_payment_intent: PgpPaymentIntent,
        provider_payment_intent: ProviderPaymentIntent,
    ) -> Tuple[PaymentIntent, PgpPaymentIntent]:
        self.req_context.log.debug(
            "[update_payment_after_submission_to_provider] Updating state for payment with intent id",
            payment_intent_id=payment_intent.id,
        )
        target_intent_status = self._get_intent_status_from_provider_status(
            provider_payment_intent.status
        )

        # Only update capture_after if payment_intent.status before != requires_capture and after == requires_capture
        capture_after: Optional[datetime] = None
        if (
            payment_intent.status != target_intent_status
            and target_intent_status == IntentStatus.REQUIRES_CAPTURE
        ):
            capture_after = datetime.utcnow() + timedelta(
                minutes=self.capture_service.default_capture_delay_in_minutes
            )

        async with self.payment_repo.payment_database_transaction():
            # Update the records we created to reflect that the provider has been invoked.
            # Cannot gather calls here because of shared connection/transaction
            updated_intent = await self.payment_repo.update_payment_intent(
                update_payment_intent_status_where_input=UpdatePaymentIntentWhereInput(
                    id=payment_intent.id, previous_status=payment_intent.status
                ),
                update_payment_intent_status_set_input=UpdatePaymentIntentSetInput(
                    status=target_intent_status,
                    updated_at=datetime.now(timezone.utc),
                    capture_after=capture_after,
                ),
            )
            update_pgp_payment_intent_where_input = UpdatePgpPaymentIntentWhereInput(
                id=pgp_payment_intent.id
            )
            update_pgp_payment_intent_set_input = UpdatePgpPaymentIntentSetInput(
                status=target_intent_status,
                resource_id=provider_payment_intent.id,
                charge_resource_id=provider_payment_intent.charges.data[0].id,
                amount_capturable=provider_payment_intent.amount_capturable,
                amount_received=provider_payment_intent.amount_received,
                updated_at=datetime.now(timezone.utc),
            )
            updated_pgp_intent = await self.payment_repo.update_pgp_payment_intent(
                update_pgp_payment_intent_where_input=update_pgp_payment_intent_where_input,
                update_pgp_payment_intent_set_input=update_pgp_payment_intent_set_input,
            )
            if self.ENABLE_NEW_CHARGE_TABLES:
                await self._create_new_charge_pair(
                    payment_intent=payment_intent,
                    pgp_payment_intent=pgp_payment_intent,
                    provider_intent=provider_payment_intent,
                    status=self._get_charge_status_from_intent_status(
                        target_intent_status
                    ),
                )

        return updated_intent, updated_pgp_intent

    async def acquire_for_capture(self, payment_intent: PaymentIntent):
        # Throws exception if current state is not same as intent, meaning another request/process has already transitioned
        # intent to a different state.
        return await self.payment_repo.update_payment_intent(
            update_payment_intent_status_where_input=UpdatePaymentIntentWhereInput(
                id=payment_intent.id, previous_status=payment_intent.status
            ),
            update_payment_intent_status_set_input=UpdatePaymentIntentSetInput(
                status=IntentStatus.CAPTURING, updated_at=datetime.now(timezone.utc)
            ),
        )

    async def submit_capture_to_provider(
        self, payment_intent: PaymentIntent, pgp_payment_intent: PgpPaymentIntent
    ) -> ProviderPaymentIntent:
        self.req_context.log.info(
            "[submit_capture_to_provider][start]",
            payment_intent=payment_intent.summary,
            pgp_payment_intent=pgp_payment_intent.summary,
        )

        # Assemble corresponding submit operations depending on amount_to_capture whether below small amount thresdhold
        submit_op: Coroutine[Any, Any, ProviderPaymentIntent]
        capture_idempotency_key = str(uuid.uuid4())

        should_capture_then_refund_small_amount_intent = (
            payment_intent.amount < self.PAYMENT_INTENT_SMALL_AMOUNT_THRESHOLD
            and runtime.get_boolean(ENABLE_SMALL_AMOUNT_CAPTURE_THEN_REFUND, True)
        )

        if should_capture_then_refund_small_amount_intent:
            submit_op = self._capture_small_amount_provider_payment_intent(
                payment_intent=payment_intent,
                pgp_payment_intent=pgp_payment_intent,
                capture_idempotency_key=capture_idempotency_key,
            )
        else:
            submit_op = self._capture_provider_payment_intent(
                amount_to_capture=payment_intent.amount,
                pgp_payment_intent=pgp_payment_intent,
                country=CountryCode(payment_intent.country),
                capture_idempotency_key=capture_idempotency_key,
            )

        try:
            self.req_context.log.info(
                "[submit_capture_to_provider] Capturing payment intent",
                country=payment_intent.country,
                idempotency_key=capture_idempotency_key,
                amount_to_capture=payment_intent.amount,
                pgp_payment_intent_id=pgp_payment_intent.resource_id,
            )
            # Make call to Stripe.  The idempotency key used here is generated each time, as we expect retries from a particular request
            # to be triggered through scheduled jobs.
            provider_intent = await submit_op  # actually execute the submit action
        except InvalidRequestError as e:
            parser = StripeErrorParser(e)
            if parser.code == StripeErrorCode.payment_intent_unexpected_state:
                raise ProviderPaymentIntentUnexpectedStatusError(
                    provider_payment_intent_status=parser.payment_intent_data.get(
                        "status", None
                    ),
                    pgp_payment_intent_status=pgp_payment_intent.status,
                    original_error=e,
                ) from e
            else:
                raise InvalidProviderRequestError(e) from e
        except StripeError as e:
            self.req_context.log.exception(
                "Provider error during capture",
                payment_intent_id=payment_intent.id,
                stripe_error_code=e.code,
            )
            raise ProviderError(e) from e
        except Exception:
            self.req_context.log.exception(
                "Unknown error capturing intent with provider",
                payment_intent_id=payment_intent.id,
            )
            raise

        return provider_intent

    async def _capture_provider_payment_intent(
        self,
        amount_to_capture: int,
        pgp_payment_intent: PgpPaymentIntent,
        country: CountryCode,
        capture_idempotency_key: str,
    ) -> ProviderPaymentIntent:
        capture_request = StripeCapturePaymentIntentRequest(
            sid=pgp_payment_intent.resource_id, amount_to_capture=amount_to_capture
        )
        provider_intent_data = await self.stripe_async_client.capture_payment_intent(
            country=country,
            request=capture_request,
            idempotency_key=capture_idempotency_key,
        )
        return provider_intent_data

    async def _capture_small_amount_provider_payment_intent(
        self,
        payment_intent: PaymentIntent,
        pgp_payment_intent: PgpPaymentIntent,
        capture_idempotency_key: str,
    ) -> ProviderPaymentIntent:
        """
        Attempt to capture a payment intent with amount_to_capture lower than what provider allows to.
        Trick here is:
        1. Capture the total amount initially authorized (payment_intent.amount_inited)
        2. Refund additional amount we captured in above step (payment_intent.amount_inited - payment_intent.amount)

        Failure scenario analysis:
        a. #1 eventually failed to capture: same as regular capture attempt,
            payment_intent status will eventually flip to [capture_failed] for further manual triage
        b. #1 went through, but we were not able to start refund step due to interim error
        c. #1 and #2 when through but we were not able to update our control object
            to reflect successful capture record
        d. #2 eventually didn't went through on stripe end.
            payment_intent status will eventually flip to [capture_failed] for further manual triage
        """

        self.req_context.log.info(
            "[_capture_small_amount_provider_payment_intent][start]",
            payment_intent_id=payment_intent.id,
            pgp_payment_intent_id=pgp_payment_intent.id,
            net_amount_to_capture=payment_intent.amount,
            init_amount_authorized=payment_intent.amount_initiated,
        )

        amount_to_capture = payment_intent.amount_initiated
        amount_to_refund = payment_intent.amount_initiated - payment_intent.amount
        country_code = CountryCode(payment_intent.country)

        try:
            # for failure scenario (a), same payment intent can only be captured once on stripe end.
            # no need to worry duplicate capture
            await self._capture_provider_payment_intent(
                amount_to_capture=amount_to_capture,
                pgp_payment_intent=pgp_payment_intent,
                country=country_code,
                capture_idempotency_key=capture_idempotency_key,
            )
        except InvalidRequestError as e:
            # Only handle and accept "payment_intent_unexpected_state" error with actual provider
            # payment intent status == succeeded. In this case, we simply assemble a ProviderPaymentIntent object
            # from error body and use it as-if we successfully captured this payment intent
            # and move on with life (with next refund step)
            error_parser = StripeErrorParser(e)
            previous_capture_succeeded = (
                error_parser.code == StripeErrorCode.payment_intent_unexpected_state
                and error_parser.payment_intent_data.get("status", None) == "succeeded"
            )
            if not previous_capture_succeeded:
                # Ok, this intent was not succeeded before but fall into some other weird state
                # Let caller handle this error
                raise

        # This refund is unique for a small amount provider payment intent in terms of combination:
        # pgp_payment_intent.idempotency_key (client specified idempotency key when creating cart payment or pi)
        # amount_to_refund
        # action.REFUND
        refund_idempotency_key = self.get_idempotency_key_for_provider_call(
            f"{pgp_payment_intent.idempotency_key}-{amount_to_refund}-small_amount_capture",
            IdempotencyKeyAction.REFUND,
        )

        # for happy case or failure scenario (b), we just continue from where we left to call stripe
        # for failure scenario (c) (d) we got idempotency key to avoid duplicate refund.
        refund_request = StripeRefundChargeRequest(
            charge=pgp_payment_intent.charge_resource_id,
            amount=amount_to_refund,
            reason=StripeRefundChargeRequest.RefundReason.REQUESTED_BY_CONSUMER,
        )

        await self.stripe_async_client.refund_charge(
            country=country_code,
            request=refund_request,
            idempotency_key=refund_idempotency_key,
        )

        # We will retrieve latest payment_intent from stripe to maintain integrity
        # for underlying payment intent, charge and refund data.  See the update_payment_after_capture_with_provider
        # function for management of this state following capture.
        return await self.stripe_async_client.retrieve_payment_intent(
            country=CountryCode(payment_intent.country),
            request=StripeRetrievePaymentIntentRequest(
                id=pgp_payment_intent.resource_id
            ),
        )

    async def update_payment_and_pgp_intent_status_only(
        self,
        new_status: IntentStatus,
        payment_intent: PaymentIntent,
        pgp_payment_intent: PgpPaymentIntent,
    ) -> Tuple[PaymentIntent, PgpPaymentIntent]:
        updateable_new_statues = [IntentStatus.SUCCEEDED, IntentStatus.CANCELLED]
        if new_status not in updateable_new_statues:
            raise ValueError(
                f"only support updating {updateable_new_statues} but found {new_status}"
            )
        if payment_intent.id != pgp_payment_intent.payment_intent_id:
            raise ValueError(
                f"payment_intent and pgp_payment_intent mismatch: payment_intent_id={payment_intent.id}, "
                f"pgp_payment_intent_id={pgp_payment_intent.id}"
            )

        if self.ENABLE_NEW_CHARGE_TABLES:
            raise NotImplementedError()
        else:
            payment_intent_and_pgp_intent = await self.payment_repo.update_payment_and_pgp_payment_intent_status(
                new_status=new_status,
                payment_intent_id=payment_intent.id,
                pgp_payment_intent_id=pgp_payment_intent.id,
            )

            if not payment_intent_and_pgp_intent:
                raise ValueError("payment_intent and pgp_intent shouldn't be None")
            return payment_intent_and_pgp_intent

    async def update_payment_after_capture_with_provider(
        self,
        payment_intent: PaymentIntent,
        pgp_payment_intent: PgpPaymentIntent,
        provider_payment_intent: ProviderPaymentIntent,
    ) -> Tuple[PaymentIntent, PgpPaymentIntent]:
        new_intent_status = self._get_intent_status_from_provider_status(
            provider_payment_intent.status
        )
        new_charge_status = self._get_charge_status_from_intent_status(
            new_intent_status
        )
        self.req_context.log.debug(
            "[update_payment_after_capture_with_provider] Updating intent with new status after capture",
            payment_intent_id=payment_intent.id,
            pgp_payment_intent_id=pgp_payment_intent.id,
            status=new_intent_status,
        )

        # Update state
        async with self.payment_repo.payment_database_transaction():
            updated_payment_intent = await self.payment_repo.update_payment_intent_capture_state(
                id=payment_intent.id,
                status=new_intent_status,
                captured_at=datetime.now(timezone.utc),
            )
            updated_pgp_payment_intent = await self.payment_repo.update_pgp_payment_intent(
                update_pgp_payment_intent_where_input=UpdatePgpPaymentIntentWhereInput(
                    id=pgp_payment_intent.id
                ),
                update_pgp_payment_intent_set_input=UpdatePgpPaymentIntentSetInput(
                    status=new_intent_status,
                    resource_id=str(provider_payment_intent.id),
                    charge_resource_id=str(provider_payment_intent.charges.data[0].id),
                    amount_capturable=provider_payment_intent.amount_capturable,
                    amount_received=provider_payment_intent.amount_received,
                    updated_at=datetime.now(timezone.utc),
                ),
            )

            if self.ENABLE_NEW_CHARGE_TABLES:
                await self._update_charge_pair_after_capture(
                    payment_intent, new_charge_status, provider_payment_intent
                )

            # If a partial refund was performed prior to capture, there will be a refund generated from the intent,
            # as the final amount captured is less than the originally authorized amount.  Ensure we record this
            # refund in our system.
            # TODO remove runtime flag after verification
            if feature_flags.record_refund_from_provider():
                provider_refund = self._get_provider_refund_from_intent_if_exists(
                    provider_payment_intent=provider_payment_intent
                )
                if provider_refund:
                    # If there is a refund, there will be a single record of it from the provider.  Use a placeholder value for
                    # idempotency key since this comes not from a client request, but rather internal logic.
                    await self.create_refund_from_provider(
                        payment_intent_id=payment_intent.id,
                        idempotency_key=f"{payment_intent.idempotency_key}-refund-at-capture",
                        provider_refund=provider_refund,
                    )

        return updated_payment_intent, updated_pgp_payment_intent

    async def _update_charge_pair_after_capture(
        self,
        payment_intent: PaymentIntent,
        status: ChargeStatus,
        provider_intent: ProviderPaymentIntent,
    ) -> Tuple[PaymentCharge, PgpPaymentCharge]:
        # Assumption: this is called within a transaction already
        payment_charge = await self.payment_repo.update_payment_charge_status(
            payment_intent.id, status.value
        )
        pgp_charge = await self._update_pgp_charge_from_provider(
            payment_charge.id, status, provider_intent
        )
        return payment_charge, pgp_charge

    async def cancel_provider_payment_charge(
        self,
        payment_intent: PaymentIntent,
        pgp_payment_intent: PgpPaymentIntent,
        reason,
    ) -> ProviderPaymentIntent:
        self.req_context.log.info(
            "[cancel_provider_payment_charge][start]",
            payment_intent=payment_intent.summary,
            pgp_payment_intent=pgp_payment_intent.summary,
        )
        try:
            intent_request = StripeCancelPaymentIntentRequest(
                sid=pgp_payment_intent.resource_id, cancellation_reason=reason
            )
            return await self.stripe_async_client.cancel_payment_intent(
                country=CountryCode(payment_intent.country),
                request=intent_request,
                idempotency_key=self.get_idempotency_key_for_provider_call(
                    payment_intent.idempotency_key, IdempotencyKeyAction.CANCEL
                ),
            )
        except StripeError as e:
            self.req_context.log.warning(
                "[cancel_provider_payment_charge] Cancel payment not successful",
                payment_intent_id=payment_intent.id,
                stripe_error_code=e.code,
                exception=str(e),
            )
            raise PaymentChargeRefundError(
                error_code=PayinErrorCode.PAYMENT_INTENT_ADJUST_REFUND_ERROR
            )
        except Exception:
            self.req_context.log.exception(
                "[cancel_provider_payment_charge] Error attempting payment cancellation with provider",
                payment_intent_id=payment_intent.id,
            )
            # todo was retryable, need refine
            raise PaymentChargeRefundError(
                error_code=PayinErrorCode.PAYMENT_INTENT_ADJUST_REFUND_ERROR
            )

    async def refund_provider_payment(
        self,
        refund: Refund,
        payment_intent: PaymentIntent,
        pgp_payment_intent: PgpPaymentIntent,
        refund_amount: int,
    ) -> ProviderRefund:

        self.req_context.log.info(
            "[refund_provider_payment][start]",
            payment_intent=payment_intent.summary,
            pgp_payment_intent=pgp_payment_intent.summary,
        )
        try:
            refund_request = StripeRefundChargeRequest(
                charge=pgp_payment_intent.charge_resource_id,
                amount=refund_amount,
                reason=StripeRefundChargeRequest.RefundReason(refund.reason.value)
                if refund.reason
                else None,
            )

            if payment_intent.application_fee_amount:
                refund_request.refund_application_fee = True
                refund_request.reverse_transfer = True
            response = await self.stripe_async_client.refund_charge(
                country=CountryCode(payment_intent.country),
                request=refund_request,
                idempotency_key=self.get_idempotency_key_for_provider_call(
                    refund.idempotency_key, IdempotencyKeyAction.REFUND
                ),
            )
            return response
        except StripeError as e:
            self.req_context.log.warning(
                "[refund_provider_payment] Cannot refund payment with provider",
                payment_intent_id=payment_intent.id,
                refund_id=refund.id,
                stripe_error_code=e.code,
                exception=str(e),
            )
            raise PaymentIntentCancelError(
                error_code=PayinErrorCode.PAYMENT_INTENT_ADJUST_REFUND_ERROR
            )
        except Exception:
            self.req_context.log.exception(
                "[refund_provider_payment] Error refunding payment with provider",
                payment_intent_id=payment_intent.id,
                refund_id=refund.id,
            )
            # todo was retryable need refine
            raise PaymentIntentCancelError(
                error_code=PayinErrorCode.PAYMENT_INTENT_ADJUST_REFUND_ERROR
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

    async def _update_charge_pair_after_refund(
        self, payment_intent: PaymentIntent, provider_refund: ProviderRefund
    ) -> Tuple[PaymentCharge, PgpPaymentCharge]:
        # Assumption: this is called within a transaction already
        status = ChargeStatus(provider_refund.status)
        payment_charge = await self.payment_repo.update_payment_charge(
            payment_intent_id=payment_intent.id,
            status=status.value,
            amount_refunded=provider_refund.amount,
        )
        pgp_charge = await self.payment_repo.update_pgp_payment_charge(
            payment_charge_id=payment_charge.id,
            status=status.value,
            amount=payment_intent.amount,
            amount_refunded=provider_refund.amount,
        )
        return payment_charge, pgp_charge

    async def _update_charge_pair_after_amount_reduction(
        self, payment_intent: PaymentIntent, amount: int
    ) -> Tuple[PaymentCharge, PgpPaymentCharge]:
        # Assumption: this is called within a transaction already
        payment_charge = await self.payment_repo.update_payment_charge_amount(
            payment_intent_id=payment_intent.id, amount=amount
        )
        pgp_charge = await self.payment_repo.update_pgp_payment_charge_amount(
            payment_charge_id=payment_charge.id, amount=amount
        )
        return payment_charge, pgp_charge

    async def _update_charge_pair_after_cancel(
        self, payment_intent: PaymentIntent, status: ChargeStatus
    ) -> Tuple[PaymentCharge, PgpPaymentCharge]:
        # Assumption: this is called within a transaction already
        payment_charge = await self.payment_repo.update_payment_charge_status(
            payment_intent_id=payment_intent.id, status=status.value
        )
        pgp_payment_charge = await self.payment_repo.update_pgp_payment_charge_status(
            payment_charge_id=payment_charge.id, status=status.value
        )
        return payment_charge, pgp_payment_charge

    async def update_payment_after_cancel_with_provider(
        self,
        payment_intent: PaymentIntent,
        pgp_payment_intent: PgpPaymentIntent,
        provider_payment_intent: ProviderPaymentIntent,
    ) -> Tuple[PaymentIntent, PgpPaymentIntent]:
        now = datetime.now(timezone.utc)
        async with self.payment_repo.payment_database_transaction():
            updated_intent = await self.payment_repo.update_payment_intent(
                update_payment_intent_status_where_input=UpdatePaymentIntentWhereInput(
                    id=payment_intent.id, previous_status=payment_intent.status
                ),
                update_payment_intent_status_set_input=UpdatePaymentIntentSetInput(
                    status=IntentStatus.CANCELLED, updated_at=now, cancelled_at=now
                ),
            )
            updated_pgp_intent = await self.payment_repo.update_pgp_payment_intent(
                update_pgp_payment_intent_where_input=UpdatePgpPaymentIntentWhereInput(
                    id=pgp_payment_intent.id
                ),
                update_pgp_payment_intent_set_input=UpdatePgpPaymentIntentSetInput(
                    status=IntentStatus.CANCELLED,
                    resource_id=provider_payment_intent.id,
                    charge_resource_id=provider_payment_intent.charges.data[0].id,
                    amount_capturable=provider_payment_intent.amount_capturable,
                    amount_received=provider_payment_intent.amount_received,
                    updated_at=now,
                    cancelled_at=now,
                ),
            )
            if self.ENABLE_NEW_CHARGE_TABLES:
                await self._update_charge_pair_after_cancel(
                    payment_intent=payment_intent, status=ChargeStatus.CANCELLED
                )

            # When cancelling a delayed capture intent, there will be a refund generated since the originally authorized amount is no longer held against
            # the payment method.  Ensure we record this refund in our system.
            # TODO remove runtime flag after verification
            if feature_flags.record_refund_from_provider():
                provider_refund = self._get_provider_refund_from_intent_if_exists(
                    provider_payment_intent=provider_payment_intent
                )
                if provider_refund:
                    # If there is a refund, there will be a single record of it from the provider.  Use a placeholder value for
                    # idempotency key since this comes not from a client request, but rather internal logic.
                    await self.create_refund_from_provider(
                        payment_intent_id=payment_intent.id,
                        idempotency_key=f"{payment_intent.idempotency_key}-refund-at-cancel",
                        provider_refund=provider_refund,
                    )

        return updated_intent, updated_pgp_intent

    async def create_refund_from_provider(
        self,
        payment_intent_id: uuid.UUID,
        idempotency_key: str,
        provider_refund: ProviderRefund,
    ) -> Tuple[Refund, PgpRefund]:
        target_status = self._get_refund_status_from_provider_refund(
            provider_refund.status
        )

        # Reason is extracted from provider refund object.  For stripe, we observe this is None if amount refunded
        # is >= minimum charge for currency, or "requested_by_customer" if below (due to our small amount capture handling).
        reason = self._get_refund_reason_from_provider_refund(provider_refund.reason)

        refund = await self.payment_repo.insert_refund(
            id=uuid.uuid4(),
            payment_intent_id=payment_intent_id,
            idempotency_key=idempotency_key,
            status=target_status,
            amount=provider_refund.amount,
            reason=reason,
        )

        pgp_refund = await self.payment_repo.insert_pgp_refund(
            id=uuid.uuid4(),
            refund_id=refund.id,
            idempotency_key=idempotency_key,
            status=target_status,
            pgp_code=PgpCode.STRIPE,
            pgp_resource_id=provider_refund.id,
            pgp_charge_resource_id=provider_refund.charge,
            amount=provider_refund.amount,
            reason=reason,
        )

        return refund, pgp_refund

    async def create_new_refund(
        self,
        refund_amount: int,
        cart_payment: CartPayment,
        payment_intent: PaymentIntent,
        idempotency_key: str,
        reason: RefundReason,
    ) -> Tuple[Refund, PgpRefund]:
        async with self.payment_repo.payment_database_transaction():
            refund = await self.payment_repo.insert_refund(
                id=uuid.uuid4(),
                payment_intent_id=payment_intent.id,
                idempotency_key=idempotency_key,
                status=RefundStatus.PROCESSING,
                amount=refund_amount,
                reason=reason,
            )

            pgp_refund = await self.payment_repo.insert_pgp_refund(
                id=uuid.uuid4(),
                refund_id=refund.id,
                idempotency_key=idempotency_key,
                status=RefundStatus.PROCESSING,
                pgp_code=PgpCode.STRIPE,
                pgp_resource_id=None,
                pgp_charge_resource_id=None,
                amount=refund_amount,
                reason=reason,
            )

        return refund, pgp_refund

    async def update_payment_after_refund_with_provider(
        self,
        refund_amount: int,
        payment_intent: PaymentIntent,
        pgp_payment_intent: PgpPaymentIntent,
        refund: Refund,
        pgp_refund: PgpRefund,
        provider_refund: ProviderRefund,
    ) -> PaymentIntent:
        target_refund_status = self._get_refund_status_from_provider_refund(
            provider_refund.status
        )
        async with self.payment_repo.payment_database_transaction():
            updated_intent = await self.payment_repo.update_payment_intent_amount(
                id=payment_intent.id, amount=(payment_intent.amount - refund_amount)
            )
            # PgpPaymentIntent is not updated since the provider amount does not change.
            await self.payment_repo.update_refund_status(
                refund_id=refund.id, status=target_refund_status
            )
            await self.payment_repo.update_pgp_refund(
                pgp_refund_id=pgp_refund.id,
                status=target_refund_status,
                pgp_resource_id=provider_refund.id,
                pgp_charge_resource_id=provider_refund.charge,
            )
            if self.ENABLE_NEW_CHARGE_TABLES:
                await self._update_charge_pair_after_refund(
                    payment_intent=payment_intent, provider_refund=provider_refund
                )

        return updated_intent

    async def increase_payment_amount(
        self,
        amount: int,
        split_payment: Optional[SplitPayment],
        cart_payment: CartPayment,
        existing_payment_intents: List[PaymentIntent],
        idempotency_key: str,
    ) -> Tuple[PaymentIntent, PgpPaymentIntent]:
        self.req_context.log.info(
            "[increase_payment_amount] New intent for cart payment, due to higher amount",
            idempotency_key=idempotency_key,
            cart_payment_id=cart_payment.id,
            new_amount=amount,
            old_amount=cart_payment.amount,
        )

        # Immutable properties, such as currency, are derived from the previous/most recent intent in order to
        # have these fields for new intent submission and keep API simple for clients.
        most_recent_intent = self.get_most_recent_intent(existing_payment_intents)
        legacy_consumer_charge_id = most_recent_intent.legacy_consumer_charge_id

        # Get payment resource IDs, required for submitting intent to providers
        pgp_intent = await self._get_most_recent_pgp_payment_intent(most_recent_intent)
        self.req_context.log.debug(
            "[increase_payment_amount] Gathering fields from last intent",
            cart_payment_id=cart_payment.id,
            pgp_payment_intent_id=pgp_intent.id,
        )

        # New intent pair for the higher amount
        async with self.payment_repo.payment_database_transaction():
            payment_intent, pgp_payment_intent = await self._create_new_intent_pair(
                cart_payment_id=cart_payment.id,
                legacy_consumer_charge_id=legacy_consumer_charge_id,
                idempotency_key=idempotency_key,
                payment_method_id=most_recent_intent.payment_method_id,
                provider_payment_method_id=pgp_intent.payment_method_resource_id,
                provider_customer_resource_id=pgp_intent.customer_resource_id,
                provider_metadata=most_recent_intent.metadata,
                amount=amount,
                country=most_recent_intent.country,
                currency=most_recent_intent.currency,
                split_payment=split_payment,
                capture_method=most_recent_intent.capture_method,
                payer_statement_description=most_recent_intent.statement_descriptor,
            )

            # Insert adjustment history record if the payment intent is not yet captured.
            if self.does_intent_require_capture(most_recent_intent):
                self.req_context.log.debug(
                    "[increase_payment_amount] Inserting payment intent adjustment history",
                    payment_intent_id=most_recent_intent.id,
                )
                await self.payment_repo.insert_payment_intent_adjustment_history(
                    id=uuid.uuid4(),
                    payer_id=cart_payment.payer_id,
                    payment_intent_id=payment_intent.id,
                    amount=amount,
                    amount_original=cart_payment.amount,
                    amount_delta=(amount - cart_payment.amount),
                    currency=payment_intent.currency,
                    idempotency_key=payment_intent.idempotency_key,
                )

        self.req_context.log.debug(
            "[increase_payment_amount] Created intent pair",
            cart_pament_id=cart_payment.id,
            payment_intent_id=payment_intent.id,
            pgp_payment_intent_id=pgp_payment_intent.id,
        )

        return payment_intent, pgp_payment_intent

    async def lower_amount_for_uncaptured_payment(
        self,
        cart_payment: CartPayment,
        payment_intent: PaymentIntent,
        amount: int,
        idempotency_key: str,
    ) -> PaymentIntent:
        # There is no need to call provider at this point in time.  The original auth done upon cart payment
        # creation is sufficient to cover a lower amount, so there is no need to update the amount with the provider.
        # Instead we will record updated amounts in our system, which will be reflected at time of (delayed) capture.
        # We skip updating the pgp_payment_intent since state in the provider is not changed yet.

        async with self.payment_repo.payment_database_transaction():
            updated_intent = await self.payment_repo.update_payment_intent_amount(
                id=payment_intent.id, amount=amount
            )
            if self.ENABLE_NEW_CHARGE_TABLES:
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
                idempotency_key=idempotency_key,
            )

        return updated_intent

    async def get_pgp_payment_info_v1(
        self,
        legacy_country_id: int,
        raw_payer: RawPayer,
        raw_payment_method: RawPaymentMethod,
    ) -> Tuple[PgpPaymentInfo, LegacyPayment]:

        pgp_payer_ref_id = raw_payer.pgp_payer_resource_id
        pgp_payment_method_ref_id = raw_payment_method.pgp_payment_method_resource_id

        if not raw_payer.payer_entity:
            self.req_context.log.error(
                "[get_pgp_payment_method] No payer entity found."
            )
            raise CartPaymentCreateError(
                error_code=PayinErrorCode.CART_PAYMENT_CREATE_INVALID_DATA,
                provider_charge_id=None,
                provider_error_code=None,
                provider_decline_code=None,
                has_provider_error_details=False,
            )

        result_legacy_payment = LegacyPayment(
            dd_consumer_id=raw_payer.payer_entity.payer_reference_id,
            dd_stripe_card_id=raw_payment_method.legacy_dd_stripe_card_id,
            dd_country_id=legacy_country_id,
        )
        self.req_context.log.debug(
            "[get_pgp_payment_method] Legacy payment generated for resource lookup",
            legacy_payment=result_legacy_payment,
        )
        pgp_payment_info = PgpPaymentInfo(
            pgp_payment_method_resource_id=pgp_payment_method_ref_id,
            pgp_payer_resource_id=pgp_payer_ref_id,
        )
        return pgp_payment_info, result_legacy_payment

    async def get_pgp_payment_info_v0(
        self, legacy_payment: LegacyPayment
    ) -> PgpPaymentInfo:
        # We need to look up the pgp's account ID and payment method ID, so that we can use then for intent
        # submission and management.  A client is expected to either provide either
        #   a. both payer_id and payment_method_id, which we can use to look up corresponding pgp resource IDs
        #   b. stripe resource IDs directly via the legacy_payment request field.
        # Used by legacy clients who haven't fully adopted payin service yet, and in this case we directly use
        # those IDs and no lookup is needed.  A LegacyPayment instance is also returned since it is required for
        # persisting charge records in the old system.
        self.req_context.log.debug(
            "[get_pgp_payment_method_by_legacy_payment] Getting payment info."
        )

        provider_payment_method_id = None

        # Legacy payment case: no payer_id/payment_method_id provided
        provider_payer_id = legacy_payment.stripe_customer_id
        provider_payment_method_id = legacy_payment.stripe_card_id

        # Ensure we have the necessary fields.  Though payer_client/payment_method_client already throws exceptions
        # if not found, still check here since we have to support the legacy payment case.
        if not provider_payer_id:
            self.req_context.log.warning(
                "[get_pgp_payment_method_by_legacy_payment] No payer pgp resource ID found."
            )
            raise CartPaymentCreateError(
                error_code=PayinErrorCode.CART_PAYMENT_CREATE_INVALID_DATA,
                provider_charge_id=None,
                provider_error_code=None,
                provider_decline_code=None,
                has_provider_error_details=False,
            )

        if not provider_payment_method_id:
            self.req_context.log.warning(
                "[get_pgp_payment_method_by_legacy_payment] No payment method pgp resource ID found."
            )
            raise CartPaymentCreateError(
                error_code=PayinErrorCode.CART_PAYMENT_CREATE_INVALID_DATA,
                provider_charge_id=None,
                provider_error_code=None,
                provider_decline_code=None,
                has_provider_error_details=False,
            )

        pgp_payment_info = PgpPaymentInfo(
            pgp_payment_method_resource_id=PgpPaymentMethodResourceId(
                provider_payment_method_id
            ),
            pgp_payer_resource_id=PgpPayerResourceId(provider_payer_id),
        )

        return pgp_payment_info

    async def mark_payment_as_failed(
        self, payment_intent: PaymentIntent, pgp_payment_intent: PgpPaymentIntent
    ) -> Tuple[PaymentIntent, PgpPaymentIntent]:
        self.req_context.log.info(
            "[mark_payment_as_failed] Marking intent pair as failed.",
            payment_intent_id=payment_intent.id,
            pgp_payment_intent_id=pgp_payment_intent.id,
        )
        async with self.payment_repo.payment_database_transaction():
            updated_intent = await self.payment_repo.update_payment_intent(
                update_payment_intent_status_where_input=UpdatePaymentIntentWhereInput(
                    id=payment_intent.id, previous_status=payment_intent.status
                ),
                update_payment_intent_status_set_input=UpdatePaymentIntentSetInput(
                    status=IntentStatus.FAILED, updated_at=datetime.now(timezone.utc)
                ),
            )
            updated_pgp_intent = await self.payment_repo.update_pgp_payment_intent_status(
                id=pgp_payment_intent.id, status=IntentStatus.FAILED
            )

        return updated_intent, updated_pgp_intent

    def populate_cart_payment_for_response(
        self,
        *,
        cart_payment: CartPayment,
        payment_intent: PaymentIntent,
        pgp_payment_intent: PgpPaymentIntent,
        last_active_sibling_payment_intent: Optional[PaymentIntent],
    ) -> CartPayment:
        """
        Populate fields within a CartPayment instance to be suitable for an API response body.
        Since CartPayment is a view on top of several models, it is necessary to synthesize info
        into a CartPayment instance from associated models.

        Arguments:
            cart_payment {CartPayment} -- The CartPayment instance to update.
            payment_intent {PaymentIntent} -- An associated PaymentIntent.
            pgp_payment_intent {PgpPaymentIntent} -- An associated PgpPaymentIntent.
            last_active_sibling_payment_intent {PaymentIntent} -- Most recent active PaymentIntent for the same cart_payment that preceded payment_intent
        """
        cart_payment.payer_statement_description = payment_intent.statement_descriptor
        cart_payment.payment_method_id = payment_intent.payment_method_id

        if (
            payment_intent.application_fee_amount
            and pgp_payment_intent.payout_account_id
        ):
            cart_payment.split_payment = SplitPayment(
                payout_account_id=pgp_payment_intent.payout_account_id,
                application_fee_amount=payment_intent.application_fee_amount,
            )

        # If any payment intent is in the doordash pending state, submitted is considered to be false
        cart_payment.deferred = self.is_payment_intent_pending(
            last_active_sibling_payment_intent
            if last_active_sibling_payment_intent
            else payment_intent
        )

        return cart_payment

    async def update_cart_payment_attributes(
        self,
        *,
        cart_payment: CartPayment,
        idempotency_key: str,
        amount: int,
        client_description: Optional[str],
        payment_intent: PaymentIntent,
        pgp_payment_intent: PgpPaymentIntent,
    ) -> CartPayment:
        updated_cart_payment = await self.payment_repo.update_cart_payment_details(
            cart_payment_id=cart_payment.id,
            amount=amount,
            client_description=client_description,
        )
        return updated_cart_payment

    async def update_state_after_provider_submission(
        self,
        payment_intent: PaymentIntent,
        pgp_payment_intent: PgpPaymentIntent,
        provider_payment_intent: ProviderPaymentIntent,
    ) -> Tuple[PaymentIntent, PgpPaymentIntent]:
        # Update state of payment in our system now that payment exists in provider
        updated_payment_intent, updated_pgp_payment_intent = await self.update_payment_after_submission_to_provider(
            payment_intent=payment_intent,
            pgp_payment_intent=pgp_payment_intent,
            provider_payment_intent=provider_payment_intent,
        )

        return (updated_payment_intent, updated_pgp_payment_intent)

    async def update_cart_payment_post_cancellation(self, id: uuid.UUID):
        now = datetime.now(timezone.utc)
        cancelled_cart_payment = await self.payment_repo.update_cart_payment_post_cancellation(
            update_cart_payment_post_cancellation_input=UpdateCartPaymentPostCancellationInput(
                id=id, updated_at=now, deleted_at=now
            )
        )
        return cancelled_cart_payment

    async def list_cart_payments_by_reference_id(
        self, reference_id: str, reference_type: str
    ) -> List[CartPayment]:
        return await self.payment_repo.get_cart_payments_by_reference_id(
            input=ListCartPaymentsByReferenceId(
                reference_id=reference_id, reference_type=reference_type
            )
        )

    async def list_cart_payments_by_payer_reference_id(
        self, payer_reference_id: str, payer_reference_id_type: PayerReferenceIdType
    ) -> List[CartPayment]:
        try:
            raw_payer = await self.payer_client.get_raw_payer(
                mixed_payer_id=not_none(payer_reference_id),
                payer_reference_id_type=not_none(payer_reference_id_type),
            )
        except PayerReadError:
            self.req_context.log.exception(
                "[list_cart_payments] No corresponding payer found for the given input"
            )
            raise CartPaymentReadError(
                error_code=PayinErrorCode.CART_PAYMENT_PAYER_NOT_FOUND_ERROR
            )
        payer_id = str(raw_payer.to_payer().id)
        consumer_id = await self.payer_client.get_consumer_id_by_payer_id(
            payer_id=not_none(payer_id)
        )
        if not consumer_id:
            self.req_context.log.exception(
                "[list_cart_payments] No valid consumer found for the input."
            )
            raise CartPaymentReadError(
                error_code=PayinErrorCode.CART_PAYMENT_DATA_INVALID
            )
        return await self.payment_repo.get_cart_payments_by_dd_consumer_id(
            input=GetCartPaymentsByConsumerIdInput(dd_consumer_id=consumer_id)
        )

    async def list_cart_payments_by_payer_id(self, payer_id: str) -> List[CartPayment]:
        consumer_id = await self.payer_client.get_consumer_id_by_payer_id(
            payer_id=payer_id
        )
        if not consumer_id:
            self.req_context.log.exception(
                "[list_cart_payments] No valid consumer found for the input."
            )
            raise CartPaymentReadError(
                error_code=PayinErrorCode.CART_PAYMENT_DATA_INVALID
            )
        return await self.payment_repo.get_cart_payments_by_dd_consumer_id(
            input=GetCartPaymentsByConsumerIdInput(dd_consumer_id=consumer_id)
        )

    async def get_cart_payment_by_reference_id(
        self, reference_id: str, reference_type: str
    ) -> Optional[CartPayment]:
        return await self.payment_repo.get_most_recent_cart_payment_by_reference_id_from_primary(
            input=GetCartPaymentsByReferenceId(
                reference_id=reference_id, reference_type=reference_type
            )
        )

    async def get_consumer_charge_by_reference_id(
        self, reference_id: str, reference_type: str
    ) -> Optional[LegacyConsumerCharge]:
        input: GetConsumerChargeByReferenceId
        try:
            input = GetConsumerChargeByReferenceId(
                target_id=int(reference_id), target_ct_id=int(reference_type)
            )
        except ValueError:
            self.req_context.log.exception(
                "[get_consumer_charge_by_reference_id] Non-numeric reference_id/reference_type provided.",
                reference_id=reference_id,
                reference_type=reference_type,
            )
            raise CartPaymentReadError(
                error_code=PayinErrorCode.CART_PAYMENT_DATA_INVALID
            )
        return await self.payment_repo.get_legacy_consumer_charge_by_reference_id(
            input=input
        )
