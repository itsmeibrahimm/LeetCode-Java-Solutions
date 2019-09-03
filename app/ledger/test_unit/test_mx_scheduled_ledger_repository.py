from datetime import datetime, timezone

from app.commons.context.app_context import AppContext
from app.ledger.core.types import MxScheduledLedgerIntervalType
from app.ledger.core.utils import pacific_start_time_for_current_interval


class TestMxScheduledLedgerRepository:
    def test_start_time_for_current_interval_success(
        self, dummy_app_context: AppContext
    ):
        routing_key = datetime(2018, 8, 2, tzinfo=timezone.utc)
        interval = MxScheduledLedgerIntervalType.WEEKLY
        start_time = pacific_start_time_for_current_interval(routing_key, interval)
        assert not start_time == datetime(2018, 7, 30, tzinfo=timezone.utc)
        assert start_time == datetime(
            2018, 7, 30, 7
        )  # Pacific time without time zone specified
