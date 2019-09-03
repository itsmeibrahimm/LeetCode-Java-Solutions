from datetime import datetime, timedelta
from math import ceil
from typing import Any, Optional

from pytz import timezone

from app.ledger.core.mx_ledger.model import MxLedger
from app.ledger.core.mx_transaction.model import MxTransaction
from app.ledger.core.types import MxScheduledLedgerIntervalType


def to_mx_ledger(row: Any) -> MxLedger:
    return MxLedger.from_orm(row)


def to_mx_transaction(row: Any) -> MxTransaction:
    return MxTransaction.from_orm(row)


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
