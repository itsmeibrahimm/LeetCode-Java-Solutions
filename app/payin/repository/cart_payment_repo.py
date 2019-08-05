from dataclasses import dataclass
from gino import GinoConnection
from typing import Any, List, Optional
from typing_extensions import final
from uuid import UUID

from app.payin.core.cart_payment.model import (
    CartPayment,
    CartMetadata,
    PaymentIntent,
    PgpPaymentIntent,
)
from app.payin.core.cart_payment.types import (
    PaymentIntentStatus,
    PgpPaymentIntentStatus,
)
from app.payin.models.paymentdb import (
    cart_payments,
    payment_intents,
    pgp_payment_intents,
)
from app.payin.repository.base import PayinDBRepository


@final
@dataclass
class CartPaymentRepository(PayinDBRepository):
    async def insert_cart_payment(
        self,
        connection: GinoConnection,
        id: UUID,
        payer_id: str,
        type: str,
        reference_id: int,
        reference_ct_id: int,
        legacy_consumer_id: Optional[int],
        amount_original: int,
        amount_total: int,
    ) -> CartPayment:
        data = {
            cart_payments.id: id,
            cart_payments.payer_id: payer_id,
            cart_payments.type: type,
            cart_payments.reference_id: reference_id,
            cart_payments.reference_ct_id: reference_ct_id,
            cart_payments.legacy_consumer_id: legacy_consumer_id,
            cart_payments.amount_original: amount_original,
            cart_payments.amount_total: amount_total,
        }

        statement = (
            cart_payments.table.insert()
            .values(data)
            .returning(*cart_payments.table.columns.values())
        )

        row = await connection.first(statement)
        return self.to_cart_payment(row)

    def to_cart_payment(self, row: Any) -> CartPayment:
        # TODO fill in additional fields
        return CartPayment(
            id=row[cart_payments.id],
            payer_id=row[cart_payments.payer_id],
            amount=row[cart_payments.amount_total],
            capture_method="todo",
            payment_method_id="todo",
            client_description=row[cart_payments.client_description],
            cart_metadata=CartMetadata(
                reference_id=row[cart_payments.reference_id],
                ct_reference_id=row[cart_payments.reference_ct_id],
                type=row[cart_payments.type],
            ),
            created_at=row[cart_payments.created_at],
            updated_at=row[cart_payments.updated_at],
        )

    async def get_cart_payment_by_id(self, cart_payment_id: UUID) -> CartPayment:
        statement = cart_payments.table.select().where(
            cart_payments.id == cart_payment_id
        )
        async with self.payment_database.master().acquire() as connection:  # type: GinoConnection
            row = await connection.first(statement)

        return self.to_cart_payment(row)

    async def insert_payment_intent(
        self,
        connection: GinoConnection,
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
        }

        statement = (
            payment_intents.table.insert()
            .values(data)
            .returning(*payment_intents.table.columns.values())
        )

        row = await connection.first(statement)
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
            status=PaymentIntentStatus(row[payment_intents.status]),
            statement_descriptor=row[payment_intents.statement_descriptor],
            created_at=row[payment_intents.created_at],
            updated_at=row[payment_intents.updated_at],
            captured_at=row[payment_intents.captured_at],
            cancelled_at=row[payment_intents.cancelled_at],
        )

    async def update_payment_intent_status(
        self, connection: GinoConnection, id: UUID, status: str
    ) -> None:
        statement = (
            payment_intents.table.update()
            .where(payment_intents.id == id)
            .values(status=status)
        )

        await connection.first(statement)

    async def get_payment_intent_for_idempotency_key(
        self, idempotency_key: str
    ) -> Optional[PaymentIntent]:
        statement = payment_intents.table.select().where(
            payment_intents.idempotency_key == idempotency_key
        )
        async with self.payment_database.master().acquire() as connection:  # type: GinoConnection
            row = await connection.first(statement)

        if not row:
            return None

        return self.to_payment_intent(row)

    async def insert_pgp_payment_intent(
        self,
        connection: GinoConnection,
        id: UUID,
        payment_intent_id: UUID,
        idempotency_key: str,
        provider: str,
        payment_method_resource_id: str,
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

        row = await connection.first(statement)
        return self.to_pgp_payment_intent(row)

    async def update_pgp_payment_intent(
        self,
        connection: GinoConnection,
        id: UUID,
        status: str,
        provider_intent_id: str,
        amount: int,
        amount_capturable: int,
        amount_received: int,
        application_fee_amount: int,
    ) -> None:
        statement = (
            pgp_payment_intents.table.update()
            .where(pgp_payment_intents.id == id)
            .values(
                status=status,
                resource_id=provider_intent_id,
                amount=amount,
                amount_capturable=amount_capturable,
                amount_received=amount_received,
                application_fee_amount=application_fee_amount,
            )
        )

        await connection.first(statement)

    async def find_pgp_payment_intents(
        self, payment_intent_id: UUID
    ) -> List[PgpPaymentIntent]:
        statement = (
            pgp_payment_intents.table.select()
            .where(pgp_payment_intents.payment_intent_id == payment_intent_id)
            .order_by(pgp_payment_intents.created_at.asc())
        )
        async with self.payment_database.master().acquire() as connection:  # type: GinoConnection
            query_results = await connection.all(statement)

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
            status=PgpPaymentIntentStatus(row[pgp_payment_intents.status]),
            invoice_resource_id=row[pgp_payment_intents.invoice_resource_id],
            charge_resource_id=row[pgp_payment_intents.charge_resource_id],
            payment_method_resource_id=row[
                pgp_payment_intents.payment_method_resource_id
            ],
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
