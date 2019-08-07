from datetime import datetime, timezone

import pytest_mock

from app.commons.context.app_context import AppContext
from app.ledger.core.mx_transaction.types import MxScheduledLedgerIntervalType
from app.ledger.repository.mx_scheduled_ledger_repository import (
    MxScheduledLedgerRepository,
)


class TestMxScheduledLedgerRepository:
    def test_start_time_for_current_interval_success(
        self, mocker: pytest_mock.MockFixture
    ):
        routing_key = datetime(2018, 8, 2, tzinfo=timezone.utc)
        interval = MxScheduledLedgerIntervalType.WEEKLY
        app_context: AppContext = AppContext(
            log=mocker.Mock(),
            payout_bankdb=mocker.Mock(),
            payin_maindb=mocker.Mock(),
            payin_paymentdb=mocker.Mock(),
            payout_maindb=mocker.Mock(),
            ledger_maindb=mocker.Mock(),
            ledger_paymentdb=mocker.Mock(),
            stripe=mocker.Mock(),
        )
        scheduled_ledger_repo = MxScheduledLedgerRepository(context=app_context)
        start_time = scheduled_ledger_repo.pacific_start_time_for_current_interval(
            routing_key, interval
        )
        assert not start_time == datetime(2018, 7, 30, tzinfo=timezone.utc)
        assert start_time == datetime(
            2018, 7, 30, 7
        )  # Pacific time without time zone specified
