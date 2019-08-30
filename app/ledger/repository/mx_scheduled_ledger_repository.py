from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from pytz import timezone
from math import ceil
from typing import Optional

from sqlalchemy import and_

from app.ledger.core.data_types import (
    InsertMxScheduledLedgerInput,
    InsertMxScheduledLedgerOutput,
    GetMxScheduledLedgerInput,
    GetMxScheduledLedgerOutput,
    GetMxScheduledLedgerByAccountInput,
)
from app.ledger.core.types import MxScheduledLedgerIntervalType, MxLedgerStateType
from app.ledger.models.paymentdb import mx_scheduled_ledgers, mx_ledgers
from app.ledger.repository.base import LedgerDBRepository


class MxScheduledLedgerRepositoryInterface:
    @abstractmethod
    async def insert_mx_scheduled_ledger(
        self, request: InsertMxScheduledLedgerInput
    ) -> InsertMxScheduledLedgerOutput:
        ...

    @abstractmethod
    async def get_open_mx_scheduled_ledger_for_period(
        self, request: GetMxScheduledLedgerInput
    ) -> Optional[GetMxScheduledLedgerOutput]:
        ...

    @abstractmethod
    async def get_open_mx_scheduled_ledger_for_payment_account(
        self, request: GetMxScheduledLedgerByAccountInput
    ) -> Optional[GetMxScheduledLedgerOutput]:
        ...


@dataclass
class MxScheduledLedgerRepository(
    MxScheduledLedgerRepositoryInterface, LedgerDBRepository
):
    async def insert_mx_scheduled_ledger(
        self, request: InsertMxScheduledLedgerInput
    ) -> InsertMxScheduledLedgerOutput:
        stmt = (
            mx_scheduled_ledgers.table.insert()
            .values(request.dict(skip_defaults=True))
            .returning(*mx_scheduled_ledgers.table.columns.values())
        )
        row = await self.payment_database.master().fetch_one(stmt)
        assert row
        return InsertMxScheduledLedgerOutput.from_row(row)

    async def get_open_mx_scheduled_ledger_for_period(
        self, request: GetMxScheduledLedgerInput
    ) -> Optional[GetMxScheduledLedgerOutput]:
        """
        Get mx_scheduled_ledger with given payment_account_id, routing_key, interval_type and corresponding open mx ledger
        Filter specific start_time and end_time to avoid multiple existing scheduled ledger with same start_time
        :param request: GetMxScheduledLedgerInput
        :return: GetMxScheduledLedgerOutput
        """
        stmt = mx_scheduled_ledgers.table.select().where(
            and_(
                mx_scheduled_ledgers.payment_account_id
                == request.payment_account_id,  # noqa: W503
                mx_scheduled_ledgers.start_time
                == self.pacific_start_time_for_current_interval(  # noqa: W503
                    request.routing_key, request.interval_type
                ),
                mx_scheduled_ledgers.end_time
                == self.pacific_end_time_for_current_interval(  # noqa: W503
                    request.routing_key, request.interval_type
                ),
                mx_ledgers.state == MxLedgerStateType.OPEN,
                mx_ledgers.table.c.id == mx_scheduled_ledgers.ledger_id,
            )
        )
        row = await self.payment_database.master().fetch_one(stmt)
        return GetMxScheduledLedgerOutput.from_row(row) if row else None

    async def get_open_mx_scheduled_ledger_for_payment_account(
        self, request: GetMxScheduledLedgerByAccountInput
    ) -> Optional[GetMxScheduledLedgerOutput]:
        """
        Get the first mx_scheduled_ledger with given payment_account_id and also 0 for closed_at value, and order by
        (end_time, start_time)
        :param request: GetMxScheduledLedgerByAccountInput
        :return: GetMxScheduledLedgerOutput
        """
        stmt = (
            mx_scheduled_ledgers.table.select()
            .where(
                and_(
                    mx_scheduled_ledgers.payment_account_id
                    == request.payment_account_id,
                    mx_scheduled_ledgers.closed_at == 0,
                )
            )
            .order_by(
                mx_scheduled_ledgers.end_time.asc(),
                mx_scheduled_ledgers.start_time.asc(),
            )
        )
        row = await self.payment_database.master().fetch_one(stmt)
        return GetMxScheduledLedgerOutput.from_row(row) if row else None

    def pacific_start_time_for_current_interval(
        self, routing_key: datetime, interval: Optional[MxScheduledLedgerIntervalType]
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
        self, routing_key: datetime, interval: Optional[MxScheduledLedgerIntervalType]
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
