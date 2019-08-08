from datetime import datetime
import uuid

import pytest
import pytest_mock

from app.commons.context.app_context import AppContext
from app.commons.database.model import Database
from app.commons.types import CurrencyType
from app.ledger.core.mx_transaction.types import (
    MxScheduledLedgerIntervalType,
    MxLedgerType,
    MxLedgerStateType,
)
from app.ledger.repository.mx_ledger_repository import (
    InsertMxLedgerInput,
    MxLedgerRepository,
)
from app.ledger.repository.mx_scheduled_ledger_repository import (
    MxScheduledLedgerRepository,
    InsertMxScheduledLedgerInput,
    GetMxScheduledLedgerInput,
)


class TestMxLedgerRepository:
    pytestmark = [pytest.mark.asyncio]

    async def test_insert_mx_scheduled_ledger_success(
        self, mocker: pytest_mock.MockFixture, ledger_paymentdb: Database
    ):
        app_context: AppContext = AppContext(
            log=mocker.Mock(),
            payout_bankdb=mocker.Mock(),
            payin_maindb=mocker.Mock(),
            payin_paymentdb=mocker.Mock(),
            payout_maindb=mocker.Mock(),
            ledger_maindb=mocker.Mock(),
            ledger_paymentdb=ledger_paymentdb,
            stripe=mocker.Mock(),
            dsj_client=mocker.Mock(),
        )
        scheduled_ledger_repo = MxScheduledLedgerRepository(context=app_context)
        ledger_repo = MxLedgerRepository(context=app_context)
        mx_scheduled_ledger_id = uuid.uuid4()
        ledger_id = uuid.uuid4()
        payment_account_id = str(uuid.uuid4())
        ledger_to_insert = InsertMxLedgerInput(
            id=ledger_id,
            type=MxLedgerType.MANUAL.value,
            currency=CurrencyType.USD.value,
            state=MxLedgerStateType.OPEN.value,
            balance=2000,
            payment_account_id=payment_account_id,
        )
        mx_scheduled_ledger_to_insert = InsertMxScheduledLedgerInput(
            id=mx_scheduled_ledger_id,
            payment_account_id=payment_account_id,
            ledger_id=ledger_id,
            interval_type=MxScheduledLedgerIntervalType.WEEKLY.value,
            start_time=datetime(2019, 8, 5),
            end_time=datetime(2019, 8, 12),
        )
        await ledger_repo.insert_mx_ledger(ledger_to_insert)
        mx_scheduled_ledger = await scheduled_ledger_repo.insert_mx_scheduled_ledger(
            mx_scheduled_ledger_to_insert
        )

        assert mx_scheduled_ledger.id == mx_scheduled_ledger_id
        assert mx_scheduled_ledger.payment_account_id == payment_account_id
        assert mx_scheduled_ledger.ledger_id == ledger_id
        assert mx_scheduled_ledger.interval_type == MxScheduledLedgerIntervalType.WEEKLY
        assert mx_scheduled_ledger.start_time == datetime(2019, 8, 5)
        assert mx_scheduled_ledger.end_time == datetime(2019, 8, 12)

    async def test_get_open_mx_scheduled_ledger_for_period_success(
        self, mocker: pytest_mock.MockFixture, ledger_paymentdb: Database
    ):
        app_context: AppContext = AppContext(
            log=mocker.Mock(),
            payout_bankdb=mocker.Mock(),
            payin_maindb=mocker.Mock(),
            payin_paymentdb=mocker.Mock(),
            payout_maindb=mocker.Mock(),
            ledger_maindb=mocker.Mock(),
            ledger_paymentdb=ledger_paymentdb,
            stripe=mocker.Mock(),
            dsj_client=mocker.Mock(),
        )
        scheduled_ledger_repo = MxScheduledLedgerRepository(context=app_context)
        ledger_repo = MxLedgerRepository(context=app_context)
        payment_account_id = str(uuid.uuid4())
        ledger_id = uuid.uuid4()
        request = GetMxScheduledLedgerInput(
            payment_account_id=payment_account_id,
            routing_key=datetime(2019, 8, 1),
            interval_type=MxScheduledLedgerIntervalType.WEEKLY.value,
        )
        ledger_to_insert = InsertMxLedgerInput(
            id=ledger_id,
            type=MxLedgerType.MANUAL.value,
            currency=CurrencyType.USD.value,
            state=MxLedgerStateType.OPEN.value,
            balance=2000,
            payment_account_id=payment_account_id,
        )
        mx_scheduled_ledger_to_insert = InsertMxScheduledLedgerInput(
            id=ledger_id,
            payment_account_id=payment_account_id,
            ledger_id=ledger_id,
            interval_type=MxScheduledLedgerIntervalType.WEEKLY.value,
            start_time=datetime(2019, 7, 29, 7),
            end_time=datetime(2019, 8, 5, 7),
        )
        await ledger_repo.insert_mx_ledger(ledger_to_insert)
        await scheduled_ledger_repo.insert_mx_scheduled_ledger(
            mx_scheduled_ledger_to_insert
        )

        mx_scheduled_ledger = await scheduled_ledger_repo.get_open_mx_scheduled_ledger_for_period(
            request
        )

        assert mx_scheduled_ledger is not None
        assert mx_scheduled_ledger.id == ledger_id
        assert mx_scheduled_ledger.payment_account_id == payment_account_id
        assert mx_scheduled_ledger.ledger_id == ledger_id
        assert mx_scheduled_ledger.interval_type == MxScheduledLedgerIntervalType.WEEKLY
        assert mx_scheduled_ledger.start_time == datetime(2019, 7, 29, 7)
        assert mx_scheduled_ledger.end_time == datetime(2019, 8, 5, 7)

    async def test_get_open_mx_scheduled_ledger_for_period_not_exist_success(
        self, mocker: pytest_mock.MockFixture, ledger_paymentdb: Database
    ):
        app_context: AppContext = AppContext(
            log=mocker.Mock(),
            payout_bankdb=mocker.Mock(),
            payin_maindb=mocker.Mock(),
            payin_paymentdb=mocker.Mock(),
            payout_maindb=mocker.Mock(),
            ledger_maindb=mocker.Mock(),
            ledger_paymentdb=ledger_paymentdb,
            stripe=mocker.Mock(),
            dsj_client=mocker.Mock(),
        )
        scheduled_ledger_repo = MxScheduledLedgerRepository(context=app_context)
        ledger_repo = MxLedgerRepository(context=app_context)
        payment_account_id = str(uuid.uuid4())
        ledger_id = uuid.uuid4()
        request = GetMxScheduledLedgerInput(
            payment_account_id=payment_account_id,
            routing_key=datetime(2019, 8, 1),
            interval_type=MxScheduledLedgerIntervalType.WEEKLY.value,
        )
        ledger_to_insert = InsertMxLedgerInput(
            id=ledger_id,
            type=MxLedgerType.MANUAL.value,
            currency=CurrencyType.USD.value,
            state=MxLedgerStateType.OPEN.value,
            balance=2000,
            payment_account_id=payment_account_id,
        )
        mx_scheduled_ledger_to_insert = InsertMxScheduledLedgerInput(
            id=ledger_id,
            payment_account_id=payment_account_id,
            ledger_id=ledger_id,
            interval_type=MxScheduledLedgerIntervalType.WEEKLY.value,
            start_time=datetime(2019, 8, 5, 7),
            end_time=datetime(2019, 8, 12, 7),
        )
        await ledger_repo.insert_mx_ledger(ledger_to_insert)
        await scheduled_ledger_repo.insert_mx_scheduled_ledger(
            mx_scheduled_ledger_to_insert
        )

        mx_scheduled_ledger = await scheduled_ledger_repo.get_open_mx_scheduled_ledger_for_period(
            request
        )
        assert mx_scheduled_ledger is None
