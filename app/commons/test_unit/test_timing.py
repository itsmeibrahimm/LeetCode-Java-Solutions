import contextlib
import pytest
from typing import List
from app.commons import timing
from app.commons.utils.testing import Stat
from app.commons.timing import _discover_caller


class TestDiscover:
    def caller(self, additional_ignores=None):
        return _discover_caller(additional_ignores=additional_ignores)

    def test_find(self):
        f, name = self.caller()
        assert (
            name == "app.commons.test_unit.test_timing"
        ), "returns the name of the caller"

    def test_find_exclude(self):
        f, name = self.caller(["app.commons.test_unit"])
        assert name != "app.commons.test_unit.test_timing", "exclude unit tests"


class TestDatabaseTimingTracker:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture(autouse=True)
    def setup(self, service_statsd_client):
        # ensure that we mock the statsd service client
        ...

    async def test_transaction(self, get_mock_statsd_events):
        @contextlib.asynccontextmanager
        async def transaction_manager():
            yield "some transaction"

        class Database(timing.Database):
            database_name = "some db"
            instance_name = "master"

            @timing.track_transaction
            def transaction(self):
                return transaction_manager()

            @timing.track_query
            async def query(self, *args, **kwargs):
                ...

        class Caller:
            db = Database()

            async def do_something(self):
                async with self.db.transaction():
                    ...
                    await self.insert_into_table()
                    await self.update_table()

            async def insert_into_table(self):
                await self.db.query()

            async def update_table(self):
                await self.db.query()

            async def insert_without_transaction(self):
                await self.db.query()

        caller = Caller()
        await caller.do_something()
        # dd.response.io.some-db.query.enter_context.latency~cluster=master~transaction=no~transaction_name=:5.885283|ms

        events: List[Stat] = get_mock_statsd_events()
        stat_names = [stat.stat_name for stat in events]

        # query timing
        assert (
            "dd.pay.payment-service.io.some-db.query.insert_into_table.latency"
            in stat_names
        )
        assert (
            "dd.pay.payment-service.io.some-db.query.update_table.latency" in stat_names
        )

        # transaction timing
        assert (
            "dd.pay.payment-service.io.some-db.transaction.do_something.latency"
            in stat_names
        )
