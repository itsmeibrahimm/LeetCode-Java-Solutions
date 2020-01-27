from asyncio import gather
from typing import List, NewType, Optional, Tuple

from structlog.stdlib import BoundLogger

from app.commons.types import CountryCode
from app.commons.utils.legacy_utils import get_country_code_by_id
from app.payin.core.cart_payment.cart_payment_client import CartPaymentInterface
from app.payin.core.cart_payment.legacy_cart_payment_client import (
    LegacyPaymentInterface,
)
from app.payin.core.cart_payment.processor import CartPaymentProcessor
from app.payin.core.cart_payment.model import (
    CartPayment,
    PaymentIntent,
    LegacyPayment,
    LegacyConsumerCharge,
    LegacyStripeCharge,
    PgpPaymentIntent,
)

from app.payin.core.cart_payment.types import IntentStatus

from app.payin.core.exceptions import CartPaymentCreateError, CommandoProcessingError
from app.payin.core.payment_method.types import PgpPaymentInfo
from app.payin.core.types import PgpPayerResourceId, PgpPaymentMethodResourceId

from app.payin.repository.cart_payment_repo import CartPaymentRepository

IntentFullfillmentResult = NewType(
    "IntentFullfillmentResult", Tuple[str, Optional[int]]
)


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
