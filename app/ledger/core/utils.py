from datetime import datetime, timedelta
from math import ceil
from typing import Any, Optional

from pytz import timezone

from app.ledger.core.mx_ledger.types import MxLedgerInternal
from app.ledger.core.mx_transaction.types import MxTransactionInternal
from app.ledger.core.types import MxScheduledLedgerIntervalType
from app.ledger.core.types import MxLedgerType


def to_mx_ledger(row: Any) -> MxLedgerInternal:
    return MxLedgerInternal(
        id=row.id,
        payment_account_id=row.payment_account_id,
        type=row.type,
        currency=row.currency,
        state=row.state,
        balance=row.balance,
        amount_paid=row.amount_paid,
        created_by_employee_id=row.created_by_employee_id,
        submitted_by_employee_id=row.submitted_by_employee_id,
        legacy_transfer_id=row.legacy_transfer_id,
        rolled_to_ledger_id=row.rolled_to_ledger_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        submitted_at=row.submitted_at,
        finalized_at=row.finalized_at,
    )


def to_mx_transaction(row: Any) -> MxTransactionInternal:
    return MxTransactionInternal(
        id=row.id,
        payment_account_id=row.payment_account_id,
        amount=row.amount,
        currency=row.currency,
        idempotency_key=row.idempotency_key,
        ledger_id=row.ledger_id,
        target_type=row.target_type,
        routing_key=row.routing_key,
        target_id=row.target_id,
        legacy_transaction_id=row.legacy_transaction_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        context=row.context,
        metadata=row.metadata,
    )


def pacific_start_time_for_current_interval(
    routing_key: datetime, interval: Optional[MxScheduledLedgerIntervalType]
) -> datetime:
    """
    Calculate the start_time(in UTC time but without tz info) for current interval based on given routing_key and interval
    The returned start_time represents Pacific start_time in UTC timezone
    :param routing_key: datetime, key to find the cur start_time
    :param interval: MxScheduledLedgerIntervalType,
    :return: start_time for current interval: datetime
    """
    interval_in_timedelta = (
        timedelta(days=7)
        if interval == MxScheduledLedgerIntervalType.WEEKLY
        else timedelta(days=1)
    )
    routing_key_utc = routing_key.astimezone(timezone("UTC"))
    base_timestamp = timezone("US/Pacific").localize(datetime(2019, 7, 1))
    num_intervals = ceil((routing_key_utc - base_timestamp) / interval_in_timedelta)
    start_time = base_timestamp + interval_in_timedelta * (num_intervals - 1)
    return start_time.astimezone(timezone("UTC")).replace(tzinfo=None)


def pacific_end_time_for_current_interval(
    routing_key: datetime, interval: Optional[MxScheduledLedgerIntervalType]
) -> datetime:
    interval_in_timedelta = (
        timedelta(days=7)
        if interval == MxScheduledLedgerIntervalType.WEEKLY
        else timedelta(days=1)
    )
    routing_key_utc = routing_key.astimezone(timezone("UTC"))
    base_timestamp = timezone("US/Pacific").localize(datetime(2019, 7, 1))
    num_intervals = ceil((routing_key_utc - base_timestamp) / interval_in_timedelta)
    start_time = base_timestamp + interval_in_timedelta * num_intervals
    return start_time.astimezone(timezone("UTC")).replace(tzinfo=None)


MX_LEDGER_TYPE_MUST_HAVE_MX_SCHEDULED_LEDGER = [MxLedgerType.SCHEDULED]
