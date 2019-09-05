import uuid
from datetime import datetime

from app.commons.types import CurrencyType
from app.ledger.core.data_types import (
    InsertMxLedgerInput,
    InsertMxTransactionInput,
    InsertMxScheduledLedgerInput,
)
from app.ledger.core.types import (
    MxLedgerStateType,
    MxLedgerType,
    MxTransactionType,
    MxScheduledLedgerIntervalType,
)
from app.ledger.core.utils import (
    pacific_start_time_for_current_interval,
    pacific_end_time_for_current_interval,
)


async def prepare_mx_ledger(
    ledger_id,
    payment_account_id,
    ledger_type=MxLedgerType.SCHEDULED,
    currency=CurrencyType.USD,
    balance=2000,
    state=MxLedgerStateType.OPEN,
):
    mx_ledger_to_insert = InsertMxLedgerInput(
        id=ledger_id,
        type=ledger_type.value,
        currency=currency.value,
        state=state.value,
        balance=balance,
        payment_account_id=payment_account_id,
    )
    return mx_ledger_to_insert


async def prepare_mx_transaction(
    transaction_id,
    payment_account_id,
    ledger_id,
    idempotency_key=str(uuid.uuid4()),
    amount=2000,
    currency=CurrencyType.USD,
    target_type=MxTransactionType.MERCHANT_DELIVERY,
    routing_key=datetime.utcnow(),
):
    mx_transaction_to_insert = InsertMxTransactionInput(
        id=transaction_id,
        payment_account_id=payment_account_id,
        amount=amount,
        currency=currency.value,
        ledger_id=ledger_id,
        idempotency_key=idempotency_key,
        target_type=target_type.value,
        routing_key=routing_key,
    )
    return mx_transaction_to_insert


async def prepare_mx_scheduled_ledger(
    payment_account_id,
    ledger_id,
    scheduled_ledger_id,
    routing_key=None,
    closed_at=0,
    interval_type=MxScheduledLedgerIntervalType.WEEKLY,
    start_time=None,
    end_time=None,
):
    """
    if routing_key is not None, then mx_scheduled_ledger_repository cannot be None.
    """
    scheduled_ledger_request = InsertMxScheduledLedgerInput(
        id=scheduled_ledger_id,
        payment_account_id=payment_account_id,
        ledger_id=ledger_id,
        interval_type=interval_type,
        closed_at=closed_at,
        start_time=pacific_start_time_for_current_interval(routing_key, interval_type)
        if routing_key
        else start_time,
        end_time=pacific_end_time_for_current_interval(routing_key, interval_type)
        if routing_key
        else end_time,
    )
    return scheduled_ledger_request


def prepare_transaction_post_request(
    payment_account_id=str(uuid.uuid4()), routing_key=datetime(2019, 8, 1)
):
    request = {
        "payment_account_id": payment_account_id,
        "target_type": MxTransactionType.MERCHANT_DELIVERY.value,
        "amount": 3000,
        "currency": CurrencyType.USD.value,
        "idempotency_key": str(uuid.uuid4()),
        "routing_key": routing_key.isoformat(),
        "interval_type": MxScheduledLedgerIntervalType.WEEKLY.value,
        "target_id": "optional_target_id",
        "context": {"abc": 123, "def": 456},
        "metadata": {},
        "legacy_transaction_id": "optional_legacy_transaction_id",
    }
    return request
