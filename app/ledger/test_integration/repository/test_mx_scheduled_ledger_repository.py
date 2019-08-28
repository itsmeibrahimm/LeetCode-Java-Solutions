from datetime import datetime
import uuid

import pytest

from app.ledger.core.data_types import (
    GetMxScheduledLedgerInput,
    GetMxLedgerByAccountInput,
)
from app.ledger.core.types import MxScheduledLedgerIntervalType
from app.ledger.repository.mx_ledger_repository import MxLedgerRepository
from app.ledger.repository.mx_scheduled_ledger_repository import (
    MxScheduledLedgerRepository,
)
from app.ledger.test_integration.utils import (
    prepare_mx_ledger,
    prepare_mx_scheduled_ledger,
)


class TestMxLedgerRepository:
    pytestmark = [pytest.mark.asyncio]

    async def test_insert_mx_scheduled_ledger_success(
        self,
        mx_scheduled_ledger_repository: MxScheduledLedgerRepository,
        mx_ledger_repository: MxLedgerRepository,
    ):
        mx_scheduled_ledger_id = uuid.uuid4()
        ledger_id = uuid.uuid4()
        payment_account_id = str(uuid.uuid4())
        routing_key = datetime(2019, 8, 7)

        ledger_to_insert = await prepare_mx_ledger(
            ledger_id=ledger_id, payment_account_id=payment_account_id
        )
        await mx_ledger_repository.insert_mx_ledger(ledger_to_insert)

        mx_scheduled_ledger_to_insert = await prepare_mx_scheduled_ledger(
            mx_scheduled_ledger_repository=mx_scheduled_ledger_repository,
            scheduled_ledger_id=mx_scheduled_ledger_id,
            ledger_id=ledger_id,
            payment_account_id=payment_account_id,
            routing_key=routing_key,
        )
        mx_scheduled_ledger = await mx_scheduled_ledger_repository.insert_mx_scheduled_ledger(
            mx_scheduled_ledger_to_insert
        )

        assert mx_scheduled_ledger.id == mx_scheduled_ledger_id
        assert mx_scheduled_ledger.payment_account_id == payment_account_id
        assert mx_scheduled_ledger.ledger_id == ledger_id
        assert mx_scheduled_ledger.interval_type == MxScheduledLedgerIntervalType.WEEKLY
        assert mx_scheduled_ledger.start_time == datetime(2019, 8, 5, 7)
        assert mx_scheduled_ledger.end_time == datetime(2019, 8, 12, 7)

    async def test_get_open_mx_scheduled_ledger_for_period_success(
        self,
        mx_scheduled_ledger_repository: MxScheduledLedgerRepository,
        mx_ledger_repository: MxLedgerRepository,
    ):
        payment_account_id = str(uuid.uuid4())
        ledger_id = uuid.uuid4()
        mx_scheduled_ledger_id = uuid.uuid4()
        routing_key = datetime(2019, 8, 1)

        ledger_to_insert = await prepare_mx_ledger(
            ledger_id=ledger_id, payment_account_id=payment_account_id
        )
        await mx_ledger_repository.insert_mx_ledger(ledger_to_insert)

        mx_scheduled_ledger_to_insert = await prepare_mx_scheduled_ledger(
            mx_scheduled_ledger_repository=mx_scheduled_ledger_repository,
            scheduled_ledger_id=mx_scheduled_ledger_id,
            ledger_id=ledger_id,
            payment_account_id=payment_account_id,
            routing_key=routing_key,
        )
        await mx_scheduled_ledger_repository.insert_mx_scheduled_ledger(
            mx_scheduled_ledger_to_insert
        )

        request = GetMxScheduledLedgerInput(
            payment_account_id=payment_account_id,
            routing_key=routing_key,
            interval_type=MxScheduledLedgerIntervalType.WEEKLY.value,
        )
        mx_scheduled_ledger = await mx_scheduled_ledger_repository.get_open_mx_scheduled_ledger_for_period(
            request
        )
        assert mx_scheduled_ledger is not None
        assert mx_scheduled_ledger.id == mx_scheduled_ledger_id
        assert mx_scheduled_ledger.payment_account_id == payment_account_id
        assert mx_scheduled_ledger.ledger_id == ledger_id
        assert mx_scheduled_ledger.interval_type == MxScheduledLedgerIntervalType.WEEKLY
        assert mx_scheduled_ledger.start_time == datetime(2019, 7, 29, 7)
        assert mx_scheduled_ledger.end_time == datetime(2019, 8, 5, 7)

    async def test_get_open_mx_scheduled_ledger_for_period_not_exist_success(
        self,
        mx_scheduled_ledger_repository: MxScheduledLedgerRepository,
        mx_ledger_repository: MxLedgerRepository,
    ):
        payment_account_id = str(uuid.uuid4())
        ledger_id = uuid.uuid4()
        mx_scheduled_ledger_id = uuid.uuid4()
        routing_key = datetime(2019, 8, 7)

        ledger_to_insert = await prepare_mx_ledger(
            ledger_id=ledger_id, payment_account_id=payment_account_id
        )
        await mx_ledger_repository.insert_mx_ledger(ledger_to_insert)

        mx_scheduled_ledger_to_insert = await prepare_mx_scheduled_ledger(
            mx_scheduled_ledger_repository=mx_scheduled_ledger_repository,
            scheduled_ledger_id=mx_scheduled_ledger_id,
            ledger_id=ledger_id,
            payment_account_id=payment_account_id,
            routing_key=routing_key,
        )
        await mx_scheduled_ledger_repository.insert_mx_scheduled_ledger(
            mx_scheduled_ledger_to_insert
        )

        request = GetMxScheduledLedgerInput(
            payment_account_id=payment_account_id,
            routing_key=datetime(2019, 8, 1),
            interval_type=MxScheduledLedgerIntervalType.WEEKLY.value,
        )

        mx_scheduled_ledger = await mx_scheduled_ledger_repository.get_open_mx_scheduled_ledger_for_period(
            request
        )
        assert mx_scheduled_ledger is None

    async def test_get_open_mx_scheduled_ledger_for_period_mutiple_same_start_time_success(
        self,
        mx_scheduled_ledger_repository: MxScheduledLedgerRepository,
        mx_ledger_repository: MxLedgerRepository,
    ):
        # construct two scheduled_ledgers with same start_time and diff end_time along with ledgers
        payment_account_id = str(uuid.uuid4())
        ledger_id = uuid.uuid4()
        scheduled_ledger_id = uuid.uuid4()
        start_time = datetime(2019, 7, 29, 7)

        ledger_to_insert = await prepare_mx_ledger(
            ledger_id=ledger_id, payment_account_id=payment_account_id
        )
        await mx_ledger_repository.insert_mx_ledger(ledger_to_insert)

        mx_scheduled_ledger_to_insert = await prepare_mx_scheduled_ledger(
            scheduled_ledger_id=scheduled_ledger_id,
            ledger_id=ledger_id,
            payment_account_id=payment_account_id,
            start_time=start_time,
            end_time=datetime(2019, 8, 5, 7),
        )
        await mx_scheduled_ledger_repository.insert_mx_scheduled_ledger(
            mx_scheduled_ledger_to_insert
        )

        ledger_id = uuid.uuid4()
        scheduled_ledger_id = uuid.uuid4()
        ledger_to_insert = await prepare_mx_ledger(
            ledger_id=ledger_id, payment_account_id=payment_account_id
        )
        await mx_ledger_repository.insert_mx_ledger(ledger_to_insert)

        mx_scheduled_ledger_to_insert = await prepare_mx_scheduled_ledger(
            scheduled_ledger_id=scheduled_ledger_id,
            ledger_id=ledger_id,
            payment_account_id=payment_account_id,
            interval_type=MxScheduledLedgerIntervalType.DAILY,
            start_time=start_time,
            end_time=datetime(2019, 7, 30, 7),
        )
        await mx_scheduled_ledger_repository.insert_mx_scheduled_ledger(
            mx_scheduled_ledger_to_insert
        )

        # construct request and retrieve scheduled_ledger
        request = GetMxScheduledLedgerInput(
            payment_account_id=payment_account_id,
            routing_key=datetime(2019, 7, 30),
            interval_type=MxScheduledLedgerIntervalType.DAILY.value,
        )
        mx_scheduled_ledger_retrieved = await mx_scheduled_ledger_repository.get_open_mx_scheduled_ledger_for_period(
            request
        )
        assert mx_scheduled_ledger_retrieved is not None

        assert mx_scheduled_ledger_retrieved.id == scheduled_ledger_id
        assert mx_scheduled_ledger_retrieved.start_time == start_time
        assert mx_scheduled_ledger_retrieved.end_time == datetime(2019, 7, 30, 7)
        assert mx_scheduled_ledger_retrieved.payment_account_id == payment_account_id
        assert mx_scheduled_ledger_retrieved.payment_account_id == payment_account_id
        assert mx_scheduled_ledger_retrieved.ledger_id == ledger_id
        assert (
            mx_scheduled_ledger_retrieved.interval_type
            == MxScheduledLedgerIntervalType.DAILY
        )
        assert mx_scheduled_ledger_retrieved.closed_at == 0

    async def test_get_open_mx_scheduled_ledger_for_payment_account_success(
        self,
        mx_scheduled_ledger_repository: MxScheduledLedgerRepository,
        mx_ledger_repository: MxLedgerRepository,
    ):
        payment_account_id = str(uuid.uuid4())
        scheduled_ledger_id_1 = uuid.uuid4()
        scheduled_ledger_id_2 = uuid.uuid4()
        ledger_id_1 = uuid.uuid4()
        ledger_id_2 = uuid.uuid4()

        ledger_to_insert = await prepare_mx_ledger(
            ledger_id=ledger_id_1, payment_account_id=payment_account_id
        )
        await mx_ledger_repository.insert_mx_ledger(ledger_to_insert)
        mx_scheduled_ledger_to_insert = await prepare_mx_scheduled_ledger(
            mx_scheduled_ledger_repository=mx_scheduled_ledger_repository,
            scheduled_ledger_id=scheduled_ledger_id_1,
            ledger_id=ledger_id_1,
            payment_account_id=payment_account_id,
            routing_key=datetime(2019, 8, 7),
        )
        await mx_scheduled_ledger_repository.insert_mx_scheduled_ledger(
            mx_scheduled_ledger_to_insert
        )

        ledger_to_insert = await prepare_mx_ledger(
            ledger_id=ledger_id_2, payment_account_id=payment_account_id
        )
        await mx_ledger_repository.insert_mx_ledger(ledger_to_insert)
        mx_scheduled_ledger_to_insert = await prepare_mx_scheduled_ledger(
            mx_scheduled_ledger_repository=mx_scheduled_ledger_repository,
            scheduled_ledger_id=scheduled_ledger_id_2,
            ledger_id=ledger_id_2,
            payment_account_id=payment_account_id,
            routing_key=datetime(2019, 8, 14),
        )
        await mx_scheduled_ledger_repository.insert_mx_scheduled_ledger(
            mx_scheduled_ledger_to_insert
        )

        request = GetMxLedgerByAccountInput(payment_account_id=payment_account_id)
        mx_scheduled_ledger = await mx_scheduled_ledger_repository.get_open_mx_scheduled_ledger_for_payment_account(
            request
        )

        assert mx_scheduled_ledger is not None
        assert mx_scheduled_ledger.id == scheduled_ledger_id_1
        assert mx_scheduled_ledger.payment_account_id == payment_account_id
        assert mx_scheduled_ledger.ledger_id == ledger_id_1
        assert mx_scheduled_ledger.interval_type == MxScheduledLedgerIntervalType.WEEKLY
        assert mx_scheduled_ledger.start_time == datetime(2019, 8, 5, 7)
        assert mx_scheduled_ledger.end_time == datetime(2019, 8, 12, 7)

    async def test_get_open_mx_scheduled_ledger_for_payment_account_not_exist_success(
        self,
        mx_scheduled_ledger_repository: MxScheduledLedgerRepository,
        mx_ledger_repository: MxLedgerRepository,
    ):
        payment_account_id = str(uuid.uuid4())
        scheduled_ledger_id = uuid.uuid4()
        ledger_id = uuid.uuid4()
        routing_key = datetime(2019, 8, 1)

        ledger_to_insert = await prepare_mx_ledger(
            ledger_id=ledger_id, payment_account_id=payment_account_id
        )
        await mx_ledger_repository.insert_mx_ledger(ledger_to_insert)

        mx_scheduled_ledger_to_insert = await prepare_mx_scheduled_ledger(
            mx_scheduled_ledger_repository=mx_scheduled_ledger_repository,
            scheduled_ledger_id=scheduled_ledger_id,
            ledger_id=ledger_id,
            payment_account_id=payment_account_id,
            routing_key=routing_key,
        )
        await mx_scheduled_ledger_repository.insert_mx_scheduled_ledger(
            mx_scheduled_ledger_to_insert
        )

        request = GetMxLedgerByAccountInput(payment_account_id=str(uuid.uuid4()))
        mx_scheduled_ledger = await mx_scheduled_ledger_repository.get_open_mx_scheduled_ledger_for_payment_account(
            request
        )
        assert mx_scheduled_ledger is None
