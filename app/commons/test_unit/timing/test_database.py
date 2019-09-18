import contextlib
import pytest
from typing import List
from app.commons import tracing, timing
from app.commons.utils.testing import Stat
from app.commons.timing.database import _discover_caller


class TestDiscover:
    def caller(self, additional_ignores=None):
        return _discover_caller(additional_ignores=additional_ignores)

    def test_find(self):
        f, name = self.caller()
        assert name == __name__, "returns the name of the caller"

    def test_find_exclude(self):
        f, name = self.caller(["app.commons.test_unit"])
        assert name != __name__, "exclude unit tests"


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

        class Database(timing.database.Database):
            database_name = "somedb"
            instance_name = "master"

            @timing.database.track_transaction
            def transaction(self):
                return transaction_manager()

            @timing.database.track_query
            async def query(self, *args, **kwargs):
                ...

        # ensure stats have app name
        @tracing.track_breadcrumb(application_name="my-app")
        class Caller:
            db = Database()

            async def do_something(self):
                async with self.db.transaction():
                    ...
                    await self.insert_into_table()
                    await self.update_table()
                    return 1

            async def insert_into_table(self):
                await self.db.query()

            async def update_table(self):
                await self.db.query()

            async def insert_without_transaction(self):
                await self.db.query()

        caller = Caller()
        assert await caller.do_something() == 1

        events: List[Stat] = get_mock_statsd_events()
        assert (
            len(events) == 3
        ), "one stat for the transaction, one for each query (2 total)"
        stat_names = {
            (event.stat_name, event.tags["query_name"]): event for event in events
        }

        # query timing
        insert_name = ("dd.pay.payment-service.io.db.latency", "insert_into_table")
        assert insert_name in stat_names, "insert query exists"
        insert_query = stat_names[insert_name]
        assert insert_query.tags == {
            "application_name": "my-app",
            "database_name": "somedb",
            "instance_name": "master",
            "transaction_name": "do_something",
            "query_name": "insert_into_table",
        }

        update_name = ("dd.pay.payment-service.io.db.latency", "update_table")
        assert update_name in stat_names, "update query exists"
        update_query = stat_names[update_name]
        assert update_query.tags == {
            "application_name": "my-app",
            "database_name": "somedb",
            "instance_name": "master",
            "transaction_name": "do_something",
            "query_name": "update_table",
        }

        # transaction timing
        transaction_name = ("dd.pay.payment-service.io.db.latency", "do_something")
        assert transaction_name in stat_names, "transaction exists"
        transaction = stat_names[transaction_name]
        assert transaction.tags == {
            "application_name": "my-app",
            "database_name": "somedb",
            "instance_name": "master",
            # "transaction_name": "do_something",
            "query_type": "transaction",
            "query_name": "do_something",
        }
