from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Optional, Tuple, Dict, AsyncIterator
from uuid import UUID

from IPython.utils.tz import utcnow
from sqlalchemy import and_, select
from typing_extensions import final

from app.commons import tracing
from app.commons.database.query import paged_query
from app.payin.core.cart_payment.model import (
    CartPayment,
    PaymentIntent,
    PgpPaymentIntent,
    PaymentIntentAdjustmentHistory,
    PaymentCharge,
    PgpPaymentCharge,
    LegacyConsumerCharge,
    LegacyStripeCharge,
    LegacyPayment,
    CorrelationIds,
)
from app.payin.core.cart_payment.types import IntentStatus, ChargeStatus
from app.payin.core.exceptions import PaymentIntentCouldNotBeUpdatedError
from app.payin.models.maindb import consumer_charges, stripe_charges
from app.payin.models.paymentdb import (
    cart_payments,
    payment_intents,
    pgp_payment_intents,
    payment_intents_adjustment_history,
    payment_charges,
    pgp_payment_charges,
)
from app.payin.repository.base import PayinDBRepository


@final
@tracing.track_breadcrumb(repository_name="cart_payment")
@dataclass
class CartPaymentRepository(PayinDBRepository):
    async def insert_cart_payment(
        self,
        *,
        id: UUID,
        payer_id: Optional[UUID],
        client_description: Optional[str],
        reference_id: str,
        reference_type: str,
        legacy_consumer_id: Optional[int],
        amount_original: int,
        amount_total: int,
        delay_capture: bool,
        metadata: Optional[Dict[str, Any]],
        legacy_stripe_card_id: int,
        legacy_provider_customer_id: str,
        legacy_provider_payment_method_id: str,
        legacy_provider_card_id: str,
    ) -> CartPayment:
        data = {
            cart_payments.id: id,
            cart_payments.payer_id: payer_id,
            cart_payments.client_description: client_description,
            cart_payments.reference_id: reference_id,
            cart_payments.reference_type: reference_type,
            cart_payments.legacy_consumer_id: legacy_consumer_id,
            cart_payments.amount_original: amount_original,
            cart_payments.amount_total: amount_total,
            cart_payments.delay_capture: delay_capture,
            cart_payments.metadata: metadata,
            cart_payments.legacy_stripe_card_id: legacy_stripe_card_id,
            cart_payments.legacy_provider_customer_id: legacy_provider_customer_id,
            cart_payments.legacy_provider_payment_method_id: legacy_provider_payment_method_id,
            cart_payments.legacy_provider_card_id: legacy_provider_card_id,
        }

        statement = (
            cart_payments.table.insert()
            .values(data)
            .returning(*cart_payments.table.columns.values())
        )

        row = await self.payment_database.master().fetch_one(statement)
        return self.to_cart_payment(row)

    def to_cart_payment(self, row: Any) -> CartPayment:
        return CartPayment(
            id=row[cart_payments.id],
            payer_id=row[cart_payments.payer_id],
            amount=row[cart_payments.amount_total],
            capture_method=None,
            payment_method_id=None,
            client_description=row[cart_payments.client_description],
            correlation_ids=CorrelationIds(
                reference_id=row[cart_payments.reference_id],
                reference_type=row[cart_payments.reference_type],
            ),
            metadata=row[cart_payments.metadata],
            created_at=row[cart_payments.created_at],
            updated_at=row[cart_payments.updated_at],
            delay_capture=row[cart_payments.delay_capture],
        )

    def to_legacy_payment(self, row: Any) -> LegacyPayment:
        return LegacyPayment(
            dd_consumer_id=row[cart_payments.legacy_consumer_id],
            dd_stripe_card_id=row[cart_payments.legacy_stripe_card_id],
            stripe_customer_id=row[cart_payments.legacy_provider_customer_id],
            stripe_payment_method_id=row[
                cart_payments.legacy_provider_payment_method_id
            ],
            stripe_card_id=row[cart_payments.legacy_provider_card_id],
        )

    async def find_payment_intents_with_status(
        self, status: IntentStatus
    ) -> List[PaymentIntent]:
        statement = payment_intents.table.select().where(
            payment_intents.status == status
        )
        results = await self.payment_database.replica().fetch_all(statement)
        return [self.to_payment_intent(row) for row in results]

    async def find_payment_intents_that_require_capture(
        self, cutoff: datetime
    ) -> AsyncIterator[PaymentIntent]:
        """

        :param cutoff: The date after which capture_after should be
        :return:
        """
        query = payment_intents.table.select().where(
            and_(
                payment_intents.status == IntentStatus.REQUIRES_CAPTURE,
                payment_intents.capture_after >= cutoff,
            )
        )

        async for result in paged_query(
            self.payment_database.replica(), query, payment_intents.id
        ):
            yield self.to_payment_intent(result)

    async def find_payment_intents_in_capturing(
        self, older_than: datetime
    ) -> List[PaymentIntent]:
        """

        :param older_than: the date before which intent should have been updated
        :return:
        """
        statement = payment_intents.table.select().where(
            and_(
                payment_intents.status == IntentStatus.CAPTURING,
                payment_intents.updated_at <= older_than,
            )
        )
        results = await self.payment_database.replica().fetch_all(statement)
        return [self.to_payment_intent(row) for row in results]

    async def get_cart_payment_by_id(
        self, cart_payment_id: UUID
    ) -> Tuple[Optional[CartPayment], Optional[LegacyPayment]]:
        statement = cart_payments.table.select().where(
            cart_payments.id == cart_payment_id
        )
        row = await self.payment_database.master().fetch_one(statement)
        if not row:
            return None, None

        return self.to_cart_payment(row), self.to_legacy_payment(row)

    async def update_cart_payment_details(
        self, cart_payment_id: UUID, amount: int, client_description: Optional[str]
    ) -> CartPayment:
        statement = (
            cart_payments.table.update()
            .where(cart_payments.id == cart_payment_id)
            .values(amount_total=amount, client_description=client_description)
            .returning(*cart_payments.table.columns.values())
        )

        row = await self.payment_database.master().fetch_one(statement)
        return self.to_cart_payment(row)

    async def insert_payment_intent(
        self,
        id: UUID,
        cart_payment_id: UUID,
        idempotency_key: str,
        amount_initiated: int,
        amount: int,
        application_fee_amount: Optional[int],
        country: str,
        currency: str,
        capture_method: str,
        confirmation_method: str,
        status: str,
        statement_descriptor: Optional[str],
        capture_after: Optional[datetime],
        payment_method_id: Optional[UUID],
        metadata: Optional[Dict[str, Any]],
        legacy_consumer_charge_id: Optional[int],
    ) -> PaymentIntent:
        data = {
            payment_intents.id: id,
            payment_intents.cart_payment_id: cart_payment_id,
            payment_intents.idempotency_key: idempotency_key,
            payment_intents.amount_initiated: amount_initiated,
            payment_intents.amount: amount,
            payment_intents.application_fee_amount: application_fee_amount,
            payment_intents.country: country,
            payment_intents.currency: currency,
            payment_intents.capture_method: capture_method,
            payment_intents.confirmation_method: confirmation_method,
            payment_intents.status: status,
            payment_intents.statement_descriptor: statement_descriptor,
            payment_intents.capture_after: capture_after,
            payment_intents.payment_method_id: payment_method_id,
            payment_intents.metadata: metadata,
            payment_intents.legacy_consumer_charge_id: legacy_consumer_charge_id,
        }

        statement = (
            payment_intents.table.insert()
            .values(data)
            .returning(*payment_intents.table.columns.values())
        )

        row = await self.payment_database.master().fetch_one(statement)
        return self.to_payment_intent(row)

    def to_payment_intent(self, row: Any) -> PaymentIntent:
        return PaymentIntent(
            id=row[payment_intents.id],
            cart_payment_id=row[payment_intents.cart_payment_id],
            idempotency_key=row[payment_intents.idempotency_key],
            amount_initiated=row[payment_intents.amount_initiated],
            amount=row[payment_intents.amount],
            amount_capturable=row[payment_intents.amount_capturable],
            amount_received=row[payment_intents.amount_received],
            application_fee_amount=row[payment_intents.application_fee_amount],
            capture_method=row[payment_intents.capture_method],
            confirmation_method=row[payment_intents.confirmation_method],
            country=row[payment_intents.country],
            currency=row[payment_intents.currency],
            status=IntentStatus(row[payment_intents.status]),
            statement_descriptor=row[payment_intents.statement_descriptor],
            payment_method_id=row[payment_intents.payment_method_id],
            metadata=row[payment_intents.metadata],
            legacy_consumer_charge_id=row[payment_intents.legacy_consumer_charge_id],
            created_at=row[payment_intents.created_at],
            updated_at=row[payment_intents.updated_at],
            captured_at=row[payment_intents.captured_at],
            cancelled_at=row[payment_intents.cancelled_at],
            capture_after=row[payment_intents.capture_after],
        )

    async def update_payment_intent_status(
        self, id: UUID, new_status: str, previous_status: str
    ) -> PaymentIntent:
        """
        Updates a payment intent's status taking into account the previous status to prevent
        race conditions

        :param id:
        :param new_status:
        :param previous_status: the status from which the intent is transitioning
        :return:
        """
        statement = (
            payment_intents.table.update()
            .where(
                and_(
                    payment_intents.id == id, payment_intents.status == previous_status
                )
            )
            .values(status=new_status, updated_at=utcnow())
            .returning(*payment_intents.table.columns.values())
        )

        row = await self.payment_database.master().fetch_one(statement)

        # Record was not updated
        if not row:
            raise PaymentIntentCouldNotBeUpdatedError()

        return self.to_payment_intent(row)

    async def update_payment_intent(
        self, id: UUID, status: str, amount_received: int, captured_at: datetime
    ):
        statement = (
            payment_intents.table.update()
            .where(payment_intents.id == id)
            .values(
                status=status, amount_received=amount_received, captured_at=captured_at
            )
            .returning(*payment_intents.table.columns.values())
        )

        row = await self.payment_database.master().fetch_one(statement)
        return self.to_payment_intent(row)

    async def update_payment_intent_amount(
        self, id: UUID, amount: int
    ) -> PaymentIntent:
        statement = (
            payment_intents.table.update()
            .where(payment_intents.id == id)
            .values(amount=amount)
            .returning(*payment_intents.table.columns.values())
        )

        row = await self.payment_database.master().fetch_one(statement)
        return self.to_payment_intent(row)

    async def get_payment_intent_for_idempotency_key(
        self, idempotency_key: str
    ) -> Optional[PaymentIntent]:
        statement = payment_intents.table.select().where(
            payment_intents.idempotency_key == idempotency_key
        )
        row = await self.payment_database.replica().fetch_one(statement)

        if not row:
            return None

        return self.to_payment_intent(row)

    async def get_payment_intent_for_legacy_consumer_charge_id(
        self, charge_id: int
    ) -> Optional[PaymentIntent]:
        statement = payment_intents.table.select().where(
            payment_intents.legacy_consumer_charge_id == charge_id
        )
        row = await self.payment_database.replica().fetch_one(statement)

        if not row:
            return None

        return self.to_payment_intent(row)

    async def get_payment_intents_for_cart_payment(
        self, cart_payment_id: UUID
    ) -> List[PaymentIntent]:
        statement = payment_intents.table.select().where(
            payment_intents.cart_payment_id == cart_payment_id
        )
        results = await self.payment_database.replica().fetch_all(statement)

        return [self.to_payment_intent(row) for row in results]

    async def insert_pgp_payment_intent(
        self,
        id: UUID,
        payment_intent_id: UUID,
        idempotency_key: str,
        provider: str,
        payment_method_resource_id: str,
        customer_resource_id: Optional[str],
        currency: str,
        amount: int,
        application_fee_amount: Optional[int],
        payout_account_id: Optional[str],
        capture_method: str,
        confirmation_method: str,
        status: str,
        statement_descriptor: Optional[str],
    ) -> PgpPaymentIntent:
        data = {
            pgp_payment_intents.id: id,
            pgp_payment_intents.payment_intent_id: payment_intent_id,
            pgp_payment_intents.idempotency_key: idempotency_key,
            pgp_payment_intents.provider: provider,
            pgp_payment_intents.payment_method_resource_id: payment_method_resource_id,
            pgp_payment_intents.customer_resource_id: customer_resource_id,
            pgp_payment_intents.currency: currency,
            pgp_payment_intents.amount: amount,
            pgp_payment_intents.application_fee_amount: application_fee_amount,
            pgp_payment_intents.payout_account_id: payout_account_id,
            pgp_payment_intents.capture_method: capture_method,
            pgp_payment_intents.confirmation_method: confirmation_method,
            pgp_payment_intents.status: status,
            pgp_payment_intents.statement_descriptor: statement_descriptor,
        }

        statement = (
            pgp_payment_intents.table.insert()
            .values(data)
            .returning(*pgp_payment_intents.table.columns.values())
        )

        row = await self.payment_database.master().fetch_one(statement)
        return self.to_pgp_payment_intent(row)

    async def update_pgp_payment_intent(
        self, id: UUID, status: str, resource_id: str, charge_resource_id: str
    ) -> PgpPaymentIntent:
        statement = (
            pgp_payment_intents.table.update()
            .where(pgp_payment_intents.id == id)
            .values(
                status=status,
                resource_id=resource_id,
                charge_resource_id=charge_resource_id,
            )
            .returning(*pgp_payment_intents.table.columns.values())
        )

        row = await self.payment_database.master().fetch_one(statement)
        return self.to_pgp_payment_intent(row)

    async def update_pgp_payment_intent_status(
        self, id: UUID, status: str
    ) -> PgpPaymentIntent:
        statement = (
            pgp_payment_intents.table.update()
            .where(pgp_payment_intents.id == id)
            .values(status=status)
            .returning(*pgp_payment_intents.table.columns.values())
        )

        row = await self.payment_database.master().fetch_one(statement)
        return self.to_pgp_payment_intent(row)

    async def update_pgp_payment_intent_amount(
        self, id: UUID, amount: int
    ) -> PgpPaymentIntent:
        statement = (
            pgp_payment_intents.table.update()
            .where(pgp_payment_intents.id == id)
            .values(amount=amount)
            .returning(*pgp_payment_intents.table.columns.values())
        )

        row = await self.payment_database.master().fetch_one(statement)
        return self.to_pgp_payment_intent(row)

    async def find_pgp_payment_intents(
        self, payment_intent_id: UUID
    ) -> List[PgpPaymentIntent]:
        statement = (
            pgp_payment_intents.table.select()
            .where(pgp_payment_intents.payment_intent_id == payment_intent_id)
            .order_by(pgp_payment_intents.created_at.asc())
        )
        query_results = await self.payment_database.replica().fetch_all(statement)

        matched_intents = []
        for row in query_results:
            matched_intents.append(self.to_pgp_payment_intent(row))
        return matched_intents

    def to_pgp_payment_intent(self, row: Any) -> PgpPaymentIntent:
        return PgpPaymentIntent(
            id=row[pgp_payment_intents.id],
            payment_intent_id=row[pgp_payment_intents.payment_intent_id],
            idempotency_key=row[pgp_payment_intents.idempotency_key],
            provider=row[pgp_payment_intents.provider],
            resource_id=row[pgp_payment_intents.resource_id],
            status=IntentStatus(row[pgp_payment_intents.status]),
            invoice_resource_id=row[pgp_payment_intents.invoice_resource_id],
            charge_resource_id=row[pgp_payment_intents.charge_resource_id],
            payment_method_resource_id=row[
                pgp_payment_intents.payment_method_resource_id
            ],
            customer_resource_id=row[pgp_payment_intents.customer_resource_id],
            currency=row[pgp_payment_intents.currency],
            amount=row[pgp_payment_intents.amount],
            amount_capturable=row[pgp_payment_intents.amount_capturable],
            amount_received=row[pgp_payment_intents.amount_received],
            application_fee_amount=row[pgp_payment_intents.application_fee_amount],
            capture_method=row[pgp_payment_intents.capture_method],
            confirmation_method=row[pgp_payment_intents.confirmation_method],
            payout_account_id=row[pgp_payment_intents.payout_account_id],
            created_at=row[pgp_payment_intents.created_at],
            updated_at=row[pgp_payment_intents.updated_at],
            captured_at=row[pgp_payment_intents.captured_at],
            cancelled_at=row[pgp_payment_intents.cancelled_at],
        )

    async def get_intent_pair_by_provider_charge_id(
        self, provider_charge_id: str
    ) -> Tuple[Optional[PaymentIntent], Optional[PgpPaymentIntent]]:
        join_statement = payment_intents.table.join(
            pgp_payment_intents.table,
            payment_intents.id == pgp_payment_intents.payment_intent_id,
        )

        statement = (
            select([payment_intents.table, pgp_payment_intents.table], use_labels=True)
            .select_from(join_statement)
            .where(pgp_payment_intents.charge_resource_id == provider_charge_id)
        )

        row = await self.payment_database.replica().fetch_one(statement)
        if not row:
            return None, None

        row_intent = {
            k: row[f"payment_intents_{k.name}"] for k in payment_intents.table.columns
        }
        row_pgp_intent = {
            k: row[f"pgp_payment_intents_{k.name}"]
            for k in pgp_payment_intents.table.columns
        }

        return (
            self.to_payment_intent(row_intent),
            self.to_pgp_payment_intent(row_pgp_intent),
        )

    async def insert_payment_intent_adjustment_history(
        self,
        id: UUID,
        payer_id: Optional[UUID],
        payment_intent_id: UUID,
        amount: int,
        amount_original: int,
        amount_delta: int,
        currency: str,
    ) -> PaymentIntentAdjustmentHistory:
        data = {
            payment_intents_adjustment_history.id: id,
            payment_intents_adjustment_history.payer_id: payer_id,
            payment_intents_adjustment_history.payment_intent_id: payment_intent_id,
            payment_intents_adjustment_history.amount: amount,
            payment_intents_adjustment_history.amount_original: amount_original,
            payment_intents_adjustment_history.amount_delta: amount_delta,
            payment_intents_adjustment_history.currency: currency,
        }

        statement = (
            payment_intents_adjustment_history.table.insert()
            .values(data)
            .returning(*payment_intents_adjustment_history.table.columns.values())
        )

        row = await self.payment_database.master().fetch_one(statement)
        return self.to_payment_intent_adjustment_history(row)

    def to_payment_intent_adjustment_history(
        self, row: Any
    ) -> PaymentIntentAdjustmentHistory:
        return PaymentIntentAdjustmentHistory(
            id=row[payment_intents_adjustment_history.id],
            payer_id=row[payment_intents_adjustment_history.payer_id],
            payment_intent_id=row[payment_intents_adjustment_history.payment_intent_id],
            amount=row[payment_intents_adjustment_history.amount],
            amount_original=row[payment_intents_adjustment_history.amount_original],
            amount_delta=row[payment_intents_adjustment_history.amount_delta],
            currency=row[payment_intents_adjustment_history.currency],
            created_at=row[payment_intents_adjustment_history.created_at],
        )

    async def insert_payment_charge(
        self,
        id: UUID,
        payment_intent_id: UUID,
        provider: str,
        idempotency_key: str,
        status: str,
        currency: str,
        amount: int,
        amount_refunded: int,
        application_fee_amount: Optional[int],
        payout_account_id: Optional[str],
    ) -> PaymentCharge:
        data = {
            payment_charges.id: str(id),
            payment_charges.payment_intent_id: str(payment_intent_id),
            payment_charges.provider: provider,
            payment_charges.idempotency_key: idempotency_key,
            payment_charges.status: status,
            payment_charges.currency: currency,
            payment_charges.amount: amount,
            payment_charges.amount_refunded: amount_refunded,
            payment_charges.application_fee_amount: application_fee_amount,
            payment_charges.payout_account_id: payout_account_id,
        }

        statement = (
            payment_charges.table.insert()
            .values(data)
            .returning(*payment_charges.table.columns.values())
        )

        row = await self.payment_database.master().fetch_one(statement)
        return self.to_payment_charge(row)

    def to_payment_charge(self, row: Any) -> PaymentCharge:
        return PaymentCharge(
            id=row[payment_charges.id],
            payment_intent_id=row[payment_charges.payment_intent_id],
            provider=row[payment_charges.provider],
            idempotency_key=row[payment_charges.idempotency_key],
            status=ChargeStatus(row[payment_charges.status]),
            currency=row[payment_charges.currency],
            amount=row[payment_charges.amount],
            amount_refunded=row[payment_charges.amount_refunded],
            application_fee_amount=row[payment_charges.application_fee_amount],
            payout_account_id=row[payment_charges.payout_account_id],
            created_at=row[payment_charges.created_at],
            updated_at=row[payment_charges.updated_at],
            captured_at=row[payment_charges.captured_at],
            cancelled_at=row[payment_charges.cancelled_at],
        )

    async def update_payment_charge_status(
        self, payment_intent_id: UUID, status: str
    ) -> PaymentCharge:
        # We expect a 1-1 relationship between intent and charge for our use cases.
        # As an optimization, support updating based on intent_id, which avoids an extra
        # round trip to fetch the record to update.
        statement = (
            payment_charges.table.update()
            .where(payment_charges.payment_intent_id == payment_intent_id)
            .values(status=status)
            .returning(*payment_charges.table.columns.values())
        )

        row = await self.payment_database.master().fetch_one(statement)
        return self.to_payment_charge(row)

    async def update_payment_charge(
        self, payment_intent_id: UUID, status: str, amount_refunded: int
    ) -> PaymentCharge:
        statement = (
            payment_charges.table.update()
            .where(payment_charges.payment_intent_id == payment_intent_id)
            .values(status=status, amount_refunded=amount_refunded)
            .returning(*payment_charges.table.columns.values())
        )

        row = await self.payment_database.master().fetch_one(statement)
        return self.to_payment_charge(row)

    async def update_payment_charge_amount(
        self, payment_intent_id: UUID, amount: int
    ) -> PaymentCharge:
        statement = (
            payment_charges.table.update()
            .where(payment_charges.payment_intent_id == payment_intent_id)
            .values(amount=amount)
            .returning(*payment_charges.table.columns.values())
        )

        row = await self.payment_database.master().fetch_one(statement)
        return self.to_payment_charge(row)

    async def insert_pgp_payment_charge(
        self,
        id: UUID,
        payment_charge_id: UUID,
        provider: str,
        idempotency_key: str,
        status: str,
        currency: str,
        amount: int,
        amount_refunded: int,
        application_fee_amount: Optional[int],
        payout_account_id: Optional[str],
        resource_id: Optional[str],
        intent_resource_id: Optional[str],
        invoice_resource_id: Optional[str],
        payment_method_resource_id: Optional[str],
    ) -> PgpPaymentCharge:
        data = {
            pgp_payment_charges.id: id,
            pgp_payment_charges.payment_charge_id: payment_charge_id,
            pgp_payment_charges.provider: provider,
            pgp_payment_charges.idempotency_key: idempotency_key,
            pgp_payment_charges.status: status,
            pgp_payment_charges.currency: currency,
            pgp_payment_charges.amount: amount,
            pgp_payment_charges.amount_refunded: amount_refunded,
            pgp_payment_charges.application_fee_amount: application_fee_amount,
            pgp_payment_charges.payout_account_id: payout_account_id,
            pgp_payment_charges.resource_id: resource_id,
            pgp_payment_charges.intent_resource_id: intent_resource_id,
            pgp_payment_charges.invoice_resource_id: invoice_resource_id,
            pgp_payment_charges.payment_method_resource_id: payment_method_resource_id,
        }

        statement = (
            pgp_payment_charges.table.insert()
            .values(data)
            .returning(*pgp_payment_charges.table.columns.values())
        )

        row = await self.payment_database.master().fetch_one(statement)
        return self.to_pgp_payment_charge(row)

    def to_pgp_payment_charge(self, row: Any) -> PgpPaymentCharge:
        return PgpPaymentCharge(
            id=row[pgp_payment_charges.id],
            payment_charge_id=row[pgp_payment_charges.payment_charge_id],
            provider=row[pgp_payment_charges.provider],
            idempotency_key=row[pgp_payment_charges.idempotency_key],
            status=ChargeStatus(row[pgp_payment_charges.status]),
            currency=row[pgp_payment_charges.currency],
            amount=row[pgp_payment_charges.amount],
            amount_refunded=row[pgp_payment_charges.amount_refunded],
            application_fee_amount=row[pgp_payment_charges.application_fee_amount],
            payout_account_id=row[pgp_payment_charges.payout_account_id],
            resource_id=row[pgp_payment_charges.resource_id],
            intent_resource_id=row[pgp_payment_charges.intent_resource_id],
            invoice_resource_id=row[pgp_payment_charges.invoice_resource_id],
            payment_method_resource_id=row[
                pgp_payment_charges.payment_method_resource_id
            ],
            created_at=row[pgp_payment_charges.created_at],
            updated_at=row[pgp_payment_charges.updated_at],
            captured_at=row[pgp_payment_charges.captured_at],
            cancelled_at=row[pgp_payment_charges.cancelled_at],
        )

    async def update_pgp_payment_charge(
        self, payment_charge_id: UUID, status: str, amount: int, amount_refunded: int
    ) -> PgpPaymentCharge:
        # We expect a 1-1 relationship between charge and pgp_charge for our use cases.
        # As an optimization, support updating based on charge_id, which avoids an extra
        # round trip to fetch the record to update.
        statement = (
            pgp_payment_charges.table.update()
            .where(pgp_payment_charges.payment_charge_id == str(payment_charge_id))
            .values(status=status, amount=amount, amount_refunded=amount_refunded)
            .returning(*pgp_payment_charges.table.columns.values())
        )

        row = await self.payment_database.master().fetch_one(statement)
        return self.to_pgp_payment_charge(row)

    async def update_pgp_payment_charge_amount(
        self, payment_charge_id: UUID, amount: int
    ) -> PgpPaymentCharge:
        statement = (
            pgp_payment_charges.table.update()
            .where(pgp_payment_charges.payment_charge_id == str(payment_charge_id))
            .values(amount=amount)
            .returning(*pgp_payment_charges.table.columns.values())
        )

        row = await self.payment_database.master().fetch_one(statement)
        return self.to_pgp_payment_charge(row)

    async def update_pgp_payment_charge_status(
        self, payment_charge_id: UUID, status: str
    ) -> PgpPaymentCharge:
        statement = (
            pgp_payment_charges.table.update()
            .where(pgp_payment_charges.payment_charge_id == payment_charge_id)
            .values(status=status)
            .returning(*pgp_payment_charges.table.columns.values())
        )

        row = await self.payment_database.master().fetch_one(statement)
        return self.to_pgp_payment_charge(row)

    async def insert_legacy_consumer_charge(
        self,
        target_ct_id: int,
        target_id: int,
        consumer_id: int,
        idempotency_key: str,
        is_stripe_connect_based: bool,
        country_id: int,
        currency: str,
        stripe_customer_id: Optional[int],
        total: int,
        original_total: int,
    ) -> LegacyConsumerCharge:
        data = {
            consumer_charges.target_ct_id: target_ct_id,
            consumer_charges.target_id: target_id,
            consumer_charges.consumer_id: consumer_id,
            consumer_charges.idempotency_key: idempotency_key,
            consumer_charges.is_stripe_connect_based: is_stripe_connect_based,
            consumer_charges.country_id: country_id,
            consumer_charges.currency: currency,
            consumer_charges.stripe_customer_id: stripe_customer_id,
            consumer_charges.total: total,
            consumer_charges.original_total: original_total,
            consumer_charges.created_at: datetime.now(),
        }

        statement = (
            consumer_charges.table.insert()
            .values(data)
            .returning(*consumer_charges.table.columns.values())
        )

        row = await self.main_database.master().fetch_one(statement)
        return self.to_legacy_consumer_charge(row)

    def to_legacy_consumer_charge(self, row: Any) -> LegacyConsumerCharge:
        return LegacyConsumerCharge(
            id=row[consumer_charges.id],
            target_id=row[consumer_charges.target_id],
            target_ct_id=row[consumer_charges.target_ct_id],
            idempotency_key=row[consumer_charges.idempotency_key],
            is_stripe_connect_based=row[consumer_charges.is_stripe_connect_based],
            total=row[consumer_charges.total],
            original_total=row[consumer_charges.original_total],
            currency=row[consumer_charges.currency],
            country_id=row[consumer_charges.country_id],
            issue_id=row[consumer_charges.issue_id],
            stripe_customer_id=row[consumer_charges.stripe_customer_id],
            created_at=row[consumer_charges.created_at],
        )

    async def get_legacy_consumer_charge_by_id(
        self, id: int
    ) -> Optional[LegacyConsumerCharge]:
        statement = consumer_charges.table.select().where(consumer_charges.id == id)
        row = await self.main_database.replica().fetch_one(statement)
        if not row:
            return None
        return self.to_legacy_consumer_charge(row)

    async def insert_legacy_stripe_charge(
        self,
        stripe_id: str,
        card_id: Optional[int],
        charge_id: int,
        amount: int,
        amount_refunded: int,
        currency: str,
        status: str,
        idempotency_key: str,
        additional_payment_info: Optional[str],
        description: Optional[str],
    ) -> LegacyStripeCharge:
        data = {
            stripe_charges.stripe_id: stripe_id,
            stripe_charges.card_id: card_id,
            stripe_charges.charge_id: charge_id,
            stripe_charges.amount: amount,
            stripe_charges.amount_refunded: amount_refunded,
            stripe_charges.currency: currency,
            stripe_charges.status: status,
            stripe_charges.idempotency_key: idempotency_key,
            stripe_charges.additional_payment_info: additional_payment_info,
            stripe_charges.description: description,
            stripe_charges.created_at: datetime.now(),
            stripe_charges.updated_at: datetime.now(),
        }

        statement = (
            stripe_charges.table.insert()
            .values(data)
            .returning(*stripe_charges.table.columns.values())
        )

        row = await self.main_database.master().fetch_one(statement)
        return self.to_legacy_stripe_charge(row)

    def to_legacy_stripe_charge(self, row: Any) -> LegacyStripeCharge:
        return LegacyStripeCharge(
            id=row[stripe_charges.id],
            amount=row[stripe_charges.amount],
            amount_refunded=row[stripe_charges.amount_refunded],
            currency=row[stripe_charges.currency],
            status=row[stripe_charges.status],
            error_reason=row[stripe_charges.error_reason],
            additional_payment_info=row[stripe_charges.additional_payment_info],
            description=row[stripe_charges.description],
            idempotency_key=row[stripe_charges.idempotency_key],
            card_id=row[stripe_charges.card_id],
            charge_id=row[stripe_charges.charge_id],
            stripe_id=row[stripe_charges.stripe_id],
            created_at=row[stripe_charges.created_at],
            updated_at=row[stripe_charges.updated_at],
            refunded_at=row[stripe_charges.refunded_at],
        )

    async def update_legacy_stripe_charge_refund(
        self, stripe_id: str, amount_refunded: int, refunded_at: datetime
    ):
        statement = (
            stripe_charges.table.update()
            .where(stripe_charges.stripe_id == stripe_id)
            .values(amount_refunded=amount_refunded, refunded_at=refunded_at)
            .returning(*stripe_charges.table.columns.values())
        )

        row = await self.main_database.master().fetch_one(statement)
        return self.to_legacy_stripe_charge(row)

    async def update_legacy_stripe_charge_provider_details(
        self,
        id: int,
        stripe_id: str,
        amount: int,
        amount_refunded: int,
        currency: str,
        status: str,
    ):
        statement = (
            stripe_charges.table.update()
            .where(stripe_charges.id == id)
            .values(
                stripe_id=stripe_id,
                amount=amount,
                amount_refunded=amount_refunded,
                currency=currency,
                status=status,
            )
            .returning(*stripe_charges.table.columns.values())
        )

        row = await self.main_database.master().fetch_one(statement)
        return self.to_legacy_stripe_charge(row)

    async def update_legacy_stripe_charge_status(
        self, stripe_charge_id: str, status: str
    ):
        statement = (
            stripe_charges.table.update()
            .where(stripe_charges.stripe_id == stripe_charge_id)
            .values(status=status)
            .returning(*stripe_charges.table.columns.values())
        )

        row = await self.main_database.master().fetch_one(statement)
        return self.to_legacy_stripe_charge(row)

    async def get_legacy_stripe_charge_by_stripe_id(
        self, stripe_charge_id: str
    ) -> Optional[LegacyStripeCharge]:
        statement = stripe_charges.table.select().where(
            stripe_charges.stripe_id == stripe_charge_id
        )
        row = await self.main_database.replica().fetch_one(statement)
        return self.to_legacy_stripe_charge(row) if row else None

    async def get_legacy_stripe_charges_by_charge_id(
        self, charge_id: int
    ) -> List[LegacyStripeCharge]:
        statement = stripe_charges.table.select().where(
            stripe_charges.charge_id == charge_id
        )
        results = await self.main_database.replica().fetch_all(statement)
        return [self.to_legacy_stripe_charge(row) for row in results]
