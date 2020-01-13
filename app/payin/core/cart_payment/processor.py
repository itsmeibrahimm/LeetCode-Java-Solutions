import uuid
from asyncio import gather
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, NewType, Optional, Tuple, Union

from doordash_python_stats.ddstats import doorstats_global
from fastapi import Depends
from stripe.error import InvalidRequestError, StripeError
from structlog.stdlib import BoundLogger

from app.commons import tracing
from app.commons.context.app_context import AppContext, get_global_app_context
from app.commons.context.req_context import (
    get_context_from_req,
    get_logger_from_req,
    get_stripe_async_client_from_req,
    ReqContext,
)
from app.commons.lock.locks import PaymentLock, PaymentLockAcquireError
from app.commons.operational_flags import ENABLE_SMALL_AMOUNT_CAPTURE_THEN_REFUND
from app.commons.providers.errors import StripeCommandoError
from app.commons.providers.stripe.commando import COMMANDO_PAYMENT_INTENT
from app.commons.providers.stripe.constants import STRIPE_PLATFORM_ACCOUNT_IDS
from app.commons.providers.stripe.errors import StripeErrorCode, StripeErrorParser
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
from app.commons.timing import track_func
from app.commons.types import CountryCode, Currency, LegacyCountryId, PgpCode
from app.commons.utils.validation import not_none
from app.payin.core import feature_flags
from app.payin.core.cart_payment.model import (
    CartPayment,
    CorrelationIds,
    LegacyConsumerCharge,
    LegacyPayment,
    LegacyStripeCharge,
    PaymentCharge,
    PaymentIntent,
    PaymentIntentAdjustmentHistory,
    PgpPaymentCharge,
    PgpPaymentIntent,
    PgpRefund,
    Refund,
    SplitPayment,
    CartPaymentList,
)
from app.payin.core.cart_payment.types import (
    CaptureMethod,
    ChargeStatus,
    IntentStatus,
    LegacyConsumerChargeId,
    LegacyStripeChargeStatus,
    RefundStatus,
)
from app.payin.core.exceptions import (
    CartPaymentCreateError,
    CartPaymentReadError,
    CartPaymentUpdateError,
    CommandoProcessingError,
    InvalidProviderRequestError,
    PayinErrorCode,
    PaymentChargeRefundError,
    PaymentIntentCancelError,
    PaymentIntentConcurrentAccessError,
    PaymentIntentCouldNotBeUpdatedError,
    PaymentIntentNotInRequiresCaptureState,
    PaymentIntentRefundError,
    PaymentMethodReadError,
    ProviderError,
    ProviderPaymentIntentUnexpectedStatusError,
)
from app.commons.utils.legacy_utils import (
    get_country_code_by_id,
    get_country_id_by_code,
)
from app.payin.core.payer.model import Payer, RawPayer
from app.payin.core.payer.payer_client import PayerClient
from app.payin.core.payment_method.model import RawPaymentMethod
from app.payin.core.payment_method.processor import PaymentMethodClient
from app.payin.core.payment_method.types import PgpPaymentInfo, CartPaymentSortKey
from app.payin.core.types import (
    PayerIdType,
    PaymentMethodIdType,
    PgpPayerResourceId,
    PgpPaymentMethodResourceId,
    PayerReferenceIdType,
)
from app.payin.repository.cart_payment_repo import (
    CartPaymentRepository,
    UpdateCartPaymentPostCancellationInput,
    UpdatePaymentIntentSetInput,
    UpdatePaymentIntentWhereInput,
    UpdatePgpPaymentIntentSetInput,
    UpdatePgpPaymentIntentWhereInput,
    GetCartPaymentsByConsumerIdInput,
)

IntentFullfillmentResult = NewType("IntentFullfillmentResult", Tuple[str, int])


class LegacyPaymentInterface:
    DEFAULT_COUNTRY_ID = LegacyCountryId.US
    ADDITIONAL_INFO_DESTINATION_KEY = "destination"
    ADDITIONAL_INFO_APPLICATION_FEE_KEY = "application_fee"

    def __init__(
        self,
        app_context: AppContext = Depends(get_global_app_context),
        req_context: ReqContext = Depends(get_context_from_req),
        payment_repo: CartPaymentRepository = Depends(
            CartPaymentRepository.get_repository
        ),
        stripe_async_client: StripeAsyncClient = Depends(
            get_stripe_async_client_from_req
        ),
    ):
        self.app_context = app_context
        self.req_context = req_context
        self.payment_repo = payment_repo
        self.stripe_async_client = stripe_async_client

    def _get_legacy_stripe_charge_status_from_provider_status(
        self, provider_status: str
    ) -> LegacyStripeChargeStatus:
        return LegacyStripeChargeStatus(provider_status)

    async def get_associated_cart_payment_id(
        self, charge_id: int
    ) -> Optional[uuid.UUID]:
        self.req_context.log.debug(
            "Looking up stripe charges for charge", dd_charge_id=charge_id
        )

        payment_intent = await self.payment_repo.get_payment_intent_by_legacy_consumer_charge_id_from_primary(
            charge_id=charge_id
        )
        return payment_intent.cart_payment_id if payment_intent else None

    async def find_existing_payment_charge(
        self, charge_id: int, idempotency_key: str
    ) -> Tuple[Optional[LegacyConsumerCharge], Optional[LegacyStripeCharge]]:
        consumer_charge = await self.payment_repo.get_legacy_consumer_charge_by_id(
            id=charge_id
        )
        if not consumer_charge:
            return None, None

        stripe_charges = await self.payment_repo.get_legacy_stripe_charges_by_charge_id(
            charge_id
        )

        matched_stripe_charges = list(
            filter(
                lambda stripe_charge: stripe_charge.idempotency_key == idempotency_key,
                stripe_charges,
            )
        )
        stripe_charge = None
        if matched_stripe_charges:
            stripe_charge = matched_stripe_charges[0]
        return consumer_charge, stripe_charge

    async def _insert_new_stripe_charge(
        self,
        charge_id: int,
        amount: int,
        currency: Currency,
        idempotency_key: str,
        description: Optional[str],
        card_id: Optional[int],
        additional_payment_info: Optional[Dict[str, Any]],
    ) -> LegacyStripeCharge:
        # Creates a new StripeCharge instance under an existing Charge record.  The StripeCharge record
        # is in initial state (transitions to next state via update_charge_after_payment_submitted).
        dd_additional_payment_info = None
        if additional_payment_info:
            dd_additional_payment_info = str(additional_payment_info)

        return await self.payment_repo.insert_legacy_stripe_charge(
            stripe_id="",
            card_id=card_id,
            charge_id=charge_id,
            amount=amount,
            amount_refunded=0,
            currency=currency,
            status=LegacyStripeChargeStatus.PENDING,
            idempotency_key=idempotency_key,
            additional_payment_info=dd_additional_payment_info,
            description=description,
            error_reason="",
        )

    async def create_new_payment_charges(
        self,
        request_cart_payment: CartPayment,
        legacy_payment: LegacyPayment,
        correlation_ids: CorrelationIds,
        country: CountryCode,
        currency: Currency,
        idempotency_key: str,
    ) -> Tuple[LegacyConsumerCharge, LegacyStripeCharge]:
        self.req_context.log.info(
            "[create_new_payment_charges] Creating charge records in legacy system",
            dd_consumer_id=legacy_payment.dd_consumer_id,
            idempotency_key=idempotency_key,
        )
        # New payment: create new consumer charge
        is_stripe_connect_based = (
            True
            if legacy_payment.dd_additional_payment_info
            and (
                self.ADDITIONAL_INFO_APPLICATION_FEE_KEY
                in legacy_payment.dd_additional_payment_info
                or self.ADDITIONAL_INFO_DESTINATION_KEY
                in legacy_payment.dd_additional_payment_info
            )
            else False
        )

        country_id = legacy_payment.dd_country_id
        if not country_id:
            country_id = get_country_id_by_code(country)

        self.req_context.log.debug("[create_new_payment_charges] Creating new charge")
        now = datetime.now(timezone.utc)
        legacy_consumer_charge = await self.payment_repo.insert_legacy_consumer_charge(
            target_ct_id=int(correlation_ids.reference_type),
            target_id=int(correlation_ids.reference_id),
            consumer_id=legacy_payment.dd_consumer_id,
            idempotency_key=idempotency_key,
            is_stripe_connect_based=is_stripe_connect_based,
            country_id=country_id,
            currency=currency,
            # stripe_customer_id=pgp_payment_intent.customer_resource_id,
            stripe_customer_id=None,
            total=0,
            original_total=request_cart_payment.amount,
            created_at=now,
            updated_at=now,
        )

        legacy_stripe_charge = await self._insert_new_stripe_charge(
            charge_id=legacy_consumer_charge.id,
            amount=request_cart_payment.amount,
            currency=currency,
            idempotency_key=idempotency_key,
            description=request_cart_payment.client_description,
            card_id=legacy_payment.dd_stripe_card_id,
            additional_payment_info=legacy_payment.dd_additional_payment_info,
        )

        return legacy_consumer_charge, legacy_stripe_charge

    async def update_existing_payment_charge(
        self,
        charge_id: int,
        amount: int,
        currency: Currency,
        idempotency_key: str,
        description: Optional[str],
        legacy_payment: LegacyPayment,
    ) -> LegacyStripeCharge:
        # For updates to existing charges, we keep a single charge record but insert an additional stripe_charge record.  This stripe_charge record
        # is inserted in initial state, and transitions to following states via update_charge_after_payment_submitted.
        return await self._insert_new_stripe_charge(
            charge_id=charge_id,
            amount=amount,
            currency=currency,
            idempotency_key=idempotency_key,
            description=description,
            card_id=legacy_payment.dd_stripe_card_id,
            additional_payment_info=legacy_payment.dd_additional_payment_info,
        )

    async def lower_amount_for_uncaptured_payment(
        self, stripe_id: str, amount_refunded: int
    ) -> LegacyStripeCharge:
        return await self.payment_repo.update_legacy_stripe_charge_add_to_amount_refunded(
            stripe_id=stripe_id,
            additional_amount_refunded=amount_refunded,
            refunded_at=datetime.now(),
        )

    async def update_state_after_provider_submission(
        self,
        legacy_stripe_charge: LegacyStripeCharge,
        idempotency_key: str,
        provider_payment_intent: ProviderPaymentIntent,
    ) -> LegacyStripeCharge:
        self.req_context.log.info(
            "[update_state_after_provider_submission] Updating stripe charge record in legacy system",
            idempotency_key=idempotency_key,
            dd_stripe_charge_id=legacy_stripe_charge.id,
            provider_payment_intent_id=provider_payment_intent.id,
        )

        provider_charges = provider_payment_intent.charges
        provider_charge = provider_charges.data[0]

        # After provider payment submission, the charge record remains as is, but the stripe_charge record is updated
        # to fill in details from the provider.

        return await self.payment_repo.update_legacy_stripe_charge_provider_details(
            id=legacy_stripe_charge.id,
            stripe_id=provider_charge.id,
            amount=provider_charge.amount,
            amount_refunded=provider_charge.amount_refunded,
            status=self._get_legacy_stripe_charge_status_from_provider_status(
                provider_charge.status
            ),
        )

    async def update_charge_after_payment_captured(
        self, provider_intent: ProviderPaymentIntent
    ) -> LegacyStripeCharge:
        charge = provider_intent.charges.data[0]
        return await self.payment_repo.update_legacy_stripe_charge_status(
            stripe_charge_id=charge.id, status=LegacyStripeChargeStatus(charge.status)
        )

    async def update_charge_after_payment_refunded(
        self, provider_refund: ProviderRefund
    ) -> LegacyStripeCharge:
        # The refund was for a specific amount.  Add that to the current refunded amount for the legacy stripe charge record.
        return await self.payment_repo.update_legacy_stripe_charge_add_to_amount_refunded(
            stripe_id=provider_refund.charge,
            additional_amount_refunded=provider_refund.amount,
            refunded_at=datetime.now(),
        )

    async def update_charge_after_payment_cancelled(
        self, provider_payment_intent: ProviderPaymentIntent
    ):
        provider_charges = provider_payment_intent.charges
        provider_charge = provider_charges.data[0]
        return await self.payment_repo.update_legacy_stripe_charge_refund(
            stripe_id=provider_charge.id,
            amount_refunded=provider_charge.amount_refunded,
            refunded_at=datetime.now(),
        )

    def _extract_error_reason_from_exception(
        self, creation_exception: CartPaymentCreateError
    ) -> str:
        if creation_exception.provider_decline_code:
            # Provider decline code is most specific error and is favored
            error_reason = creation_exception.provider_decline_code
        elif creation_exception.provider_error_code:
            # Provider error code is next most descriptive
            error_reason = creation_exception.provider_error_code
        elif (
            creation_exception.error_code
            == PayinErrorCode.PAYMENT_INTENT_CREATE_STRIPE_ERROR
        ):
            # An error was received from stripe, but we still lack more detailed fields above.
            if creation_exception.has_provider_error_details:
                # Error details were found, but no specific info was extracted.
                error_reason = "empty_error_reason"
            else:
                # Error details not found.  Default to generic message reflecting stripe usage.
                error_reason = "generic_stripe_api_error"
        else:
            # Fallback to generic error message
            error_reason = "generic_exception"

        return error_reason

    async def mark_charge_as_failed(
        self,
        stripe_charge: LegacyStripeCharge,
        creation_exception: CartPaymentCreateError,
    ) -> LegacyStripeCharge:
        return await self.payment_repo.update_legacy_stripe_charge_error_details(
            id=stripe_charge.id,
            stripe_id=creation_exception.provider_charge_id
            if creation_exception.provider_charge_id
            else f"stripeid_lost_{str(uuid.uuid4())}",
            status=LegacyStripeChargeStatus.FAILED,
            error_reason=self._extract_error_reason_from_exception(creation_exception),
        )

    async def list_cart_payments(
        self,
        dd_consumer_id: int,
        active_only: bool,
        sort_by: CartPaymentSortKey,
        created_at_gte: datetime = None,
        created_at_lte: datetime = None,
    ) -> CartPaymentList:
        cart_payments: List[
            CartPayment
        ] = await self.payment_repo.get_cart_payments_by_dd_consumer_id(
            input=GetCartPaymentsByConsumerIdInput(dd_consumer_id=dd_consumer_id)
        )
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
        if active_only:
            cart_payments = list(
                filter(
                    lambda cart_payment: cart_payment.deleted_at is None, cart_payments
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


class IdempotencyKeyAction(Enum):
    CREATE = "create"
    ADJUST = "adjust"
    CANCEL = "cancel"
    REFUND = "refund"


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

    def is_adjustment_for_payment_intents(
        self,
        adjustment_history: PaymentIntentAdjustmentHistory,
        intent_list: List[PaymentIntent],
    ):
        return any(
            [
                payment_intent.id == adjustment_history.payment_intent_id
                for payment_intent in intent_list
            ]
        )

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

        # todo @Arjun please consumer this refund object and populate it to our control objects
        await self.stripe_async_client.refund_charge(
            country=country_code,
            request=refund_request,
            idempotency_key=refund_idempotency_key,
        )

        # we will retrieve latest payment_intent from stripe to maintain integrity
        # for underlying payment intent, charge and refund data
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
        reason: str,
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
                reason=reason,
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

        return updated_intent, updated_pgp_intent

    async def create_new_refund(
        self,
        refund_amount: int,
        cart_payment: CartPayment,
        payment_intent: PaymentIntent,
        idempotency_key: str,
    ) -> Tuple[Refund, PgpRefund]:
        async with self.payment_repo.payment_database_transaction():
            refund = await self.payment_repo.insert_refund(
                id=uuid.uuid4(),
                payment_intent_id=payment_intent.id,
                idempotency_key=idempotency_key,
                status=RefundStatus.PROCESSING,
                amount=refund_amount,
                reason=None,
            )

            pgp_refund = await self.payment_repo.insert_pgp_refund(
                id=uuid.uuid4(),
                refund_id=refund.id,
                idempotency_key=idempotency_key,
                status=RefundStatus.PROCESSING,
                pgp_code=PgpCode.STRIPE,
                amount=refund_amount,
                reason=None,
            )

            # Insert adjustment history record
            await self.payment_repo.insert_payment_intent_adjustment_history(
                id=uuid.uuid4(),
                payer_id=cart_payment.payer_id,
                payment_intent_id=payment_intent.id,
                amount=cart_payment.amount - refund_amount,
                amount_original=cart_payment.amount,
                amount_delta=-refund_amount,
                currency=payment_intent.currency,
                idempotency_key=idempotency_key,
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

            # Insert adjustment history record
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
        payer_id: uuid.UUID,
        payment_method_id: Optional[uuid.UUID],
        legacy_country_id: int,
        raw_payer: Optional[RawPayer] = None,
        dd_stripe_card_id: Optional[int] = None,
    ) -> Tuple[PgpPaymentInfo, LegacyPayment]:

        if not (payment_method_id or dd_stripe_card_id):
            raise ValueError(
                "At least one of payment_method_id and dd_stripe_card_id need to be specified"
            )

        raw_payment_method: RawPaymentMethod
        if payment_method_id:
            raw_payment_method = await self.payment_method_client.get_raw_payment_method(
                payer_id=payer_id,
                payer_id_type=PayerIdType.PAYER_ID,
                payment_method_id=payment_method_id,
                payment_method_id_type=PaymentMethodIdType.PAYMENT_METHOD_ID,
            )
        else:
            raw_payment_method = await self.payment_method_client.get_raw_payment_method(
                payer_id=payer_id,
                payer_id_type=PayerIdType.PAYER_ID,
                payment_method_id=str(not_none(dd_stripe_card_id)),
                payment_method_id_type=PaymentMethodIdType.DD_STRIPE_CARD_ID,
            )

        if not raw_payer:
            raw_payer = await self.payer_client.get_raw_payer(
                mixed_payer_id=payer_id,
                payer_reference_id_type=PayerReferenceIdType.PAYER_ID,
            )
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
        cart_payment: CartPayment,
        payment_intent: PaymentIntent,
        pgp_payment_intent: PgpPaymentIntent,
    ) -> CartPayment:
        """
        Populate fields within a CartPayment instance to be suitable for an API response body.
        Since CartPayment is a view on top of several models, it is necessary to synthesize info
        into a CartPayment instance from associated models.

        Arguments:
            cart_payment {CartPayment} -- The CartPayment instance to update.
            payment_intent {PaymentIntent} -- An associated PaymentIntent.
            pgp_payment_intent {PgpPaymentIntent} -- An associated PgpPaymentIntent.
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

        return cart_payment

    async def update_cart_payment_attributes(
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
        self.populate_cart_payment_for_response(
            updated_cart_payment, payment_intent, pgp_payment_intent
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
    ):
        self.log = log
        self.cart_payment_interface = cart_payment_interface
        self.legacy_payment_interface = legacy_payment_interface
        self.payer_client = payer_client

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
            refund, pgp_refund = await self.cart_payment_interface.create_new_refund(
                refund_amount=payment_intent.amount,
                cart_payment=cart_payment,
                payment_intent=payment_intent,
                idempotency_key=self.cart_payment_interface.get_idempotency_key_for_provider_call(
                    payment_intent.idempotency_key, IdempotencyKeyAction.REFUND
                ),
            )

            provider_refund = await self.cart_payment_interface.refund_provider_payment(
                refund=refund,
                payment_intent=payment_intent,
                pgp_payment_intent=pgp_payment_intent,
                reason=StripeRefundChargeRequest.RefundReason.REQUESTED_BY_CONSUMER,
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
            assert existing_payment_intents[0].payment_method_id
            try:
                pgp_payment_method, legacy_payment = await self.cart_payment_interface.get_pgp_payment_info_v1(
                    payer_id=cart_payment.payer_id,
                    payment_method_id=existing_payment_intents[0].payment_method_id,
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
                self.cart_payment_interface.populate_cart_payment_for_response(
                    cart_payment, existing_payment_intent, pgp_payment_intent
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
                )

            provider_refund = await self.cart_payment_interface.refund_provider_payment(
                refund=refund,
                payment_intent=refundable_intent,
                pgp_payment_intent=refundable_pgp_payment_intent,
                reason=StripeRefundChargeRequest.RefundReason.REQUESTED_BY_CONSUMER,
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
        existing_payment_intent = self.cart_payment_interface.filter_payment_intents_by_idempotency_key(
            payment_intents, idempotency_key
        )
        if existing_payment_intent:
            if self.cart_payment_interface.is_payment_intent_failed(
                payment_intent=existing_payment_intent
            ):
                # If there was an intent with the same idempotency key and it failed, return an error.
                # TODO support returning previous result based on idempotency key reuse.
                self.log.warning(
                    "[update_payment_for_legacy_charge] Reuse of idempotency key for failed payment intent",
                    idempotency_key=idempotency_key,
                )
                raise CartPaymentUpdateError(
                    error_code=PayinErrorCode.PAYMENT_INTENT_CREATE_FAILED_ERROR
                )
            # For any non failed state, return success
            self.log.info(
                "[update_payment_for_legacy_charge] Reuse of idempotency key for previous payment intent",
                idempotency_key=idempotency_key,
                payment_intent_id=existing_payment_intent.id,
            )
            existing_pgp_payment_intent = await self.cart_payment_interface.get_cart_payment_submission_pgp_intent(
                payment_intent=existing_payment_intent
            )
            return self.cart_payment_interface.populate_cart_payment_for_response(
                cart_payment=cart_payment,
                payment_intent=existing_payment_intent,
                pgp_payment_intent=existing_pgp_payment_intent,
            )
        else:
            # No payment intent with idempotency key.  Next check adjustment history, which may hold key from previous amount reduction.
            adjustment_history = await self.cart_payment_interface.get_payment_intent_adjustment(
                idempotency_key=idempotency_key
            )
            if adjustment_history:
                if not self.cart_payment_interface.is_adjustment_for_payment_intents(
                    adjustment_history, intent_list=payment_intents
                ):
                    self.log.error(
                        "[update_payment_for_legacy_charge] Reuse of idempotency key for used by another payment intent",
                        idempotency_key=idempotency_key,
                        payment_intent_id=adjustment_history.payment_intent_id,
                    )
                    raise CartPaymentUpdateError(
                        error_code=PayinErrorCode.CART_PAYMENT_IDEMPOTENCY_KEY_ERROR
                    )
                existing_payment_intent = self.cart_payment_interface.get_most_recent_intent(
                    intent_list=payment_intents
                )
                existing_pgp_payment_intent = await self.cart_payment_interface.get_cart_payment_submission_pgp_intent(
                    payment_intent=existing_payment_intent
                )
                return self.cart_payment_interface.populate_cart_payment_for_response(
                    cart_payment=cart_payment,
                    payment_intent=existing_payment_intent,
                    pgp_payment_intent=existing_pgp_payment_intent,
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
            payment_intents = await self.cart_payment_interface.get_cart_payment_intents(
                cart_payment
            )
            payment_intent = self.cart_payment_interface.get_most_recent_intent(
                payment_intents
            )
            pgp_payment_intent = await self.cart_payment_interface.get_cart_payment_submission_pgp_intent(
                payment_intent
            )

        updated_cart_payment = await self.cart_payment_interface.update_cart_payment_attributes(
            cart_payment=cart_payment,
            idempotency_key=idempotency_key,
            payment_intent=payment_intent,
            pgp_payment_intent=pgp_payment_intent,
            amount=amount,
            client_description=client_description,
        )
        return self.cart_payment_interface.populate_cart_payment_for_response(
            updated_cart_payment, payment_intent, pgp_payment_intent
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
        dd_stripe_card_id: Optional[int] = None,
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
        assert request_cart_payment.payment_method_id or dd_stripe_card_id

        # TODO: PAYIN-292 consolidate the process of fetching all required metadata to create a cart payment
        payer_reference_id: Union[uuid.UUID, str]
        payer_reference_id_type: PayerReferenceIdType

        if request_cart_payment.payer_id:
            payer_reference_id = request_cart_payment.payer_id
            payer_reference_id_type = PayerReferenceIdType.PAYER_ID
        elif request_cart_payment.payer_correlation_ids:
            payer_reference_id = (
                request_cart_payment.payer_correlation_ids.payer_reference_id
            )
            payer_reference_id_type = (
                request_cart_payment.payer_correlation_ids.payer_reference_id_type
            )
        else:
            raise ValueError(
                "at least one of payer_id or payer_reference_id should be specified"
            )

        raw_payer: RawPayer = await self.cart_payment_interface.payer_client.get_raw_payer(
            mixed_payer_id=payer_reference_id,
            payer_reference_id_type=payer_reference_id_type,
        )

        if not request_cart_payment.payer_id:
            request_cart_payment.payer_id = raw_payer.to_payer().id

        try:
            pgp_payment_info, legacy_payment = await self.cart_payment_interface.get_pgp_payment_info_v1(
                payer_id=not_none(request_cart_payment.payer_id),
                payment_method_id=request_cart_payment.payment_method_id,
                legacy_country_id=get_country_id_by_code(payment_country),
                raw_payer=raw_payer,
                dd_stripe_card_id=dd_stripe_card_id,
            )
        except PaymentMethodReadError as e:
            if e.error_code == PayinErrorCode.PAYMENT_METHOD_GET_NOT_FOUND:
                raise CartPaymentCreateError(
                    error_code=PayinErrorCode.CART_PAYMENT_PAYMENT_METHOD_NOT_FOUND
                ) from e
            raise

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
                        existing_cart_payment,
                        existing_payment_intent,
                        pgp_payment_intent,
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
            cart_payment, payment_intent, pgp_payment_intent
        )

        cart_payment.payer_correlation_ids = request_cart_payment.payer_correlation_ids

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
        active_only: bool,
        dd_consumer_id: int,
        sort_by: CartPaymentSortKey,
        created_at_gte: datetime = None,
        created_at_lte: datetime = None,
    ) -> CartPaymentList:
        return await self.legacy_payment_interface.list_cart_payments(
            dd_consumer_id=dd_consumer_id,
            created_at_gte=created_at_gte,
            created_at_lte=created_at_lte,
            active_only=active_only,
            sort_by=sort_by,
        )

    async def list_cart_payments(
        self,
        payer_id: str,
        active_only: bool,
        sort_by: CartPaymentSortKey,
        created_at_gte: datetime = None,
        created_at_lte: datetime = None,
    ) -> CartPaymentList:
        consumer_id = await self.payer_client.get_consumer_id_by_payer_id(
            payer_id=payer_id
        )
        if not consumer_id:
            self.log.exception("No valid consumer found for the input.")
            raise CartPaymentReadError(
                error_code=PayinErrorCode.CART_PAYMENT_DATA_INVALID
            )
        return await self.legacy_payment_interface.list_cart_payments(
            dd_consumer_id=consumer_id,
            created_at_gte=created_at_gte,
            created_at_lte=created_at_lte,
            active_only=active_only,
            sort_by=sort_by,
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


# TODO PAYIN-36 Decouple CommandoProcessor from CartPaymentProcessor
class CommandoProcessor(CartPaymentProcessor):
    """
    I'm sneaky
    """

    log: BoundLogger
    cart_payment_interface: CartPaymentInterface
    legacy_payment_interface: LegacyPaymentInterface
    cart_payment_repo: CartPaymentRepository

    def __init__(
        self,
        log: BoundLogger,
        cart_payment_interface: CartPaymentInterface,
        legacy_payment_interface: LegacyPaymentInterface,
        cart_payment_repo: CartPaymentRepository,
    ):
        self.log = log
        self.cart_payment_interface = cart_payment_interface
        self.legacy_payment_interface = legacy_payment_interface
        self.cart_payment_repo = cart_payment_repo
        super().__init__(
            log=log,
            cart_payment_interface=cart_payment_interface,
            legacy_payment_interface=legacy_payment_interface,
        )

    async def _associated_payment_intent_data(
        self, payment_intent: PaymentIntent
    ) -> Tuple[
        CartPayment,
        LegacyPayment,
        PgpPaymentIntent,
        LegacyConsumerCharge,
        LegacyStripeCharge,
    ]:
        cart_payment, legacy_payment = await self.cart_payment_repo.get_cart_payment_by_id_from_primary(
            cart_payment_id=payment_intent.cart_payment_id
        )

        pgp_payment_intent = await self.cart_payment_interface.get_cart_payment_submission_pgp_intent(
            payment_intent
        )

        legacy_consumer_charge, legacy_stripe_charge = await self.legacy_payment_interface.find_existing_payment_charge(
            charge_id=payment_intent.legacy_consumer_charge_id,
            idempotency_key=payment_intent.idempotency_key,
        )

        if (
            not cart_payment
            or not legacy_payment
            or not legacy_consumer_charge
            or not legacy_stripe_charge
        ):
            msg = "Could not find complete set of payment information for given payment intent"
            self.log.warning(msg, payment_intent_id=str(payment_intent.id))
            raise CommandoProcessingError(msg)

        return (
            cart_payment,
            legacy_payment,
            pgp_payment_intent,
            legacy_consumer_charge,
            legacy_stripe_charge,
        )

    async def fullfill_intent(
        self, payment_intent: PaymentIntent
    ) -> IntentFullfillmentResult:
        (
            cart_payment,
            legacy_payment,
            pgp_payment_intent,
            legacy_consumer_charge,
            legacy_stripe_charge,
        ) = await self._associated_payment_intent_data(payment_intent)

        if not pgp_payment_intent.customer_resource_id:
            msg = "Could not find customer_resource_id for given pgp payment intent"
            self.log.warning(msg, pgp_payment_intent_id=str(pgp_payment_intent.id))
            raise CommandoProcessingError(msg)

        pgp_payment_info = PgpPaymentInfo(
            pgp_payment_method_resource_id=PgpPaymentMethodResourceId(
                pgp_payment_intent.payment_method_resource_id
            ),
            pgp_payer_resource_id=PgpPayerResourceId(
                pgp_payment_intent.customer_resource_id
            ),
        )

        if cart_payment.payer_id:
            payer = await self.get_payer_by_id(cart_payment.payer_id)
            payer_country = CountryCode(payer.country)
        else:
            payer_country = get_country_code_by_id(legacy_consumer_charge.country_id)

        try:
            provider_payment_intent = await self.cart_payment_interface.submit_payment_to_provider(
                payer_country=payer_country,
                payment_intent=payment_intent,
                pgp_payment_intent=pgp_payment_intent,
                pgp_payment_info=pgp_payment_info,
                provider_description=cart_payment.client_description,
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
        # Also takes care of triggering immediate capture if needed.

        # update legacy values in db
        legacy_stripe_charge = await self.legacy_payment_interface.update_state_after_provider_submission(
            legacy_stripe_charge=legacy_stripe_charge,
            idempotency_key=payment_intent.idempotency_key,
            provider_payment_intent=provider_payment_intent,
        )

        # update payment_intent and pgp_payment_intent pair in db
        payment_intent, _ = await self.cart_payment_interface.update_state_after_provider_submission(
            payment_intent=payment_intent,
            pgp_payment_intent=pgp_payment_intent,
            provider_payment_intent=provider_payment_intent,
        )

        self.log.info(
            "Recoup attempted",
            payment_intent_id=payment_intent.id,
            status=payment_intent.status,
            amount=legacy_stripe_charge.amount,
        )
        return IntentFullfillmentResult(
            (payment_intent.status, legacy_stripe_charge.amount)
        )

    async def recoup(
        self, limit: Optional[int] = 10000, chunk_size: int = 100
    ) -> Tuple[int, List[IntentFullfillmentResult]]:
        """
        This may have to be called multiple times from ipython shell until we have re-couped everything.

        :param limit:
        :param chunk_size:
        :return:
        """
        pending_ps_payment_intents = await self.cart_payment_repo.get_payment_intents_paginated(
            status=IntentStatus.PENDING, limit=limit
        )
        total = 0
        results: List[IntentFullfillmentResult] = []
        for i in range(0, len(pending_ps_payment_intents), chunk_size):
            chunk = pending_ps_payment_intents[i : i + chunk_size]
            results.extend(
                await gather(
                    *[self.fullfill_intent(payment_intent=pi) for pi in chunk],
                    return_exceptions=True,
                )
            )
            total += len(results)
            self.log.info("Attempted to recoup payment_intents", amount=len(results))

        return total, results
