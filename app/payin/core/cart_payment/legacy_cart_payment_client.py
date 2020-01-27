import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from fastapi import Depends

from app.commons.context.app_context import AppContext, get_global_app_context
from app.commons.context.req_context import (
    get_context_from_req,
    get_stripe_async_client_from_req,
    ReqContext,
)
from app.commons.core.errors import DBOperationError
from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.commons.providers.stripe.stripe_models import (
    PaymentIntent as ProviderPaymentIntent,
    Refund as ProviderRefund,
)
from app.commons.types import CountryCode, Currency, LegacyCountryId
from app.commons.utils.legacy_utils import get_country_id_by_code
from app.payin.core.cart_payment.model import (
    CartPayment,
    CorrelationIds,
    LegacyConsumerCharge,
    LegacyPayment,
    LegacyStripeCharge,
)
from app.payin.core.cart_payment.types import LegacyStripeChargeStatus
from app.payin.core.exceptions import (
    CartPaymentCreateError,
    LegacyStripeChargeConcurrentAccessError,
    LegacyStripeChargeCouldNotBeUpdatedError,
    LegacyStripeChargeUpdateError,
    PayinErrorCode,
)
from app.payin.core.payer.types import DeletePayerRedactingText
from app.payin.repository.cart_payment_repo import (
    CartPaymentRepository,
    GetCartPaymentsByConsumerIdInput,
    GetLegacyConsumerChargeIdsByConsumerIdInput,
    UpdateLegacyStripeChargeErrorDetailsSetInput,
    UpdateLegacyStripeChargeErrorDetailsWhereInput,
    UpdateLegacyStripeChargeRemovePiiSetInput,
    UpdateLegacyStripeChargeRemovePiiWhereInput,
)


# TODO rename module to LegacyCartPaymentClient
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

    async def get_legacy_consumer_charge_ids_by_consumer_id(
        self, consumer_id: int
    ) -> List[int]:
        return await self.payment_repo.get_legacy_consumer_charge_ids_by_consumer_id(
            get_legacy_consumer_charge_ids_by_consumer_id_input=GetLegacyConsumerChargeIdsByConsumerIdInput(
                consumer_id=consumer_id
            )
        )

    async def get_legacy_stripe_charges_by_charge_id(
        self, charge_id: int
    ) -> List[LegacyStripeCharge]:
        return await self.payment_repo.get_legacy_stripe_charges_by_charge_id(
            charge_id=charge_id
        )

    async def update_legacy_stripe_charge_remove_pii(
        self, id: int
    ) -> Optional[LegacyStripeCharge]:
        try:
            return await self.payment_repo.update_legacy_stripe_charge_remove_pii(
                update_legacy_stripe_charge_remove_pii_where_input=UpdateLegacyStripeChargeRemovePiiWhereInput(
                    id=id
                ),
                update_legacy_stripe_charge_remove_pii_set_input=UpdateLegacyStripeChargeRemovePiiSetInput(
                    description=DeletePayerRedactingText.REDACTED
                ),
            )
        except DBOperationError as e:
            self.req_context.log.exception(
                "[update_legacy_stripe_charge_remove_pii] Error occurred with updating stripe charge",
                charge_id=id,
            )
            raise LegacyStripeChargeUpdateError(
                error_code=PayinErrorCode.LEGACY_STRIPE_CHARGE_UPDATE_DB_ERROR
            ) from e

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
        # Update the status of stripe_charge based on the provider intent.
        # We do not need to update amount_refunded here since we do that at cart payment adjustment time in order to preserve
        # correct behavior in DSJ, which does not have the concept of delayed capture.
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
        try:
            return await self.payment_repo.update_legacy_stripe_charge_error_details(
                update_legacy_stripe_charge_where_input=UpdateLegacyStripeChargeErrorDetailsWhereInput(
                    id=stripe_charge.id, previous_status=stripe_charge.status
                ),
                update_legacy_stripe_charge_set_input=UpdateLegacyStripeChargeErrorDetailsSetInput(
                    stripe_id=creation_exception.provider_charge_id
                    if creation_exception.provider_charge_id
                    else f"stripeid_lost_{str(uuid.uuid4())}",
                    status=LegacyStripeChargeStatus.FAILED,
                    error_reason=self._extract_error_reason_from_exception(
                        creation_exception
                    ),
                    updated_at=datetime.now(timezone.utc),
                ),
            )
        except LegacyStripeChargeCouldNotBeUpdatedError as e:
            self.req_context.log.error(
                "Legacy stripe charge could not be updated",
                stripe_charge_id=stripe_charge.id,
                stripe_id=stripe_charge.stripe_id,
                status=stripe_charge.status,
                error_reason=stripe_charge.error_reason,
            )
            raise LegacyStripeChargeConcurrentAccessError(
                error_code=PayinErrorCode.CART_PAYMENT_CONCURRENT_ACCESS_ERROR
            ) from e

    async def list_cart_payments_by_dd_consumer_id(
        self, dd_consumer_id: int
    ) -> List[CartPayment]:
        cart_payments: List[
            CartPayment
        ] = await self.payment_repo.get_cart_payments_by_dd_consumer_id(
            input=GetCartPaymentsByConsumerIdInput(dd_consumer_id=dd_consumer_id)
        )
        return cart_payments
